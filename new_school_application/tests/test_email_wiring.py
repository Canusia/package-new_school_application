from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from cis.models.course import Cohort, Course, CourseAdministrator
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
)
from new_school_application.new_school_application.settings.new_school_application import (
    new_school_application as NSASettings,
)

User = get_user_model()


class EmailWiringTest(TestCase):
    def setUp(self):
        NSASettings().install()
        from cis.models.settings import Setting
        s = Setting.objects.get(key='new_school_application')
        s.value = {**s.value, 'is_active': 'Yes', 'app_started_email_recipient': 'ce@example.com'}
        s.save()
        self.cohort = Cohort.objects.create(name='Co', designator='CO')
        self.course = Course.objects.create(
            name='C1', title='Course 1', cohort=self.cohort,
            catalog_number='101', credit_hours=3)
        self.admin = User.objects.create_user(
            username='r@example.com', email='r@example.com', password='x')
        CourseAdministrator.objects.create(
            user=self.admin, course=self.course, role='Administrator', status='Active')

    @mock.patch('new_school_application.new_school_application.services.emails.send_html_mail')
    def test_create_sends_welcome(self, send):
        HighSchoolApplication.objects.create(
            name='HS', school_contacts={'submitted_by': {'name': 'Jo', 'email': 'jo@example.com'}})
        # welcome (+ internal) emails fire on create
        self.assertTrue(send.called)

    @mock.patch('new_school_application.new_school_application.services.emails.send_html_mail')
    def test_under_review_emails_reviewer(self, send):
        app = HighSchoolApplication.objects.create(
            name='HS', school_contacts={'submitted_by': {'name': 'Jo', 'email': 'jo@example.com'}})
        HighSchoolInterestedCourse.objects.create(highschool_application=app, course=self.course)
        send.reset_mock()
        app.status = 'Under Review'
        app.save()  # assigns reviewer → reviewer email; + submitted internal email
        recipients = [c[0][4] for c in send.call_args_list]
        flat = [r for sub in recipients for r in sub]
        self.assertIn('r@example.com', flat)

    def test_ce_url_and_approval_url(self):
        app = HighSchoolApplication.objects.create(name='HS')
        self.assertIn(str(app.id), app.ce_url)
        self.assertIn(str(app.id), app.approval_letter_url)
