from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import HighSchoolApplication, HighSchoolApplicationCourseReview


@receiver(post_save, sender=HighSchoolApplication)
def assign_reviewers_on_under_review(sender, instance, created, **kwargs):
    if instance.status == 'Under Review':
        instance.add_reviewers()


@receiver(post_save, sender=HighSchoolApplication)
def application_created_email(sender, instance, created, **kwargs):
    if created:
        from .services import emails as _emails
        _emails.notify_application_created(instance)


@receiver(post_save, sender=HighSchoolApplication)
def application_submitted_email(sender, instance, created, **kwargs):
    if not created and instance.status == 'Under Review':
        from .services import emails as _emails
        _emails.notify_application_submitted(instance)


@receiver(post_save, sender=HighSchoolApplicationCourseReview)
def review_side_effects(sender, instance, created, **kwargs):
    if created:
        # Alert (and, in Plan E, email) the reviewer once per application.
        already = HighSchoolApplicationCourseReview.objects.filter(
            reviewer=instance.reviewer,
            interested_course__highschool_application=(
                instance.interested_course.highschool_application),
        ).count()
        if already <= 1:
            instance.notify_reviewer()
    else:
        instance.notify_status_change(instance.status)
        from alerts.models import Alert
        app = instance.interested_course.highschool_application
        # Match on the application UUID embedded in the alert link, not the
        # free-text name (which is non-unique and substring-collides).
        Alert.objects.filter(
            alert_type='new_school_application_pending_review',
            read_on__isnull=True,
            recipient=instance.reviewer,
            message__contains=str(app.id),
        ).update(read_on=timezone.now())
