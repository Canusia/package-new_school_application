from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.views.decorators.clickjacking import xframe_options_exempt

from rest_framework import viewsets

from cis.menu import cis_menu, draw_menu
from cis.models.course import Course

from ..forms.ce import (
    HighSchoolApplicationApprovalNotificationForm,
    HighSchoolApplicationEditForm,
)
from ..services.pdf import approval_letter_pdf as _build_approval_pdf
from ..models import (
    HighSchoolApplication,
    HighSchoolApplicationCourseReview,
    HighSchoolInterestedCourse,
    SchoolApplicationNote,
)
from ..permissions import CISUserOnly
from ..serializers.ce import ApplicationListSerializer, NoteSerializer


class ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApplicationListSerializer
    permission_classes = [CISUserOnly]

    def get_queryset(self):
        qs = HighSchoolApplication.objects.all().order_by('-created_on')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        created_on = self.request.GET.get('created_on')
        if created_on:
            qs = qs.filter(created_on__date__gte=created_on)
        created_until = self.request.GET.get('created_until')
        if created_until:
            qs = qs.filter(created_on__date__lte=created_until)
        return qs


class NoteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [CISUserOnly]

    def get_queryset(self):
        app_id = self.request.GET.get('application_id')
        if not _is_uuid(app_id):
            return SchoolApplicationNote.objects.none()
        return SchoolApplicationNote.objects.filter(
            highschool_application__id=app_id,
        ).order_by('-created_on')


def _is_uuid(value):
    import uuid
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _available_courses():
    return Course.objects.filter(
        meta__available_for_new_schools='1', status='Active',
    ).order_by('title')


# Ordered (key, role-label, contacts-dict, contact-key) for the application's people.
def _contacts_list(record):
    sc = record.school_contacts or {}
    dc = record.district_contacts or {}
    rows = [
        ('submitter', 'Submitter', sc.get('submitted_by', {})),
        ('principal', 'Principal', sc.get('principal', {})),
        ('primary_contact', 'Primary Contact', sc.get('primary_contact', {})),
        ('guidance', 'Director of Guidance', sc.get('guidance', {})),
        ('superintendent', 'Superintendent', dc.get('superintendent', {})),
    ]
    return [
        {'key': key, 'role': role,
         'name': (info or {}).get('name') or '',
         'email': (info or {}).get('email') or ''}
        for key, role, info in rows
    ]


def _contacts_map(record):
    return {c['key']: c['email'] for c in _contacts_list(record)}


def index(request):
    from ..models import APPLICATION_STATUS_OPTIONS
    return render(request, 'new_school_application/ce/index.html', {
        'page_title': 'New School Applications',
        'menu': draw_menu(cis_menu, 'highschools', 'new_school_applications'),
        'status_options': APPLICATION_STATUS_OPTIONS,
        'api_url': reverse_lazy('new_school_application_ce:application-list'),
    })


