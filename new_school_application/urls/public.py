from django.urls import path

from ..views import public

app_name = 'new_school_application'

urlpatterns = [
    path('', public.apply, name='apply'),
    path('courses/<uuid:application_id>/', public.apply_courses, name='apply_courses'),
]
