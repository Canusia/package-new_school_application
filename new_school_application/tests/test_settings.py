from django.test import TestCase

from cis.models.settings import Setting
from new_school_application.new_school_application.settings.new_school_application import (
    new_school_application as NSASettings,
)


class SettingsTest(TestCase):
    def test_from_db_empty_when_absent(self):
        self.assertEqual(NSASettings.from_db(), {})

    def test_install_creates_defaults(self):
        NSASettings().install()
        cfg = NSASettings.from_db()
        self.assertEqual(cfg['is_active'], 'No')
        self.assertIn('new_applicant_email', cfg)
        self.assertIn('app_ready_email', cfg)
        self.assertIn('app_approved_letter', cfg)
        self.assertEqual(Setting.objects.filter(key='new_school_application').count(), 1)

    def test_has_email_gate_fields(self):
        fields = NSASettings().fields
        self.assertIn('is_active', fields)
        self.assertIn('debug_email_list', fields)
