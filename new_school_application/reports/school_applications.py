import csv
import io

from django import forms
from django.core.files.base import ContentFile
from django.urls import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.backends.storage_backend import PrivateMediaStorage

from ..models import APPLICATION_STATUS_OPTIONS, HighSchoolApplication


def _first(data, key):
    """The report runner passes the raw POST dict (list-valued); pull a scalar."""
    value = data.get(key)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return value or None


class school_applications(forms.Form):
    """Export new high school applications to CSV, filterable by status + date range."""

    status = forms.ChoiceField(
        required=False, label='Status',
        choices=[('', 'All statuses')] + list(APPLICATION_STATUS_OPTIONS))
    start_date = forms.DateField(
        required=False, label='Created from',
        widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(
        required=False, label='Created until',
        widget=forms.DateInput(attrs={'type': 'date'}))

    request = None

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.helper = FormHelper()
        self.helper.attrs = {'target': '_blank'}
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Generate Export'))
        if request:
            self.helper.form_action = reverse_lazy(
                'report:run_report', args=[request.GET.get('report_id')])

    HEADERS = [
        'Created On', 'High School', 'District', 'State', 'Status',
        'Interested Courses', 'Course Count',
        'Submitter', 'Submitter Email',
        'Principal', 'Principal Email',
        'Superintendent', 'Superintendent Email',
    ]

    def _get_queryset(self, data):
        qs = HighSchoolApplication.objects.all().order_by('-created_on')
        status = _first(data, 'status')
        start = _first(data, 'start_date')
        end = _first(data, 'end_date')
        if status:
            qs = qs.filter(status=status)
        if start:
            qs = qs.filter(created_on__date__gte=start)
        if end:
            qs = qs.filter(created_on__date__lte=end)
        return qs

    def _row(self, app):
        sc = app.school_contacts or {}
        dc = app.district_contacts or {}
        addr = (app.information or {}).get('address', {})
        courses = list(app.interested_courses.select_related('course'))
        return [
            app.created_on.strftime('%m/%d/%Y') if app.created_on else '',
            app.name,
            app.district,
            addr.get('state', ''),
            app.status,
            ', '.join(str(ic.course) for ic in courses),
            len(courses),
            sc.get('submitted_by', {}).get('name', ''),
            sc.get('submitted_by', {}).get('email', ''),
            sc.get('principal', {}).get('name', ''),
            sc.get('principal', {}).get('email', ''),
            dc.get('superintendent', {}).get('name', ''),
            dc.get('superintendent', {}).get('email', ''),
        ]

    def run(self, task, data):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(self.HEADERS)
        for app in self._get_queryset(data).iterator():
            writer.writerow(self._row(app))

        file_name = 'school-applications-export.csv'
        path = f'reports/{task.id}/{file_name}'
        storage = PrivateMediaStorage()
        path = storage.save(path, ContentFile(stream.getvalue().encode('utf-8')))
        return storage.url(path)
