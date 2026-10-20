from django import forms

from ..captcha import CaptchaField

from cis.models.course import Course

from ..countries import COUNTRY_CHOICES
from ..models import (
    HighSchoolApplication,
    HighSchoolInterestedCourse,
    OTHER_COLLEGE_COURSE_CHOICES,
)


HEAR_ABOUT_US_CHOICES = [
    ('', 'Select'),
    ('Information Session', 'Information Session'),
    ('From another school', 'From another partner school'),
    ('Other', 'Other'),
]


def _is_ce_admin(request):
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    try:
        return 'ce' in user.get_roles()
    except Exception:
        return False


class HighSchoolApplicationForm(forms.Form):
    """Step 1 — high school + contact details. Public/unauthenticated."""

    your_name = forms.CharField(required=True, label='Your Name')
    your_email = forms.EmailField(
        required=True, label='Your Email',
        help_text='Enter a valid email so we can notify you about your application.',
    )

    highschool_name = forms.CharField(required=True, label='High School Name')
    highschool_code = forms.CharField(
        required=False, label='High School Code', help_text='CEEB Code, if known')
    highschool_address = forms.CharField(required=True, label='Address Line 1')
    highschool_city = forms.CharField(required=True, label='City')
    highschool_state = forms.CharField(required=True, label='State/Province')
    highschool_postal_code = forms.CharField(required=True, label='Zip / Postal Code')
    highschool_phone = forms.CharField(required=True, label='Phone')
    highschool_fax = forms.CharField(required=True, label='Fax')
    highschool_country = forms.ChoiceField(
        label='Country', choices=COUNTRY_CHOICES, initial='United States')

    principal_name = forms.CharField(required=True, label='Principal Name')
    principal_email = forms.EmailField(required=True, label='Principal Email')
    primary_contact_name = forms.CharField(
        required=True, label='Primary Contact Name',
        help_text='This person will be the primary concurrent-enrollment contact for the school.',
    )
    primary_contact_email = forms.EmailField(required=True, label='Primary Contact Email')
    guidance_name = forms.CharField(required=True, label='Director of Guidance Name')
    guidance_email = forms.EmailField(required=True, label='Director of Guidance Email')

    district_name = forms.CharField(required=False, label='District Name')
    superintendent_name = forms.CharField(required=True, label='Superintendent Name')
    superintendent_email = forms.EmailField(required=True, label='Superintendent Email')

    action = forms.CharField(required=True, widget=forms.HiddenInput, initial='part_1')
    captcha = CaptchaField(label='')

    def __init__(self, request=None, record=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Captcha is for anonymous public submitters; drop it for CE admins only.
        if _is_ce_admin(request):
            del self.fields['captcha']
            self.fields['your_name'].label = 'Submitter Name'
            self.fields['your_email'].label = 'Submitter Email'

        if record:
            sc = record.school_contacts or {}
            dc = record.district_contacts or {}
            addr = (record.information or {}).get('address', {})
            self.fields['your_name'].initial = sc.get('submitted_by', {}).get('name')
            self.fields['your_email'].initial = sc.get('submitted_by', {}).get('email')
            self.fields['highschool_name'].initial = record.name
            self.fields['district_name'].initial = record.district
            self.fields['highschool_code'].initial = addr.get('code')
            self.fields['highschool_address'].initial = addr.get('address')
            self.fields['highschool_city'].initial = addr.get('city')
            self.fields['highschool_state'].initial = addr.get('state')
            self.fields['highschool_postal_code'].initial = addr.get('postal_code')
            self.fields['highschool_phone'].initial = addr.get('phone')
            self.fields['highschool_fax'].initial = addr.get('fax')
            self.fields['highschool_country'].initial = addr.get('country')
            self.fields['principal_name'].initial = sc.get('principal', {}).get('name')
            self.fields['principal_email'].initial = sc.get('principal', {}).get('email')
            self.fields['primary_contact_name'].initial = sc.get('primary_contact', {}).get('name')
            self.fields['primary_contact_email'].initial = sc.get('primary_contact', {}).get('email')
            self.fields['guidance_name'].initial = sc.get('guidance', {}).get('name')
            self.fields['guidance_email'].initial = sc.get('guidance', {}).get('email')
            self.fields['superintendent_name'].initial = dc.get('superintendent', {}).get('name')
            self.fields['superintendent_email'].initial = dc.get('superintendent', {}).get('email')

    def save(self, commit=True, app=None):
        data = self.cleaned_data
        if app is None:
            app = HighSchoolApplication()
        if not app.information:
            app.information = {}

        app.name = data.get('highschool_name')
        app.district = data.get('district_name') or ''

        app.information['address'] = {
            'code': data.get('highschool_code'),
            'address': data.get('highschool_address'),
            'city': data.get('highschool_city'),
            'state': data.get('highschool_state'),
            'postal_code': data.get('highschool_postal_code'),
            'phone': data.get('highschool_phone'),
            'fax': data.get('highschool_fax'),
            'country': data.get('highschool_country') or '',
        }
        app.school_contacts = {
            'submitted_by': {'name': data.get('your_name'), 'email': data.get('your_email')},
            'principal': {'name': data.get('principal_name'), 'email': data.get('principal_email')},
            'primary_contact': {'name': data.get('primary_contact_name'), 'email': data.get('primary_contact_email')},
            'guidance': {'name': data.get('guidance_name'), 'email': data.get('guidance_email')},
        }
        app.district_contacts = {
            'superintendent': {'name': data.get('superintendent_name'), 'email': data.get('superintendent_email')},
        }

        if commit:
            app.save()
        return app


class HighSchoolCourseForm(forms.Form):
    """Step 2 — curriculum answers, course-guide upload, interested courses."""

    course = forms.CharField(required=False, widget=forms.HiddenInput)

    faculty = forms.CharField(
        required=True,
        label='How many faculty do you anticipate training as adjunct instructors for each subject area?',
    )
    student_eligibility = forms.CharField(
        required=True, widget=forms.Textarea,
        label='What criteria will you use to determine student eligibility for each course?',
    )
    students_in_course = forms.CharField(
        required=True,
        label='How many students do you expect to be eligible to participate annually in each course?',
    )
    students_annually = forms.CharField(
        required=True,
        label='How many students do you expect to enroll annually in each course?',
    )
    course_fit = forms.CharField(
        required=True, widget=forms.Textarea,
        label="How will the college courses fit into the school's departmental and overall curriculum?",
    )
    implementation = forms.CharField(
        required=True, widget=forms.Textarea,
        label="How do you expect implementing these courses will impact your school's students and faculty?",
    )
    course_guide = forms.FileField(
        required=True, label="Please attach a copy of your school's current course guide:",
    )
    course_guide_link = forms.CharField(required=False, widget=forms.HiddenInput)
    other_college_course = forms.MultipleChoiceField(
        required=False, choices=OTHER_COLLEGE_COURSE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='What other college-level course(s) do you currently offer?',
    )
    other_course = forms.CharField(required=False, label='If other, please specify')
    hear_about_us = forms.ChoiceField(
        required=True, choices=HEAR_ABOUT_US_CHOICES,
        label='How did you hear about the program?',
    )
    hear_about_us_from = forms.CharField(required=False, label='If other, please specify')
    action = forms.CharField(required=True, widget=forms.HiddenInput, initial='part_2')

    def __init__(self, request=None, record=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if record:
            info = record.information or {}
            for key in ('faculty', 'student_eligibility', 'students_in_course',
                        'students_annually', 'course_fit', 'implementation',
                        'course_guide_link', 'hear_about_us', 'hear_about_us_from',
                        'other_course'):
                self.fields[key].initial = info.get(key)
            self.fields['other_college_course'].initial = record.other_college_courses
            if record.course_guide:
                self.fields['course_guide'].required = False

    def clean(self):
        cleaned = super().clean()
        courses = [c.strip() for c in self.data.getlist('course') if c.strip()]
        if not courses:
            self.add_error('course', 'Please select at least one course.')
        cleaned['course'] = courses
        return cleaned

    def save(self, record, commit=True):
        data = self.cleaned_data
        if not record.information:
            record.information = {}
        for key in ('faculty', 'student_eligibility', 'students_in_course',
                    'students_annually', 'course_fit', 'implementation',
                    'course_guide_link', 'hear_about_us', 'hear_about_us_from',
                    'other_course'):
            record.information[key] = data.get(key)
        record.other_college_courses = data.get('other_college_course')

        for course_id in data.get('course', []):
            course = Course.objects.get(pk=course_id)
            HighSchoolInterestedCourse.objects.get_or_create(
                highschool_application=record, course=course,
            )

        if data.get('course_guide'):
            record.course_guide = data.get('course_guide')

        record.status = 'Under Review'
        if commit:
            record.save()
        return record
