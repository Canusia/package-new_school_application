"""The captcha field new_school_application's public intake form uses (ewu#87).

A tenant that has moved off Google reCAPTCHA provides
``cis.captcha.CaptchaField`` (ALTCHA; see the pass tenant, 8fd3173); every
other tenant keeps django-recaptcha, which it already installs itself.

Checked with ``find_spec`` rather than ``try/except ImportError`` so that a
broken tenant ``cis/captcha.py`` (e.g. django-altcha missing) raises instead
of silently falling back to reCAPTCHA.
"""
import importlib.util


def _has_tenant_captcha():
    try:
        return importlib.util.find_spec('cis.captcha') is not None
    except ModuleNotFoundError:
        return False


if _has_tenant_captcha():
    from cis.captcha import CaptchaField  # noqa: F401
else:
    from django_recaptcha.fields import ReCaptchaField as CaptchaField  # noqa: F401
