from django import forms
from django.http import JsonResponse
from django.urls import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.models.settings import Setting


_ACTIVE_CHOICES = [('Yes', 'Yes'), ('Debug', 'Debug'), ('No', 'No')]


class new_school_application(forms.Form):
    key = 'new_school_application'

    # --- email gate ---
    is_active = forms.ChoiceField(
        choices=_ACTIVE_CHOICES, label='Email Status',
        help_text='Yes = send live; Debug = redirect to debug list; No = suppress.')
    debug_email_list = forms.CharField(
        max_length=500, required=False, label='Debug Email List',
        help_text='Comma-separated; used when Email Status is Debug.')

    # --- page headers ---
    app_start_page_header = forms.CharField(
        widget=forms.Textarea, required=False, label='Application Start Page Header')
    app_course_page_header = forms.CharField(
        widget=forms.Textarea, required=False, label='Course Selection Page Header')

    # --- internal recipient ---
    app_started_email_recipient = forms.CharField(
        max_length=500, required=False, label='Internal Notification Recipient(s)',
        help_text='Comma-separated. Receives new/submitted/reviewed notices.')

    # --- welcome to submitter (on create) ---
    new_applicant_email_subject = forms.CharField(
        max_length=200, required=False, label='Applicant Welcome - Subject')
    new_applicant_email = forms.CharField(
        widget=forms.Textarea, required=False, label='Applicant Welcome - Body',
        help_text='Vars: {{submitter_name}}, {{submitter_email}}')

    # --- internal "started" (on create) ---
    app_started_email = forms.CharField(
        widget=forms.Textarea, required=False, label='Application Started (Internal) - Body',
        help_text='Vars: {{highschool}}, {{highschool_state}}')

    # --- submitted / under review ---
    app_submitted_email_subject = forms.CharField(
        max_length=200, required=False, label='Application Submitted - Subject')
    app_submitted_email = forms.CharField(
        widget=forms.Textarea, required=False, label='Application Submitted - Body',
        help_text='Vars: {{highschool}}, {{highschool_state}}')

    # --- reviewer assigned ---
    app_ready_email_subject = forms.CharField(
        max_length=200, required=False, label='Reviewer Assigned - Subject')
    app_ready_email = forms.CharField(
        widget=forms.Textarea, required=False, label='Reviewer Assigned - Body',
        help_text='Vars: {{highschool}}, {{application_url}}')

    # --- review decided ---
    app_reviewed_email_subject = forms.CharField(
        max_length=200, required=False, label='Review Submitted - Subject')
    app_reviewed_email = forms.CharField(
        widget=forms.Textarea, required=False, label='Review Submitted - Body',
        help_text='Vars: {{highschool}}, {{reviewer_name}}, {{reviewer_decision}}, {{reviewer_comment}}')

    # --- approved (email + letter; used in Plan F) ---
    app_approved_email_subject = forms.CharField(
        max_length=200, required=False, label='Approved - Subject')
    app_approved_email = forms.CharField(
        widget=forms.Textarea, required=False, label='Approved - Email Body',
        help_text='Vars: {{highschool_name}}, {{principal_name}}, {{approval_letter_url}}')
    app_approved_letter = forms.CharField(
        widget=forms.Textarea, required=False, label='Approval Letter (PDF) Template',
        help_text='Supports HTML. Vars: {{highschool_name}}, {{principal_name}}, '
                  '{{principal_firstname}}, {{interested_courses_status}}, etc.')

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if request is not None:
            self.request = request
            self.helper = FormHelper()
            self.helper.attrs = {'target': '_blank'}
            self.helper.form_method = 'POST'
            self.helper.form_action = reverse_lazy(
                'setting:run_record', args=[request.GET.get('report_id')])
            self.helper.add_input(Submit('submit', 'Save Setting'))

    @classmethod
    def from_db(cls):
        try:
            return Setting.objects.get(key=cls.key).value
        except Setting.DoesNotExist:
            return {}

    def _defaults(self):
        return {
            'is_active': 'No',
            'debug_email_list': '',
            'app_start_page_header': '',
            'app_course_page_header': '',
            'app_started_email_recipient': '',
            'new_applicant_email_subject': 'Your application has been started',
            'new_applicant_email': 'Hello {{submitter_name}}, thank you for starting your application.',
            'app_started_email': 'A new application was started by {{highschool}} ({{highschool_state}}).',
            'app_submitted_email_subject': 'Application submitted',
            'app_submitted_email': 'Application submitted by {{highschool}} ({{highschool_state}}).',
            'app_ready_email_subject': 'An application is ready for your review',
            'app_ready_email': 'An application from {{highschool}} is ready for review: {{application_url}}',
            'app_reviewed_email_subject': 'A course review was submitted',
            'app_reviewed_email': '{{reviewer_name}} marked {{highschool}} as {{reviewer_decision}}. {{reviewer_comment}}',
            'app_approved_email_subject': 'Your application has been approved',
            'app_approved_email': 'Congratulations {{principal_name}}, {{highschool_name}} has been approved. {{approval_letter_url}}',
            'app_approved_letter': '<h2>Approval Letter</h2><p>Dear {{principal_firstname}},</p>'
                                   '<p>{{highschool_name}} is approved for: {{interested_courses_status}}</p>',
        }

    def install(self):
        try:
            setting = Setting.objects.get(key=self.key)
        except Setting.DoesNotExist:
            setting = Setting(key=self.key)
        setting.value = self._defaults()
        setting.save()

    def _to_python(self):
        return dict(self.cleaned_data)

    def run_record(self):
        try:
            setting = Setting.objects.get(key=self.key)
        except Setting.DoesNotExist:
            setting = Setting(key=self.key)
        setting.value = self._to_python()
        setting.save()
        return JsonResponse({'message': 'Successfully saved settings', 'status': 'success'})
