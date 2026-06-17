from unittest import mock

from django.test import TestCase

from new_school_application.new_school_application.models import HighSchoolApplication
from new_school_application.new_school_application.services import pdf
from new_school_application.new_school_application.settings.new_school_application import (
    new_school_application as NSASettings,
)


class ApprovalPdfTest(TestCase):
    def setUp(self):
        NSASettings().install()
        self.app = HighSchoolApplication.objects.create(
            name='Lincoln HS',
            school_contacts={'principal': {'name': 'Dr. Jane Roe', 'email': 'p@example.com'}})

    def test_build_letter_html_renders_vars(self):
        html = pdf.build_approval_letter_html(self.app)
        self.assertIn('Lincoln HS', html)

    @mock.patch('new_school_application.new_school_application.services.pdf.pdfkit')
    def test_approval_letter_pdf_returns_bytes(self, pk):
        pk.from_string.return_value = b'%PDF-fake'
        out = pdf.approval_letter_pdf(self.app)
        self.assertEqual(out, b'%PDF-fake')
        self.assertTrue(pk.from_string.called)
