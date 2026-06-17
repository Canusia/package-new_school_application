from rest_framework import serializers

from ..models import HighSchoolApplicationCourseReview


class ReviewSerializer(serializers.ModelSerializer):
    created_on = serializers.DateTimeField(format='%m/%d/%Y')
    highschool = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()

    class Meta:
        model = HighSchoolApplicationCourseReview
        fields = ['id', 'created_on', 'status', 'highschool', 'course']
        datatables_always_serialize = ['id', 'created_on', 'status', 'highschool', 'course']

    def get_highschool(self, obj):
        return obj.interested_course.highschool_application.name

    def get_course(self, obj):
        return str(obj.interested_course.course)
