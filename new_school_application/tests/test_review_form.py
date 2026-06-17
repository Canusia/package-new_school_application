from django.contrib.auth import get_user_model
from django.test import TestCase

from cis.models.course import Cohort, Course, CourseAdministrator
from new_school_application.new_school_application.forms.ce import (
    HighSchoolApplicationEditForm,
)
from new_school_application.new_school_application.forms.faculty import (
    HighSchoolCourseReviewForm,
)
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
)

User = get_user_model()


class ReviewFormTest(TestCase):
    def setUp(self):
        self.cohort = Cohort.objects.create(name='Co', designator='CO')
        self.course = Course.objects.create(
            name='C1', title='Course 1', cohort=self.cohort,
            catalog_number='101', credit_hours=3)
        self.user = User.objects.create_user(
            username='f@example.com', email='f@example.com', password='x')
        self.app = HighSchoolApplication.objects.create(name='Test HS')
        ic = HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app, course=self.course)
        self.review = HighSchoolApplicationCourseReview.objects.create(
            interested_course=ic, reviewer=self.user)

    def test_comment_required_for_not_approved(self):
        form = HighSchoolCourseReviewForm(self.review, {
            'decision': 'Not Approved', 'comment': '',
            'application_course_review_id': str(self.review.id), 'action': 'submit_review'})
        self.assertFalse(form.is_valid())

    def test_save_updates_status_and_appends_note(self):
        form = HighSchoolCourseReviewForm(self.review, {
            'decision': 'Approved', 'comment': 'looks good',
            'application_course_review_id': str(self.review.id), 'action': 'submit_review'})
        self.assertTrue(form.is_valid(), form.errors)
        review = form.save()
        review.refresh_from_db()
        self.assertEqual(review.status, 'Approved')
        self.assertIn('looks good', review.misc_info['note'])

    def test_comment_is_html_escaped(self):
        form = HighSchoolCourseReviewForm(self.review, {
            'decision': 'Approved', 'comment': '<script>alert(1)</script>',
            'application_course_review_id': str(self.review.id), 'action': 'submit_review'})
        self.assertTrue(form.is_valid(), form.errors)
        review = form.save()
        review.refresh_from_db()
        self.assertNotIn('<script>', review.misc_info['note'])
        self.assertIn('&lt;script&gt;', review.misc_info['note'])


class EditFormDecisionGuardTest(TestCase):
    def setUp(self):
        self.cohort = Cohort.objects.create(name='Co', designator='CO')
        self.course = Course.objects.create(
            name='C1', title='Course 1', cohort=self.cohort,
            catalog_number='101', credit_hours=3)
        self.user = User.objects.create_user(
            username='f2@example.com', email='f2@example.com', password='x')
        self.app = HighSchoolApplication.objects.create(name='Test HS')
        ic = HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app, course=self.course)
        HighSchoolApplicationCourseReview.objects.create(
            interested_course=ic, reviewer=self.user)  # Pending

    def test_decision_made_blocked_while_reviews_pending(self):
        form = HighSchoolApplicationEditForm(
            self.app, {'status': 'Decision Made', 'action': 'edit_application'})
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
