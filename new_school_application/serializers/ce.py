from django.urls import reverse

from rest_framework import serializers

from ..models import HighSchoolApplication, SchoolApplicationNote


class ApplicationListSerializer(serializers.ModelSerializer):
    """Server-side DataTables row for the CE application list."""

    created_on = serializers.DateTimeField(format='%m/%d/%Y')
    state = serializers.SerializerMethodField()
    interested_courses_count = serializers.SerializerMethodField()
    other_college_courses_display = serializers.SerializerMethodField()
    detail_url = serializers.SerializerMethodField()

    class Meta:
        model = HighSchoolApplication
        fields = [
            'id', 'name', 'district', 'status', 'created_on',
            'state', 'interested_courses_count',
            'other_college_courses_display', 'detail_url',
        ]
        datatables_always_serialize = [
            'id', 'name', 'district', 'status', 'created_on',
            'state', 'interested_courses_count',
            'other_college_courses_display', 'detail_url',
        ]

    def get_state(self, obj):
        return (obj.information or {}).get('address', {}).get('state', '')

    def get_interested_courses_count(self, obj):
        return obj.interested_courses.count()

    def get_other_college_courses_display(self, obj):
        return ', '.join(obj.other_college_courses or [])

    def get_detail_url(self, obj):
        return reverse('new_school_application_ce:detail', kwargs={'record_id': obj.id})


class NoteSerializer(serializers.ModelSerializer):
    """Server-side DataTables row for an application's notes."""

    created_on = serializers.DateTimeField(format='%m/%d/%Y %I:%M %p')
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = SchoolApplicationNote
        fields = ['id', 'created_on', 'message', 'type', 'created_by_display']
        datatables_always_serialize = [
            'id', 'created_on', 'message', 'type', 'created_by_display',
        ]

    def get_created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or str(obj.created_by) or '—'
        return '—'
