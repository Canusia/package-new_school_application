from django.http import JsonResponse
from django.shortcuts import render

from rest_framework import viewsets

from cis.menu import cis_menu, draw_menu

from ..forms.faculty import HighSchoolCourseReviewForm
from ..models import HighSchoolApplicationCourseReview
from ..permissions import FacultyUserOnly
from ..serializers.faculty import ReviewSerializer


class ReviewViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [FacultyUserOnly]

    def get_queryset(self):
        return HighSchoolApplicationCourseReview.objects.filter(
            reviewer=self.request.user).select_related(
            'interested_course', 'interested_course__course',
            'interested_course__highschool_application').order_by('-created_on')


def reviews(request):
    return render(request, 'new_school_application/faculty/reviews.html', {
        'page_title': 'Application Reviews',
        'menu': draw_menu(cis_menu, 'highschools', 'new_school_application_reviews'),
        'api_url': '/faculty/new_school_application/api/review/',
    })


def submit_review(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    review_id = request.POST.get('application_course_review_id')
    try:
        review = HighSchoolApplicationCourseReview.objects.get(pk=review_id)
    except HighSchoolApplicationCourseReview.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Not found.'}, status=404)
    if review.reviewer_id != request.user.id:
        return JsonResponse({'status': 'error', 'message': 'Not your review.'}, status=403)
    form = HighSchoolCourseReviewForm(review, request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse({'status': 'success', 'message': 'Decision recorded.', 'action': 'reload'})
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
