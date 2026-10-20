"""The public intake form's captcha comes from the tenant's cis.captcha (ewu#87)."""
from django.test import SimpleTestCase

from cis.captcha import CaptchaField


class CaptchaShimTests(SimpleTestCase):

    def test_shim_reexports_the_tenant_field(self):
        from new_school_application.new_school_application import captcha
        self.assertIs(captcha.CaptchaField, CaptchaField)

    def test_public_form_uses_it(self):
        from new_school_application.new_school_application.forms.public import HighSchoolApplicationForm
        self.assertIsInstance(HighSchoolApplicationForm.base_fields['captcha'], CaptchaField)
