import pdfkit

from django.template import Context, Template
from django.template.loader import get_template

from ..settings.new_school_application import new_school_application as NSASettings


def _principal_firstname(app):
    """Best-effort given name: drop a leading honorific (e.g. 'Dr.'), take the
    first remaining token."""
    name = (app.school_contacts or {}).get('principal', {}).get('name', '')
    tokens = [t for t in name.split() if not t.endswith('.')]
    if tokens:
        return tokens[0]
    return name.split()[0] if name else ''


def build_approval_letter_html(app):
    """Render the inner approval-letter HTML from the settings template (no pdfkit)."""
    cfg = NSASettings.from_db()
    sc = app.school_contacts or {}
    dc = app.district_contacts or {}
    addr = (app.information or {}).get('address', {})
    tmpl = Template(cfg.get('app_approved_letter') or '')
    return tmpl.render(Context({
        'highschool_name': app.name,
        'highschool_state': addr.get('state', ''),
        'highschool_city': addr.get('city', ''),
        'highschool_address': addr.get('address', ''),
        'principal_name': sc.get('principal', {}).get('name', ''),
        'principal_firstname': _principal_firstname(app),
        'principal_email': sc.get('principal', {}).get('email', ''),
        'primary_contact_name': sc.get('primary_contact', {}).get('name', ''),
        'director_guidance_name': sc.get('guidance', {}).get('name', ''),
        'superintendent_name': dc.get('superintendent', {}).get('name', ''),
        'approval_letter_url': app.approval_letter_url,
        'interested_courses_status': app.interested_courses_status,
    }))


def approval_letter_pdf(app):
    """Return the approval letter as PDF bytes (wrapped in cis/print_base.html)."""
    inner = build_approval_letter_html(app)
    html = get_template('cis/print_base.html').render({'main_content': inner})
    return pdfkit.from_string(html, False, {'page-size': 'Letter'})
