from django.contrib.auth import get_user_model
from django.test import TestCase

from cis.models.course import Cohort, Course, CourseAdministrator
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
)

User = get_user_model()


class ReviewerAssignmentTest(TestCase):
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

    def test_add_reviewers_creates_review_per_course_admin(self):
        self.app.add_reviewers()
        reviews = HighSchoolApplicationCourseReview.objects.filter(
            interested_course__highschool_application=self.app)
        self.assertEqual(reviews.count(), 1)
        self.assertEqual(reviews.first().reviewer_id, self.admin_user.id)

    def test_add_reviewers_is_idempotent(self):
        self.app.add_reviewers()
        self.app.add_reviewers()
        self.assertEqual(
            HighSchoolApplicationCourseReview.objects.filter(
                interested_course__highschool_application=self.app).count(), 1)

    def test_has_all_courses_reviewed(self):
        self.app.add_reviewers()
        self.assertFalse(self.app.has_all_courses_reviewed())  # Pending
        review = HighSchoolApplicationCourseReview.objects.first()
        review.status = 'Approved'
        review.save()
        self.assertTrue(self.app.has_all_courses_reviewed())

    def test_user_has_pending_reviews(self):
        self.app.add_reviewers()
        self.assertTrue(self.app.user_has_pending_reviews(self.admin_user))
        other = User.objects.create_user(
            username='o@example.com', email='o@example.com', password='x')
        self.assertFalse(self.app.user_has_pending_reviews(other))
