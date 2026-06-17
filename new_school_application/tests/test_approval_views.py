from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.urls import reverse

from cis.models.highschool import HighSchool
from new_school_application.new_school_application.models import HighSchoolApplication
from new_school_application.new_school_application.settings.new_school_application import (
    new_school_application as NSASettings,
)

User = get_user_model()
try:
    from django_login_history.models import post_login as _plh
except Exception:
    _plh = None


class ApprovalViewTest(TestCase):
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
        NSASettings().install()
        # The HSAdministratorPosition post_save signal requires this group.
        Group.objects.get_or_create(name='highschool_admin')
        self.user = User.objects.create_user(
            username='ce@example.com', email='ce@example.com', password='x')
        self.user.groups.add(Group.objects.get_or_create(name='ce')[0])
        self.client.force_login(self.user)
        self.app = HighSchoolApplication.objects.create(
            name='Lincoln High', status='Decision Made',
            information={'address': {'city': 'Town', 'state': 'WA', 'country': 'US'}},
            school_contacts={
                'submitted_by': {'name': 'Jo', 'email': 'jo@example.com'},
                'principal': {'name': 'Dr. Jane Roe', 'email': 'p@example.com'},
                'guidance': {'name': 'G', 'email': 'g@example.com'},
                'primary_contact': {'name': 'C', 'email': 'c@example.com'}},
            district_contacts={'superintendent': {'name': 'S', 'email': 's@example.com'}})

    @mock.patch('new_school_application.new_school_application.services.pdf.pdfkit')
    def test_approval_letter_pdf_download(self, pk):
        pk.from_string.return_value = b'%PDF-fake'
        resp = self.client.get(
            reverse('new_school_application_ce:approval_letter', args=[self.app.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_import_action_creates_highschool_and_redirects(self):
        resp = self.client.post(
            reverse('new_school_application_ce:detail', args=[self.app.id]),
            {'action': 'import_as_highschool'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        self.assertEqual(HighSchool.objects.filter(name__iexact='Lincoln High').count(), 1)

    def test_approval_letter_reverse_now_resolves(self):
        # approval_letter_url should now use the real route (not the detail fallback)
        self.assertIn('/approval_letter/', self.app.approval_letter_url)
