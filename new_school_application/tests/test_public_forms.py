from types import SimpleNamespace
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from cis.models.course import Cohort, Course
from new_school_application.new_school_application.forms.public import (
    HighSchoolApplicationForm,
    HighSchoolCourseForm,
)
from new_school_application.new_school_application.models import (
    HighSchoolApplication,
    HighSchoolInterestedCourse,
)


def _step1_post(country='United States'):
    return {
        'your_name': 'Jane Doe',
        'your_email': 'jane@example.com',
        'highschool_name': 'Test HS',
        'highschool_code': 'CEEB1',
        'highschool_address': '1 Main St',
        'highschool_city': 'Town',
        'highschool_state': 'WA',
        'highschool_postal_code': '99001',
        'highschool_phone': '555-1212',
        'highschool_fax': '555-1213',
        'highschool_country': country,
        'principal_name': 'P Rincipal',
        'principal_email': 'principal@example.com',
        'primary_contact_name': 'Prim Contact',
        'primary_contact_email': 'prim@example.com',
        'guidance_name': 'Gee Idance',
        'guidance_email': 'guidance@example.com',
        'district_name': 'Test District',
        'superintendent_name': 'Sue Per',
        'superintendent_email': 'super@example.com',
        'action': 'part_1',
    }


class HighSchoolApplicationFormTest(TestCase):
    def test_anonymous_form_has_captcha(self):
        form = HighSchoolApplicationForm(request=None)
        self.assertIn('captcha', form.fields)

    def test_ce_admin_form_drops_captcha(self):
        request = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=True, is_anonymous=False,
                                 get_roles=lambda: ['ce']))
        form = HighSchoolApplicationForm(request=request)
        self.assertNotIn('captcha', form.fields)

    def test_save_creates_application_with_serialized_json(self):
        # bind without captcha by simulating a CE-admin request (skips recaptcha)
        request = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=True, is_anonymous=False,
                                 get_roles=lambda: ['ce']))
        form = HighSchoolApplicationForm(request, None, _step1_post('United States'))
        self.assertTrue(form.is_valid(), form.errors)
        app = form.save()

        self.assertIsInstance(app, HighSchoolApplication)
        self.assertEqual(app.name, 'Test HS')
        self.assertEqual(app.district, 'Test District')
        self.assertEqual(app.status, 'In Progress')
        self.assertEqual(app.school_contacts['submitted_by']['email'], 'jane@example.com')
        self.assertEqual(app.school_contacts['principal']['name'], 'P Rincipal')
        self.assertEqual(app.school_contacts['primary_contact']['email'], 'prim@example.com')
        self.assertEqual(app.school_contacts['guidance']['name'], 'Gee Idance')
        self.assertEqual(app.district_contacts['superintendent']['email'], 'super@example.com')
        self.assertEqual(app.information['address']['city'], 'Town')
        self.assertEqual(app.information['address']['country'], 'United States')


class HighSchoolCourseFormTest(TestCase):
    def setUp(self):
        self.cohort = Cohort.objects.create(name='Co', designator='CO')
        self.course = Course.objects.create(
            name='C1', title='Course 1', cohort=self.cohort,
            catalog_number='101', credit_hours=3,
        )
        self.app = HighSchoolApplication.objects.create(name='Test HS')

    def _post(self, course_ids):
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.update({
            'faculty': '2',
            'student_eligibility': 'GPA 3.0',
            'students_in_course': '20',
            'students_annually': '15',
            'course_fit': 'fits well',
            'implementation': 'positive',
            'hear_about_us': 'Other',
            'hear_about_us_from': 'a colleague',
            'other_course': '',
            'action': 'part_2',
        })
        for cid in course_ids:
            qd.appendlist('course', str(cid))
        qd.setlist('other_college_course', ['AP'])
        return qd

    def test_requires_at_least_one_course(self):
        form = HighSchoolCourseForm(None, None, self._post([]))
        self.assertFalse(form.is_valid())
        self.assertIn('course', form.errors)

    def test_save_creates_interested_courses_and_sets_under_review(self):
        files = {'course_guide': SimpleUploadedFile(
            'guide.pdf', b'%PDF-1.4 fake', content_type='application/pdf')}
        form = HighSchoolCourseForm(None, None, self._post([self.course.id]), files)
        self.assertTrue(form.is_valid(), form.errors)

        # Avoid a real S3 upload: the model's course_guide uses PrivateMediaStorage.
        storage = HighSchoolApplication._meta.get_field('course_guide').storage
        with mock.patch.object(
            storage, 'save',
            return_value='new_school_application/course_guides/guide.pdf',
        ):
            record = form.save(self.app)

        self.assertEqual(record.status, 'Under Review')
        self.assertEqual(record.information['faculty'], '2')
        self.assertEqual(record.information['course_fit'], 'fits well')
        self.assertEqual(list(record.other_college_courses), ['AP'])
        self.assertEqual(
            HighSchoolInterestedCourse.objects.filter(highschool_application=record).count(),
            1,
        )
        self.assertEqual(
            HighSchoolInterestedCourse.objects.get(highschool_application=record).course_id,
            self.course.id,
        )
