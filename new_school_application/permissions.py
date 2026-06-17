from rest_framework.permissions import BasePermission

from cis.utils import user_has_cis_role, user_has_faculty_role


class CISUserOnly(BasePermission):
    def has_permission(self, request, view):
        return user_has_cis_role(request.user)


class FacultyUserOnly(BasePermission):
    def has_permission(self, request, view):
        return user_has_faculty_role(request.user)
