from django.conf import settings as django_settings
from django.template import Context, Template
from django.template.loader import render_to_string

from mailer import send_html_mail

from ..settings.new_school_application import new_school_application as NSASettings


def _cfg():
    return NSASettings.from_db()


def send_app_email(subject, message_text, recipients):
    """Gate + send. is_active No→suppress, Debug/DEBUG→debug list, Yes→recipients."""
    cfg = _cfg()
    is_active = cfg.get('is_active', 'No')
    if is_active == 'No':
        return

    to = [r for r in (recipients or []) if r]
    if is_active == 'Debug' or getattr(django_settings, 'DEBUG', False):
        to = [e.strip() for e in (cfg.get('debug_email_list') or '').split(',') if e.strip()]
    if not to:
        return

    html_body = render_to_string('cis/email.html', {'message': message_text})
    send_html_mail(subject, message_text, html_body,
                   django_settings.DEFAULT_FROM_EMAIL, to)


def _render(template_str, ctx):
    return Template(template_str or '').render(Context(ctx))


def notify_application_created(app):
    """Welcome the submitter + notify internal recipient. Called on create."""
    cfg = _cfg()
    sc = app.school_contacts or {}
    submitter = sc.get('submitted_by', {})
    send_app_email(
        cfg.get('new_applicant_email_subject', ''),
        _render(cfg.get('new_applicant_email'), {
            'submitter_name': submitter.get('name', ''),
            'submitter_email': submitter.get('email', '')}),
        [submitter.get('email')],
    )
    internal = [e.strip() for e in (cfg.get('app_started_email_recipient') or '').split(',') if e.strip()]
    if internal:
        state = (app.information or {}).get('address', {}).get('state', '')
        send_app_email(
            cfg.get('app_submitted_email_subject', ''),
            _render(cfg.get('app_started_email'), {'highschool': app.name, 'highschool_state': state}),
            internal,
        )


def notify_application_submitted(app):
    """Internal notice when the application moves to Under Review."""
    cfg = _cfg()
    internal = [e.strip() for e in (cfg.get('app_started_email_recipient') or '').split(',') if e.strip()]
    if not internal:
        return
    state = (app.information or {}).get('address', {}).get('state', '')
    send_app_email(
        cfg.get('app_submitted_email_subject', ''),
        _render(cfg.get('app_submitted_email'), {'highschool': app.name, 'highschool_state': state}),
        internal,
    )


def notify_reviewer_assigned(review):
    """Email a reviewer that an application awaits their course review."""
    cfg = _cfg()
    app = review.interested_course.highschool_application
    send_app_email(
        cfg.get('app_ready_email_subject', ''),
        _render(cfg.get('app_ready_email'), {
            'highschool': app.name, 'application_url': app.ce_url}),
        [review.reviewer.email],
    )


def notify_review_decided(review):
    """Notify internal recipient that a reviewer submitted a decision."""
    cfg = _cfg()
    app = review.interested_course.highschool_application
    internal = [e.strip() for e in (cfg.get('app_started_email_recipient') or '').split(',') if e.strip()]
    if not internal:
        return
    send_app_email(
        cfg.get('app_reviewed_email_subject', ''),
        _render(cfg.get('app_reviewed_email'), {
            'highschool': app.name, 'reviewer_name': str(review.reviewer),
            'reviewer_decision': review.status,
            'reviewer_comment': (review.misc_info or {}).get('note', '')}),
        internal,
    )


def send_application_approved(app, recipients):
    """Render + send the approval email to the chosen recipients."""
    cfg = _cfg()
    sc = app.school_contacts or {}
    body = _render(cfg.get('app_approved_email'), {
        'highschool_name': app.name,
        'principal_name': sc.get('principal', {}).get('name', ''),
        'approval_letter_url': app.approval_letter_url,
        'submitter_name': sc.get('submitted_by', {}).get('name', ''),
    })
    send_app_email(cfg.get('app_approved_email_subject', ''), body, recipients)


def send_applicant_note(app, recipients, message):
    """Email a free-text note authored by CE staff to the school's contacts.

    The note text is the message body; it is also persisted as a
    SchoolApplicationNote by the caller so it shows in the Notes tab.
    """
    cfg = _cfg()
    subject = cfg.get('applicant_note_subject') or (
        'A message regarding your application — %s' % app.name)
    send_app_email(subject, message, recipients)
