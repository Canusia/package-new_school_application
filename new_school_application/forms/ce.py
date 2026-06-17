from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe

from ..models import APPLICATION_STATUS_OPTIONS


class HighSchoolApplicationEditForm(forms.Form):
    """CE staff form: change status + checklist + (optional) course-guide file."""

    action = forms.CharField(required=False, widget=forms.HiddenInput())
    status = forms.ChoiceField(required=True, label='Status',
                               choices=APPLICATION_STATUS_OPTIONS)
    checklist = forms.MultipleChoiceField(
        required=False, label='Checklist', help_text='If approved',
        widget=forms.CheckboxSelectMultiple(),
        choices=[('Sent Materials', 'Sent Materials')],
    )
    file = forms.FileField(label='Course Guide', required=False, widget=forms.FileInput())

    def __init__(self, record, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.record = record
        if record:
            self.fields['status'].initial = record.status
            self.fields['checklist'].initial = (record.information or {}).get('checklist')
            if record.course_guide:
                self.fields['file'].label = mark_safe(
                    'Course Guide<br><small><a href="%s">Download current file</a> '
                    'or upload new</small>' % record.course_guide.url)

    def clean(self):
        data = super().clean()
        if (self.record and data.get('status') == 'Decision Made'
                and not self.record.has_all_courses_reviewed()):
            raise ValidationError(
                'Cannot mark Decision Made while course reviews are pending.',
                code='invalid')
        return data

    def save(self, request, record, commit=True):
        data = self.cleaned_data
        if getattr(request, 'FILES', None):
            uploaded = request.FILES.get('file')
            if uploaded:
                record.course_guide = uploaded
        record.status = data.get('status')
        if not record.information:
            record.information = {}
        record.information['checklist'] = data.get('checklist')
        if commit:
            record.save()
        return record


_NOTIF_CHOICES = [
    ('Submitter', 'Submitter'),
    ('Principal', 'Principal'),
    ('Primary Contact', 'Primary Contact'),
    ('Dir. of Guidance', 'Dir. of Guidance'),
    ('Superintendent', 'Superintendent'),
]


class HighSchoolApplicationApprovalNotificationForm(forms.Form):
    action = forms.CharField(required=False, widget=forms.HiddenInput())
    notif_checklist = forms.MultipleChoiceField(
        required=True, label='Who should be notified',
        widget=forms.CheckboxSelectMultiple(), choices=_NOTIF_CHOICES)

    def __init__(self, record, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.record = record

    def clean(self):
        data = super().clean()
        if self.record and not self.record.has_application_reviewed():
            raise ValidationError(
                'Notifications can only be sent when the application is "Decision Made".',
                code='invalid')
        if self.record and not self.record.has_all_courses_reviewed():
            raise ValidationError(
                'One or more courses have not been fully reviewed.', code='invalid')
        return data

    def save(self, request, record, commit=True):
        data = self.cleaned_data
        sc = record.school_contacts or {}
        dc = record.district_contacts or {}
        chosen = data.get('notif_checklist', [])
        role_map = {
            'Submitter': sc.get('submitted_by', {}).get('email'),
            'Principal': sc.get('principal', {}).get('email'),
            'Primary Contact': sc.get('primary_contact', {}).get('email'),
            'Dir. of Guidance': sc.get('guidance', {}).get('email'),
            'Superintendent': dc.get('superintendent', {}).get('email'),
        }
        recipients = [role_map[c] for c in chosen if role_map.get(c)]
        record.notify_application_approved(recipients)
        record.add_note(
            getattr(request, 'user', None),
            'Sent application approval notification to ' + ', '.join(recipients))
        record.mark_as_approval_notification(request)
        return record
