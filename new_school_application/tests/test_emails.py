from unittest import mock

from django.test import TestCase

from new_school_application.new_school_application.settings.new_school_application import (
    new_school_application as NSASettings,
)
from new_school_application.new_school_application.services import emails


class SendAppEmailTest(TestCase):
    def _set(self, **over):
        NSASettings().install()
        from cis.models.settings import Setting
        s = Setting.objects.get(key='new_school_application')
        s.value = {**s.value, **over}
        s.save()

    @mock.patch.object(emails, 'send_html_mail')
    def test_suppressed_when_no(self, send):
        self._set(is_active='No')
        emails.send_app_email('S', 'body', ['a@example.com'])
        send.assert_not_called()

    @mock.patch.object(emails, 'send_html_mail')
    def test_redirects_when_debug(self, send):
        self._set(is_active='Debug', debug_email_list='dbg@example.com')
        emails.send_app_email('S', 'body', ['a@example.com'])
        self.assertTrue(send.called)
        self.assertEqual(send.call_args[0][4], ['dbg@example.com'])

    @mock.patch.object(emails, 'send_html_mail')
    def test_sends_live_when_yes(self, send):
        self._set(is_active='Yes')
        emails.send_app_email('S', 'body', ['a@example.com'])
        self.assertTrue(send.called)
        self.assertEqual(send.call_args[0][4], ['a@example.com'])
