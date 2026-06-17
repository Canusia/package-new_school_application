from django.contrib.auth.decorators import user_passes_test
from django.urls import include, path

from rest_framework.routers import DefaultRouter

from cis.utils import user_has_faculty_role

from ..views.faculty import ReviewViewSet, reviews, submit_review

app_name = 'new_school_application_faculty'

router = DefaultRouter()
router.register('review', ReviewViewSet, basename='review')

_fac = user_passes_test(user_has_faculty_role, login_url='/')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', _fac(reviews), name='reviews'),
    path('submit_review/', _fac(submit_review), name='submit_review'),
]
