from django.test import TestCase

from cis.models.course import Cohort, Course
from new_school_application.new_school_application.models import (
    HighSchoolApplication, HighSchoolInterestedCourse,
)
from new_school_application.new_school_application.serializers.ce import (
    ApplicationListSerializer,
)


class ApplicationListSerializerTest(TestCase):
    def setUp(self):
        self.app = HighSchoolApplication.objects.create(
            name='Test HS', district='D',
            information={'address': {'state': 'WA'}},
            other_college_courses=['AP', 'IB'],
        )
        cohort = Cohort.objects.create(name='Co', designator='CO')
        course = Course.objects.create(
            name='C1', title='Course 1', cohort=cohort,
            catalog_number='101', credit_hours=3)
        HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app, course=course)

    def test_serialized_fields(self):
        data = ApplicationListSerializer(self.app).data
        self.assertEqual(data['name'], 'Test HS')
        self.assertEqual(data['status'], 'In Progress')
        self.assertEqual(data['state'], 'WA')
        self.assertEqual(data['other_college_courses_display'], 'AP, IB')
        self.assertEqual(data['interested_courses_count'], 1)
        self.assertIn('/ce/new_school_applications/', data['detail_url'])
