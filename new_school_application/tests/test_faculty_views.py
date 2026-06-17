from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.urls import reverse

from cis.models.course import Cohort, Course, CourseAdministrator
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
)

User = get_user_model()
try:
    from django_login_history.models import post_login as _plh
except Exception:
    _plh = None


class FacultyReviewViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        if _plh is not None:
            user_logged_in.disconnect(_plh)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if _plh is not None:
            user_logged_in.connect(_plh)

    def setUp(self):
        self.cohort = Cohort.objects.create(name='Co', designator='CO')
        self.course = Course.objects.create(
            name='C1', title='Course 1', cohort=self.cohort,
            catalog_number='101', credit_hours=3)
        self.user = User.objects.create_user(
            username='f@example.com', email='f@example.com', password='x')
        self.user.groups.add(Group.objects.get_or_create(name='faculty')[0])
        CourseAdministrator.objects.create(
            user=self.user, course=self.course, role='Administrator', status='Active')
        self.client.force_login(self.user)
        self.app = HighSchoolApplication.objects.create(name='Test HS')
        HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app, course=self.course)
        self.app.status = 'Under Review'
        self.app.save()  # signal assigns a review to self.user
        self.review = HighSchoolApplicationCourseReview.objects.get(reviewer=self.user)

    def test_reviews_page_renders(self):
        resp = self.client.get(reverse('new_school_application_faculty:reviews'))
        self.assertEqual(resp.status_code, 200)

    def test_api_lists_only_my_reviews(self):
        other = User.objects.create_user(
            username='o@example.com', email='o@example.com', password='x')
        ic2 = HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app,
            course=Course.objects.create(name='C2', title='C2', cohort=self.cohort,
                                         catalog_number='102', credit_hours=3))
        HighSchoolApplicationCourseReview.objects.create(interested_course=ic2, reviewer=other)
        resp = self.client.get(
            reverse('new_school_application_faculty:review-list') + '?format=datatables')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['recordsTotal'], 1)  # only my review

    def test_submit_review_updates_status(self):
        resp = self.client.post(reverse('new_school_application_faculty:submit_review'), {
            'action': 'submit_review', 'decision': 'Approved', 'comment': 'ok',
            'application_course_review_id': str(self.review.id)})
        self.assertEqual(resp.status_code, 200)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, 'Approved')

    def test_submit_review_rejects_foreign_review(self):
        other = User.objects.create_user(
            username='o2@example.com', email='o2@example.com', password='x')
        ic2 = HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app,
            course=Course.objects.create(name='C3', title='C3', cohort=self.cohort,
                                         catalog_number='103', credit_hours=3))
        foreign = HighSchoolApplicationCourseReview.objects.create(
            interested_course=ic2, reviewer=other)
        resp = self.client.post(reverse('new_school_application_faculty:submit_review'), {
            'action': 'submit_review', 'decision': 'Approved', 'comment': 'x',
            'application_course_review_id': str(foreign.id)})
        self.assertEqual(resp.status_code, 403)
