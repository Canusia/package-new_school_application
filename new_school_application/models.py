import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from model_utils import FieldTracker
from multiselectfield import MultiSelectField

from cis.backends.storage_backend import PrivateMediaStorage


APPLICATION_STATUS_OPTIONS = [
    ('In Progress', 'In Progress'),
    ('Submitted', 'Submitted'),
    ('Under Review', 'Under Review'),
    ('Decision Made', 'Decision Made'),
    ('Withdrawn', 'Withdrawn'),
    ('Closed', 'Closed'),
]

INTERESTED_COURSE_STATUS_OPTIONS = [
    ('Applied', 'Applied'),
    ('Approved', 'Approved'),
    ('Not Approved', 'Not Approved'),
]

COURSE_REVIEW_STATUS_OPTIONS = [
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Approved and Waitlisted', 'Approved and Waitlisted'),
    ('Not Approved', 'Not Approved'),
    ('Need more information', 'Need more information'),
]

OTHER_COLLEGE_COURSE_CHOICES = [
    ('AP', 'AP'),
    ('IB', 'IB'),
    ('Community College', 'Community College'),
    ('Other', 'Other'),
]

NOTE_TYPE_CHOICES = [
    ('note', 'Internal note'),
    ('response', 'Response'),
    ('to_submitter', 'To submitter'),
    ('to_all_hs_admin', 'To all HS admins'),
]

EDITABLE_STATUSES = ('In Progress', 'Submitted')


