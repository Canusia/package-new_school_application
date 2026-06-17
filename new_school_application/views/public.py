from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from cis.models.course import Course

from ..forms.public import HighSchoolApplicationForm, HighSchoolCourseForm
from ..models import HighSchoolApplication


def apply(request):
    """Step 1 — create a HighSchoolApplication from school + contact details."""
    template = 'new_school_application/public/application.html'
    context = {}

    if request.method == 'POST':
        form = HighSchoolApplicationForm(request, None, request.POST)
        if form.is_valid():
            record = form.save()
            messages.add_message(
                request, messages.SUCCESS,
                'Thank you for starting your application. Please select the '
                'course(s) you are interested in offering to complete it.',
                'list-group-item-success',
            )
            return redirect('new_school_application:apply_courses', application_id=record.id)
        messages.add_message(
            request, messages.ERROR,
            'Please correct the errors and try again.', 'list-group-item-danger')
    else:
        form = HighSchoolApplicationForm(request, None)

    context['form'] = form
    return render(request, template, context)


apply.login_required = False


def apply_courses(request, application_id):
    """Step 2 — curriculum answers + course selection; moves status to Under Review."""
    template = 'new_school_application/public/courses.html'
    record = get_object_or_404(HighSchoolApplication, pk=application_id)
    context = {}

    if request.method == 'POST':
        if not record.can_edit:
            messages.add_message(
                request, messages.ERROR,
                'This application can no longer be edited.', 'list-group-item-danger')
            return redirect('index')
        form = HighSchoolCourseForm(request, None, request.POST, request.FILES)
        if form.is_valid():
            form.save(record)
            messages.add_message(
                request, messages.SUCCESS,
                'Thank you for submitting your application. We will be in touch soon.',
                'list-group-item-success',
            )
            return redirect('index')
        messages.add_message(
            request, messages.ERROR,
            'Please correct the errors and try again.', 'list-group-item-danger')
    else:
        form = HighSchoolCourseForm(request, None)

    context['form'] = form
    context['record'] = record
    # Show every active course flagged available for new schools. (We don't use
    # Course.available_for_new_schools() here: it groups by stream and silently
    # drops courses that have no stream assigned.)
    context['available_courses'] = Course.objects.filter(
        meta__available_for_new_schools='1', status='Active',
    ).order_by('stream', 'title')
    return render(request, template, context)


apply_courses.login_required = False