@xframe_options_exempt
def detail(request, record_id):
    record = get_object_or_404(HighSchoolApplication, pk=record_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'edit_application':
            form = HighSchoolApplicationEditForm(record, request.POST, request.FILES)
            if form.is_valid():
                form.save(request, record)
                return JsonResponse({'status': 'success', 'message': 'Updated.'})
            return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
        if action == 'add_note':
            message = (request.POST.get('message') or '').strip()
            if not message:
                return JsonResponse({'status': 'error', 'message': 'Empty note.'}, status=400)
            record.add_note(created_by=request.user, message=message)
            return JsonResponse({'status': 'success', 'message': 'Note added.'})
        if action == 'email_note':
            message = (request.POST.get('message') or '').strip()
            if not message:
                return JsonResponse({'status': 'error', 'message': 'Note message is required.'}, status=400)
            chosen = request.POST.getlist('recipient')
            emails = [_contacts_map(record).get(key) for key in chosen]
            emails = [e for e in emails if e]
            if not emails:
                return JsonResponse({'status': 'error', 'message': 'Select at least one recipient with an email.'}, status=400)
            # save into notes (so it appears in the Notes tab) AND email it
            record.add_note(created_by=request.user, message=message, note_type='to_submitter')
            from ..services import emails as _emails
            _emails.send_applicant_note(record, emails, message)
            return JsonResponse({'status': 'success', 'message': 'Note saved and emailed.'})
        if action == 'import_as_highschool':
            try:
                hs = record.import_as_highschool()
            except Exception as exc:  # provisioning is best-effort; report failure
                return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)
            return JsonResponse({
                'status': 'success',
                'message': 'Imported as a new high school. Review the administrators.',
                'redirect': reverse('cis:hs_detail', kwargs={'record_id': hs.id}),
            })
        if action == 'send_approval_notification':
            form = HighSchoolApplicationApprovalNotificationForm(record, request.POST)
            if form.is_valid():
                form.save(request, record)
                return JsonResponse({'status': 'success', 'message': 'Approval notification sent.'})
            return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
        if action == 'update_courses':
            # ignore malformed (non-UUID) checkbox values to avoid a 500
            selected_ids = {c for c in request.POST.getlist('course') if _is_uuid(c)}
            existing = {
                str(ic.course_id): ic
                for ic in record.interested_courses.all()
            }
            existing_ids = set(existing.keys())
            # remove interested courses that are no longer selected (delete their
            # reviews first to respect the PROTECT FK on course reviews)
            to_remove = existing_ids - selected_ids
            if to_remove:
                remove_pks = [existing[cid].pk for cid in to_remove]
                HighSchoolApplicationCourseReview.objects.filter(
                    interested_course__in=remove_pks).delete()
                HighSchoolInterestedCourse.objects.filter(pk__in=remove_pks).delete()
            # add newly selected courses
            to_add = selected_ids - existing_ids
            for course_id in to_add:
                course = Course.objects.filter(pk=course_id).first()
                if course is None:
                    continue
                HighSchoolInterestedCourse.objects.get_or_create(
                    highschool_application=record, course=course)
            return JsonResponse({'status': 'success', 'message': 'Courses updated.'})
        return JsonResponse({'status': 'error', 'message': 'Unknown action.'}, status=400)

    from collections import OrderedDict
    from django.template.loader import render_to_string

    interested_courses = record.interested_courses.select_related('course')
    note_api_url = mark_safe(
        reverse('new_school_application_ce:note-list')
        + '?application_id=' + str(record.id) + '&format=datatables'
    )
    # Context shared by every tab partial (each is pre-rendered to a tab's html).
    pane_ctx = {
        'record': record,
        'contacts': _contacts_list(record),
        'interested_courses': interested_courses,
        'available_courses': _available_courses(),
        'interested_course_ids': [str(cid) for cid in interested_courses.values_list('course_id', flat=True)],
        'note_api_url': note_api_url,
    }
    detail_tabs = OrderedDict()
    detail_tabs['info'] = {
        'slug': 'tab-info', 'title': 'High School Info', 'icon': 'fas fa-school',
        'badge': None, 'active': True, 'lazy': False,
        'html': render_to_string('new_school_application/ce/tabs/_info.html', pane_ctx, request=request),
    }
    detail_tabs['courses'] = {
        'slug': 'tab-courses', 'title': 'Interested Courses', 'icon': 'fas fa-book',
        'badge': interested_courses.count(), 'active': False, 'lazy': False,
        'html': render_to_string('new_school_application/ce/tabs/_courses.html', pane_ctx, request=request),
    }
    detail_tabs['notes'] = {
        'slug': 'tab-notes', 'title': 'Notes', 'icon': 'fas fa-sticky-note',
        'badge': record.notes.count(), 'active': False, 'lazy': False,
        'html': render_to_string('new_school_application/ce/tabs/_notes.html', pane_ctx, request=request),
    }
    return render(request, 'new_school_application/ce/detail.html', {
        'page_title': 'High School Application',
        'menu': draw_menu(cis_menu, 'highschools', 'new_school_applications'),
        'record': record,
        'form': HighSchoolApplicationEditForm(record),
        'approval_notification_form': HighSchoolApplicationApprovalNotificationForm(record),
        'detail_tabs': detail_tabs,
    })


def approval_letter(request, record_id):
    record = get_object_or_404(HighSchoolApplication, pk=record_id)
    pdf_bytes = _build_approval_pdf(record)
    resp = HttpResponse(pdf_bytes, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="approval_letter.pdf"'
    return resp


def delete_record(request, record_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)
    record = get_object_or_404(HighSchoolApplication, pk=record_id)
    HighSchoolApplicationCourseReview.objects.filter(
        interested_course__highschool_application=record).delete()
    HighSchoolInterestedCourse.objects.filter(highschool_application=record).delete()
    SchoolApplicationNote.objects.filter(highschool_application=record).delete()
    record.delete()
    return JsonResponse({
        'status': 'success', 'message': 'Application deleted.',
        'redirect': str(reverse_lazy('new_school_application_ce:index')),
    })
