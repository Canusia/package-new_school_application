from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.urls import reverse

from new_school_application.new_school_application.models import (
    HighSchoolApplication, SchoolApplicationNote,
)

User = get_user_model()

try:
    from django_login_history.models import post_login as _login_history_post_login
except Exception:
    _login_history_post_login = None


class NoteApiTest(TestCase):
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
        self.app1 = HighSchoolApplication.objects.create(name='App One')
        self.app2 = HighSchoolApplication.objects.create(name='App Two')
        SchoolApplicationNote.objects.create(
            highschool_application=self.app1, message='n1', created_by=self.user)
        SchoolApplicationNote.objects.create(
            highschool_application=self.app1, message='n2', created_by=self.user)
        SchoolApplicationNote.objects.create(
            highschool_application=self.app2, message='other')

    def _url(self, app_id):
        return (reverse('new_school_application_ce:note-list')
                + '?application_id=' + str(app_id) + '&format=datatables')

    def test_notes_filtered_by_application(self):
        resp = self.client.get(self._url(self.app1.id))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['recordsTotal'], 2)
        self.assertEqual(len(data['data']), 2)

    def test_notes_other_application(self):
        resp = self.client.get(self._url(self.app2.id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['recordsTotal'], 1)

    def test_created_by_display(self):
        resp = self.client.get(self._url(self.app1.id))
        row = resp.json()['data'][0]
        self.assertIn('created_by_display', row)
        self.assertIn('created_on', row)

    def test_created_by_display_falls_back_to_dash(self):
        resp = self.client.get(self._url(self.app2.id))
        row = resp.json()['data'][0]
        self.assertEqual(row['created_by_display'], '—')

    def test_api_blocks_non_ce(self):
        self.client.logout()
        other = User.objects.create_user(
            username='i@example.com', email='i@example.com', password='x')
        other.groups.add(Group.objects.get_or_create(name='instructor')[0])
        self.client.force_login(other)
        resp = self.client.get(self._url(self.app1.id))
        self.assertEqual(resp.status_code, 403)

    def test_malformed_application_id_does_not_500(self):
        resp = self.client.get(
            reverse('new_school_application_ce:note-list')
            + '?application_id=not-a-uuid&format=datatables')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['recordsTotal'], 0)