class _StatusHistoryModel(models.Model):
    """Abstract base for models with a ``status`` workflow field.

    Appends a ``{'status', 'on'}`` entry to ``status_changed_on`` whenever the
    status is set on create or subsequently changes. Concrete subclasses must
    declare ``status``, ``status_changed_on`` (JSONField default=list), and
    ``tracker = FieldTracker(fields=['status'])``.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding or self.tracker.has_changed('status'):
            history = list(self.status_changed_on or [])
            history.append({'status': self.status, 'on': timezone.now().isoformat()})
            self.status_changed_on = history
            update_fields = kwargs.get('update_fields')
            if update_fields is not None and 'status_changed_on' not in update_fields:
                kwargs['update_fields'] = list(update_fields) + ['status_changed_on']
        super().save(*args, **kwargs)


class HighSchoolApplication(_StatusHistoryModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    district = models.TextField(blank=True, default='')
    school_contacts = models.JSONField(default=dict, blank=True)
    district_contacts = models.JSONField(default=dict, blank=True)
    information = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=APPLICATION_STATUS_OPTIONS, default='In Progress',
    )
    created_on = models.DateTimeField(auto_now_add=True)
    status_changed_on = models.JSONField(default=list, blank=True)
    course_guide = models.FileField(
        storage=PrivateMediaStorage(),
        upload_to='new_school_application/course_guides/',
        null=True, blank=True,
    )
    other_college_courses = MultiSelectField(
        choices=OTHER_COLLEGE_COURSE_CHOICES, max_length=200, blank=True,
    )

    tracker = FieldTracker(fields=['status'])

    @property
    def can_edit(self):
        return self.status in EDITABLE_STATUSES

    @property
    def ce_url(self):
        from django.urls import reverse
        from cis.utils import getDomain  # ewu domain helper
        return getDomain() + reverse('new_school_application_ce:detail', kwargs={'record_id': self.id})

    @property
    def approval_letter_url(self):
        from django.urls import reverse, NoReverseMatch
        from cis.utils import getDomain
        try:
            path = reverse('new_school_application_ce:approval_letter', kwargs={'record_id': self.id})
        except NoReverseMatch:
            path = reverse('new_school_application_ce:detail', kwargs={'record_id': self.id})
        return getDomain() + path

    @property
    def interested_course_ids(self):
        return list(self.interested_courses.values_list('course_id', flat=True))

    @property
    def interested_courses_status(self):
        return ', '.join(
            '%s: %s' % (ic.course, ic.status)
            for ic in self.interested_courses.select_related('course'))

    def add_note(self, created_by, message, note_type='note'):
        return SchoolApplicationNote.objects.create(
            highschool_application=self,
            created_by=created_by,
            message=message,
            type=note_type,
        )

    def add_reviewers(self):
        """Create a course-review per interested course's active course
        administrators. Idempotent (unique_together(interested_course, reviewer)
        + get_or_create)."""
        from cis.models.course import Course
        for interested_course in self.interested_courses.all():
            admins = Course.get_administrators([interested_course.course_id]).distinct('user')
            for admin in admins:
                HighSchoolApplicationCourseReview.objects.get_or_create(
                    interested_course=interested_course,
                    reviewer=admin.user,
                )

    def has_all_courses_reviewed(self):
        return not HighSchoolApplicationCourseReview.objects.filter(
            interested_course__highschool_application=self,
            status__in=['Pending', 'Need more information'],
        ).exists()

    def has_application_reviewed(self):
        return self.status == 'Decision Made'

    def user_has_pending_reviews(self, user):
        if not getattr(user, 'is_authenticated', False):
            return False
        return HighSchoolApplicationCourseReview.objects.filter(
            interested_course__highschool_application=self,
            reviewer=user,
            status__in=['Pending', 'Need more information'],
        ).exists()

    def pending_reviews_for_user(self, user):
        return HighSchoolApplicationCourseReview.objects.filter(
            interested_course__highschool_application=self,
            reviewer=user,
            status__in=['Pending', 'Need more information'],
        ).select_related('interested_course', 'interested_course__course')

    @staticmethod
    def _split_name(full_name):
        parts = (full_name or '').split()
        if not parts:
            return '', ''
        if len(parts) == 1:
            return parts[0], parts[0]
        return parts[0], ' '.join(parts[1:])

    def import_as_highschool(self):
        """Provision (or update) a real HighSchool + administrator records from
        this application. Idempotent: existing HS matched by name is updated."""
        from cis.models.highschool import HighSchool
        from cis.models.highschool_administrator import (
            HSAdministrator, HSAdministratorPosition, HSPosition,
        )

        addr = (self.information or {}).get('address', {})
        hs = HighSchool.objects.filter(name__iexact=self.name).first()
        if hs is None:
            hs = HighSchool(name=self.name)
        # HighSchool.code is NOT NULL (default '-') and part of unique_together
        # ('name', 'code'); fall back to '-' when the application has no CEEB code.
        hs.code = addr.get('code') or '-'
        hs.address1 = addr.get('address') or ''
        hs.city = addr.get('city') or ''
        hs.state = addr.get('state') or ''
        hs.postal_code = addr.get('postal_code') or ''
        hs.country = addr.get('country') or ''
        hs.status = 'Active'
        hs.save()

        sc = self.school_contacts or {}
        dc = self.district_contacts or {}
        people = [
            ('Principal', sc.get('principal', {})),
            ('Director of Guidance', sc.get('guidance', {})),
            ('Superintendent', dc.get('superintendent', {})),
            ('Program Coordinator', sc.get('primary_contact', {})),  # neutralized label
        ]
        for position_name, contact in people:
            email = contact.get('email')
            if not email:
                continue
            first, last = self._split_name(contact.get('name'))
            position = HSPosition.get_or_add(name=position_name)
            hsadmin = HSAdministrator.get_or_add(
                email=email, first_name=first, last_name=last)
            HSAdministratorPosition.get_or_add(
                hsadmin=hsadmin, highschool=hs, position=position, status='Active')

        return hs

    def notify_application_approved(self, send_to):
        from .services import emails as _emails
        _emails.send_application_approved(self, send_to)

    def mark_as_approval_notification(self, request):
        from django.utils import timezone
        info = self.information or {}
        info['approval_notification_last_sent_on'] = timezone.now().strftime('%m/%d/%Y')
        info['approval_last_sent_by'] = str(getattr(request, 'user', ''))
        HighSchoolApplication.objects.filter(pk=self.id).update(information=info)
        self.information = info

    @property
    def sexy_approval_notification_sent_on(self):
        sent = (self.information or {}).get('approval_notification_last_sent_on')
        if not sent:
            return ''
        return 'Approval notification last sent on %s' % sent

    def __str__(self):
        return f'{self.name} ({self.status})'


class HighSchoolInterestedCourse(_StatusHistoryModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    highschool_application = models.ForeignKey(
        HighSchoolApplication, on_delete=models.PROTECT,
        related_name='interested_courses',
    )
    course = models.ForeignKey('cis.Course', on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20, choices=INTERESTED_COURSE_STATUS_OPTIONS, default='Applied',
    )
    status_changed_on = models.JSONField(default=list, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    tracker = FieldTracker(fields=['status'])

    class Meta:
        unique_together = ['highschool_application', 'course']

    def __str__(self):
        return f'{self.course_id} → {self.status}'


class HighSchoolApplicationCourseReview(_StatusHistoryModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interested_course = models.ForeignKey(
        HighSchoolInterestedCourse, on_delete=models.PROTECT,
        related_name='reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
    )
    status = models.CharField(
        max_length=30, choices=COURSE_REVIEW_STATUS_OPTIONS, default='Pending',
    )
    misc_info = models.JSONField(default=dict, blank=True)
    status_changed_on = models.JSONField(default=list, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    tracker = FieldTracker(fields=['status'])

    class Meta:
        unique_together = ['interested_course', 'reviewer']

    def __str__(self):
        return f'review({self.interested_course_id}) {self.status}'

    def notify_reviewer(self):
        """Create an in-app alert for the reviewer. Email is sent in Plan E."""
        from django.urls import reverse
        from django.utils.html import escape

        from alerts.models import Alert
        app = self.interested_course.highschool_application
        # Embed the application UUID in the link so the alert can be matched
        # exactly when it's later marked read (Alert has no structured FK).
        url = '%s?application=%s' % (
            reverse('new_school_application_faculty:reviews'), app.id)
        Alert.objects.create(
            alert_type='new_school_application_pending_review',
            recipient=self.reviewer,
            message=(
                '<a href="%s">A new school application (%s) is pending your '
                'course review.</a>' % (url, escape(app.name))
            ),
        )
        from .services import emails as _emails
        _emails.notify_reviewer_assigned(self)

    def notify_status_change(self, new_status):
        from .services import emails as _emails
        _emails.notify_review_decided(self)


class SchoolApplicationNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    highschool_application = models.ForeignKey(
        HighSchoolApplication, on_delete=models.CASCADE, related_name='notes',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    message = models.TextField()
    type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES, default='note')
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'note({self.highschool_application_id})'
