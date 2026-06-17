from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from cis.models.course import Cohort, Course, CourseAdministrator
from new_school_application.new_school_application.forms.ce import (
    HighSchoolApplicationApprovalNotificationForm,
)
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
)
from new_school_application.new_school_application.settings.new_school_application import (
    new_school_application as NSASettings,
)

User = get_user_model()


class ApprovalNotificationTest(TestCase):
    def setUp(self):
        NSASettings().install()
        from cis.models.settings import Setting
        s = Setting.objects.get(key='new_school_application')
        s.value = {**s.value, 'is_active': 'Yes'}
        s.save()
        self.app = HighSchoolApplication.objects.create(
            name='Lincoln High', status='Decision Made',
            school_contacts={
                'submitted_by': {'name': 'Jo', 'email': 'jo@example.com'},
                'principal': {'name': 'Dr. Jane Roe', 'email': 'p@example.com'},
                'guidance': {'name': 'G', 'email': 'g@example.com'},
                'primary_contact': {'name': 'C', 'email': 'c@example.com'}},
            district_contacts={'superintendent': {'name': 'S', 'email': 's@example.com'}})

    def test_form_blocks_when_not_decision_made(self):
        self.app.status = 'Under Review'
        self.app.save()
        form = HighSchoolApplicationApprovalNotificationForm(
            self.app, {'notif_checklist': ['Principal'], 'action': 'send_approval_notification'})
        self.assertFalse(form.is_valid())

    @mock.patch('new_school_application.new_school_application.services.emails.send_html_mail')
    def test_form_sends_to_selected_recipients(self, send):
        form = HighSchoolApplicationApprovalNotificationForm(
            self.app, {'notif_checklist': ['Principal', 'Submitter'],
                       'action': 'send_approval_notification'})
        self.assertTrue(form.is_valid(), form.errors)
        request = SimpleNamespace(user=User.objects.create_user(
            username='ce@example.com', email='ce@example.com', password='x'))
        form.save(request, self.app)
        self.assertTrue(send.called)
        to = send.call_args[0][4]
        self.assertIn('p@example.com', to)
        self.assertIn('jo@example.com', to)

    def test_mark_as_approval_notification_records_timestamp(self):
        request = SimpleNamespace(user=User.objects.create_user(
            username='ce2@example.com', email='ce2@example.com', password='x'))
        self.app.mark_as_approval_notification(request)
        self.app.refresh_from_db()
        self.assertIn('approval_notification_last_sent_on', self.app.information)
