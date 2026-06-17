from django.contrib.auth import get_user_model
from django.test import TestCase

from alerts.models import Alert
from cis.models.course import Cohort, Course, CourseAdministrator
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
)

User = get_user_model()


class SignalTest(TestCase):
    def setUp(self):
        self.cohort = Cohort.objects.create(name='Co', designator='CO')
        self.course = Course.objects.create(
            name='C1', title='Course 1', cohort=self.cohort,
            catalog_number='101', credit_hours=3)
        self.admin_user = User.objects.create_user(
            username='fac@example.com', email='fac@example.com', password='x')
        CourseAdministrator.objects.create(
            user=self.admin_user, course=self.course,
            role='Administrator', status='Active')
        self.app = HighSchoolApplication.objects.create(name='Test HS')
        HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app, course=self.course)

    def test_under_review_assigns_reviewers(self):
        self.app.status = 'Under Review'
        self.app.save()
        self.assertEqual(
            HighSchoolApplicationCourseReview.objects.filter(
                interested_course__highschool_application=self.app).count(), 1)

    def test_review_creation_alerts_reviewer(self):
        self.app.status = 'Under Review'
        self.app.save()
        self.assertEqual(
            Alert.objects.filter(
                recipient=self.admin_user,
                alert_type='new_school_application_pending_review').count(), 1)

    def test_review_update_marks_alert_read(self):
        self.app.status = 'Under Review'
        self.app.save()
        review = HighSchoolApplicationCourseReview.objects.first()
        review.status = 'Approved'
        review.save()
        alert = Alert.objects.get(recipient=self.admin_user,
                                  alert_type='new_school_application_pending_review')
        self.assertIsNotNone(alert.read_on)
