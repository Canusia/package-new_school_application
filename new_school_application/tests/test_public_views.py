from django.test import TestCase
from django.urls import reverse

from new_school_application.new_school_application.models import HighSchoolApplication


class PublicIntakeViewTest(TestCase):
    def test_step1_get_renders(self):
        resp = self.client.get(reverse('new_school_application:apply'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)
        # The form must actually render into the page body (guards against the
        # template extending a block name the base template doesn't render).
        self.assertContains(resp, 'name="highschool_name"')
        self.assertContains(resp, '<form')

    def test_step1_post_creates_record_and_redirects_to_step2(self):
        # Anonymous public submission. The container sets RECAPTCHA_TESTING=True,
        # so settings monkeypatches recaptcha validation to always-pass when a
        # 'g-recaptcha-response' value is present — exercising the real public path.
        post = {
            'your_name': 'Jane Doe', 'your_email': 'jane@example.com',
            'highschool_name': 'Test HS', 'highschool_code': '',
            'highschool_address': '1 Main St', 'highschool_city': 'Town',
            'highschool_state': 'WA', 'highschool_postal_code': '99001',
            'highschool_phone': '555-1212', 'highschool_fax': '555-1213',
            'highschool_country': 'United States',
            'principal_name': 'P', 'principal_email': 'p@example.com',
            'primary_contact_name': 'C', 'primary_contact_email': 'c@example.com',
            'guidance_name': 'G', 'guidance_email': 'g@example.com',
            'district_name': 'D', 'superintendent_name': 'S',
            'superintendent_email': 's@example.com', 'action': 'part_1',
            'g-recaptcha-response': 'PASSED',
        }
        resp = self.client.post(reverse('new_school_application:apply'), post)
        self.assertEqual(HighSchoolApplication.objects.count(), 1)
        record = HighSchoolApplication.objects.first()
        self.assertRedirects(
            resp,
            reverse('new_school_application:apply_courses', args=[record.id]),
            fetch_redirect_response=False,
        )

    def test_step2_get_renders(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        resp = self.client.get(
            reverse('new_school_application:apply_courses', args=[app.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('record', resp.context)
        self.assertIn('available_courses', resp.context)
        self.assertContains(resp, '<form')  # body block must render

    def test_flagged_course_without_stream_is_listed(self):
        from cis.models.course import Cohort, Course
        cohort = Cohort.objects.create(name='Co', designator='CO')
        course = Course.objects.create(
            name='C1', title='Course 1', cohort=cohort, catalog_number='101',
            credit_hours=3, status='Active', meta={'available_for_new_schools': '1'})
        # course has NO stream assigned
        app = HighSchoolApplication.objects.create(name='Test HS')
        resp = self.client.get(
            reverse('new_school_application:apply_courses', args=[app.id]))
        ids = [str(c.id) for c in resp.context['available_courses']]
        self.assertIn(str(course.id), ids)
        self.assertContains(resp, str(course.id))

    def test_step2_post_rejected_when_not_editable(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        app.status = 'Under Review'
        app.save()
        resp = self.client.post(
            reverse('new_school_application:apply_courses', args=[app.id]),
            {'action': 'part_2'})
        self.assertRedirects(resp, reverse('index'), fetch_redirect_response=False)
        app.refresh_from_db()
        self.assertEqual(app.status, 'Under Review')
        self.assertEqual(app.interested_courses.count(), 0)
