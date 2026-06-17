from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape

from ..models import (
    COURSE_REVIEW_STATUS_OPTIONS,
    HighSchoolApplicationCourseReview,
)

_COMMENT_REQUIRED = ('Not Approved', 'Need more information')


class HighSchoolCourseReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=COURSE_REVIEW_STATUS_OPTIONS, label='Your Decision/Recommendation')
    comment = forms.CharField(
        widget=forms.Textarea, required=False, label='Comment',
        help_text='Visible to CE staff only.')
    application_course_review_id = forms.CharField(widget=forms.HiddenInput)
    action = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, review=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if review:
            self.fields['application_course_review_id'].initial = review.id

    def clean(self):
        data = super().clean()
        if data.get('decision') in _COMMENT_REQUIRED and not (data.get('comment') or '').strip():
            raise ValidationError('Please add a comment below.', code='invalid')
        return data

    def save(self):
        data = self.cleaned_data
        review = HighSchoolApplicationCourseReview.objects.get(
            pk=data['application_course_review_id'])
        review.status = data['decision']
        misc = review.misc_info or {}
        prior = misc.get('note', '')
        # Escape the reviewer-supplied comment: notes are rendered as HTML to CE
        # staff, so an unescaped comment would be a stored-XSS vector.
        misc['note'] = escape(data.get('comment') or '') + '<br>-----<br>' + prior
        review.misc_info = misc
        review.save()
        return review
