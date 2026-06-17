from django.contrib.auth.decorators import user_passes_test
from django.urls import include, path

from rest_framework.routers import DefaultRouter

from cis.utils import user_has_cis_role

from ..views.ce import (
    ApplicationViewSet, NoteViewSet, index, detail, delete_record, approval_letter,
)

app_name = 'new_school_application_ce'

router = DefaultRouter()
router.register('application', ApplicationViewSet, basename='application')
router.register('note', NoteViewSet, basename='note')

_ce = user_passes_test(user_has_cis_role, login_url='/')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', _ce(index), name='index'),
    path('<uuid:record_id>/', _ce(detail), name='detail'),
    path('<uuid:record_id>/approval_letter/', _ce(approval_letter), name='approval_letter'),
    path('<uuid:record_id>/delete/', _ce(delete_record), name='delete'),
]
