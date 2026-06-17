from types import SimpleNamespace

from django.test import TestCase

from new_school_application.new_school_application.forms.ce import (
    HighSchoolApplicationEditForm,
)
from new_school_application.new_school_application.models import HighSchoolApplication


class HighSchoolApplicationEditFormTest(TestCase):
    def setUp(self):
        self.app = HighSchoolApplication.objects.create(name='Test HS')

    def test_initial_from_record(self):
        form = HighSchoolApplicationEditForm(self.app)
        self.assertEqual(form.fields['status'].initial, 'In Progress')

    def test_save_updates_status_and_checklist(self):
        form = HighSchoolApplicationEditForm(
            self.app,
            {'status': 'Under Review', 'checklist': ['Sent Materials'], 'action': 'edit_application'},
        )
        self.assertTrue(form.is_valid(), form.errors)
        request = SimpleNamespace(FILES={})
        record = form.save(request, self.app)
        record.refresh_from_db()
        self.assertEqual(record.status, 'Under Review')
        self.assertEqual(record.information['checklist'], ['Sent Materials'])
