from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.urls import reverse

from cis.models.course import Cohort, Course

from new_school_application.new_school_application.models import (
    HighSchoolApplication,
    HighSchoolApplicationCourseReview,
    HighSchoolInterestedCourse,
    SchoolApplicationNote,
)

User = get_user_model()

try:
    from django_login_history.models import post_login as _login_history_post_login
except Exception:
    _login_history_post_login = None


class CEViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        if _login_history_post_login is not None:
            user_logged_in.disconnect(_login_history_post_login)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if _login_history_post_login is not None:
            user_logged_in.connect(_login_history_post_login)

    def setUp(self):
        self.user = User.objects.create_user(
            username='ce@example.com', email='ce@example.com', password='x')
        self.user.groups.add(Group.objects.get_or_create(name='ce')[0])
        self.client.force_login(self.user)
        self.app = HighSchoolApplication.objects.create(name='Test HS')

    def test_list_requires_ce_role(self):
        self.client.logout()
        resp = self.client.get(reverse('new_school_application_ce:index'))
        self.assertEqual(resp.status_code, 302)  # redirected to login

    def test_list_renders_for_ce(self):
        resp = self.client.get(reverse('new_school_application_ce:index'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('api_url', resp.context)

    def test_detail_renders(self):
        resp = self.client.get(
            reverse('new_school_application_ce:detail', args=[self.app.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('record', resp.context)

    def test_detail_is_xframe_exempt(self):
        resp = self.client.get(
            reverse('new_school_application_ce:detail', args=[self.app.id]))
        # @xframe_options_exempt prevents the DENY header so the page can be
        # embedded in the shared #details iframe modal.
        self.assertNotEqual(resp.get('X-Frame-Options'), 'DENY')

    def test_detail_context_has_modal_fields(self):
        resp = self.client.get(
            reverse('new_school_application_ce:detail', args=[self.app.id]))
        self.assertIn('available_courses', resp.context)
        self.assertIn('interested_course_ids', resp.context)
        self.assertIn('note_api_url', resp.context)
        self.assertIn('application_id=' + str(self.app.id), resp.context['note_api_url'])

    def _make_course(self, catalog_number='101', available=True):
        cohort = Cohort.objects.create(
            name='Co' + catalog_number, designator='CO' + catalog_number)
        return Course.objects.create(
            name='C' + catalog_number, title='Course ' + catalog_number,
            cohort=cohort, catalog_number=catalog_number, credit_hours=3,
            status='Active',
            meta={'available_for_new_schools': '1'} if available else {})

    def test_update_courses_adds_and_removes(self):
        c1 = self._make_course('101')
        c2 = self._make_course('102')
        HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app, course=c1)
        # post selecting only c2 → c1 removed, c2 added
        resp = self.client.post(
            reverse('new_school_application_ce:detail', args=[self.app.id]),
            {'action': 'update_courses', 'course': [str(c2.id)]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        ids = set(self.app.interested_courses.values_list('course_id', flat=True))
        self.assertEqual(ids, {c2.id})

    def test_update_courses_removes_interested_with_review(self):
        c1 = self._make_course('101')
        ic = HighSchoolInterestedCourse.objects.create(
            highschool_application=self.app, course=c1)
        HighSchoolApplicationCourseReview.objects.create(
            interested_course=ic, reviewer=self.user)
        # post empty selection → ic and its review removed (PROTECT respected)
        resp = self.client.post(
            reverse('new_school_application_ce:detail', args=[self.app.id]),
            {'action': 'update_courses'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.app.interested_courses.count(), 0)
        self.assertEqual(HighSchoolApplicationCourseReview.objects.count(), 0)

    def test_edit_application_action_updates_status(self):
        resp = self.client.post(
            reverse('new_school_application_ce:detail', args=[self.app.id]),
            {'action': 'edit_application', 'status': 'Under Review'})
        self.assertEqual(resp.status_code, 200)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'Under Review')

    def test_add_note_action(self):
        resp = self.client.post(
            reverse('new_school_application_ce:detail', args=[self.app.id]),
            {'action': 'add_note', 'message': 'a note'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            SchoolApplicationNote.objects.filter(highschool_application=self.app).count(), 1)

    def test_delete_cascades(self):
        SchoolApplicationNote.objects.create(highschool_application=self.app, message='n')
        resp = self.client.post(
            reverse('new_school_application_ce:delete', args=[self.app.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(HighSchoolApplication.objects.count(), 0)
        self.assertEqual(SchoolApplicationNote.objects.count(), 0)

    def test_delete_rejects_get(self):
        resp = self.client.get(
            reverse('new_school_application_ce:delete', args=[self.app.id]))
        self.assertEqual(resp.status_code, 405)
        self.assertEqual(HighSchoolApplication.objects.count(), 1)

    def test_api_returns_rows_for_ce(self):
        resp = self.client.get(
            reverse('new_school_application_ce:application-list') + '?format=datatables')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['recordsTotal'], 1)

    def test_api_blocks_non_ce(self):
        self.client.logout()
        other = User.objects.create_user(
            username='i@example.com', email='i@example.com', password='x')
        other.groups.add(Group.objects.get_or_create(name='instructor')[0])
        self.client.force_login(other)
        resp = self.client.get(
            reverse('new_school_application_ce:application-list') + '?format=datatables')
        self.assertEqual(resp.status_code, 403)

    def test_email_note_saves_note_and_targets_recipient(self):
        from unittest import mock
        from cis.models.settings import Setting
        from new_school_application.new_school_application.settings.new_school_application import (
            new_school_application as NSAS,
        )
        self.app.school_contacts = {'submitted_by': {'name': 'Jo', 'email': 'jo@example.com'}}
        self.app.save()
        NSAS().install()
        s = Setting.objects.get(key='new_school_application')
        s.value = {**s.value, 'is_active': 'Yes'}
        s.save()
        with mock.patch(
            'new_school_application.new_school_application.services.emails.send_html_mail'
        ) as send:
            resp = self.client.post(
                reverse('new_school_application_ce:detail', args=[self.app.id]),
                {'action': 'email_note', 'recipient': ['submitter'], 'message': 'Hello there'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        note = SchoolApplicationNote.objects.filter(
            highschool_application=self.app, type='to_submitter').first()
        self.assertIsNotNone(note)
        self.assertEqual(note.message, 'Hello there')
        self.assertTrue(send.called)
        self.assertIn('jo@example.com', send.call_args[0][4])

    def test_email_note_requires_message(self):
        resp = self.client.post(
            reverse('new_school_application_ce:detail', args=[self.app.id]),
            {'action': 'email_note', 'recipient': ['submitter']})
        self.assertEqual(resp.status_code, 400)
