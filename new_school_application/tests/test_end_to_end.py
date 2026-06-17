from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from cis.models.course import Cohort, Course, CourseAdministrator
from cis.models.highschool import HighSchool
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
)

User = get_user_model()


class EndToEndTest(TestCase):
    def test_full_lifecycle(self):
        # The HSAdministratorPosition post_save signal requires this group.
        Group.objects.get_or_create(name='highschool_admin')
        cohort = Cohort.objects.create(name='Co', designator='CO')
        course = Course.objects.create(
            name='C1', title='Course 1', cohort=cohort, catalog_number='101', credit_hours=3)
        reviewer = User.objects.create_user(
            username='r@example.com', email='r@example.com', password='x')
        CourseAdministrator.objects.create(
            user=reviewer, course=course, role='Administrator', status='Active')

        # 1. application created + course of interest
        app = HighSchoolApplication.objects.create(
            name='Lincoln High',
            information={'address': {'city': 'Town', 'state': 'WA', 'country': 'US'}},
            school_contacts={
                'submitted_by': {'name': 'Jo', 'email': 'jo@example.com'},
                'principal': {'name': 'Dr. Jane Roe', 'email': 'p@example.com'},
                'guidance': {'name': 'G', 'email': 'g@example.com'},
                'primary_contact': {'name': 'C', 'email': 'c@example.com'}},
            district_contacts={'superintendent': {'name': 'S', 'email': 's@example.com'}})
        HighSchoolInterestedCourse.objects.create(highschool_application=app, course=course)

        # 2. under review → reviewer assigned (signal)
        app.status = 'Under Review'
        app.save()
        review = HighSchoolApplicationCourseReview.objects.get(reviewer=reviewer)

        # 3. reviewer approves → all reviewed
        review.status = 'Approved'
        review.save()
        self.assertTrue(app.has_all_courses_reviewed())

        # 4. decision made → provision
        app.status = 'Decision Made'
        app.save()
        hs = app.import_as_highschool()
        self.assertEqual(HighSchool.objects.filter(name__iexact='Lincoln High').count(), 1)
        self.assertEqual(hs.status, 'Active')
