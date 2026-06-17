from django.conf import settings
from django.db import models as dj_models
from django.test import TestCase

from new_school_application.new_school_application.models import (
    HighSchoolApplication,
    HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
    SchoolApplicationNote,
)


class HighSchoolApplicationModelTest(TestCase):
    def test_create_with_defaults(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        self.assertEqual(app.status, 'In Progress')
        self.assertEqual(app.district, '')
        self.assertEqual(app.school_contacts, {})
        self.assertEqual(app.district_contacts, {})
        self.assertEqual(app.information, {})
        self.assertIsNotNone(app.created_on)

    def test_status_history_recorded_on_create_and_change(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        self.assertEqual(len(app.status_changed_on), 1)
        self.assertEqual(app.status_changed_on[0]['status'], 'In Progress')

        app.status = 'Submitted'
        app.save()
        self.assertEqual(len(app.status_changed_on), 2)
        self.assertEqual(app.status_changed_on[-1]['status'], 'Submitted')

    def test_status_history_not_appended_when_status_unchanged(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        app.name = 'Renamed HS'
        app.save()
        self.assertEqual(len(app.status_changed_on), 1)

    def test_status_history_persists_with_update_fields(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        app.status = 'Submitted'
        app.save(update_fields=['status'])
        app.refresh_from_db()
        self.assertEqual(len(app.status_changed_on), 2)
        self.assertEqual(app.status_changed_on[-1]['status'], 'Submitted')

    def test_can_edit_property(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        self.assertTrue(app.can_edit)  # In Progress
        app.status = 'Under Review'
        app.save()
        self.assertFalse(app.can_edit)

    def test_course_guide_uses_private_storage(self):
        from cis.backends.storage_backend import PrivateMediaStorage
        field = HighSchoolApplication._meta.get_field('course_guide')
        self.assertIsInstance(field.storage, PrivateMediaStorage)

    def test_other_college_courses_is_multiselect(self):
        field = HighSchoolApplication._meta.get_field('other_college_courses')
        choice_values = [c[0] for c in field.choices]
        self.assertIn('AP', choice_values)
        self.assertIn('IB', choice_values)

    def test_add_note_helper(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        note = app.add_note(created_by=None, message='hello')
        self.assertEqual(note.highschool_application_id, app.id)
        self.assertEqual(note.message, 'hello')
        self.assertEqual(app.notes.count(), 1)


class HighSchoolInterestedCourseModelTest(TestCase):
    def test_fk_targets_and_on_delete(self):
        app_field = HighSchoolInterestedCourse._meta.get_field('highschool_application')
        self.assertEqual(app_field.related_model, HighSchoolApplication)
        self.assertEqual(app_field.remote_field.related_name, 'interested_courses')

        course_field = HighSchoolInterestedCourse._meta.get_field('course')
        self.assertEqual(course_field.related_model._meta.label, 'cis.Course')
        self.assertEqual(course_field.remote_field.on_delete, dj_models.PROTECT)

    def test_status_default_and_choices(self):
        field = HighSchoolInterestedCourse._meta.get_field('status')
        self.assertEqual(field.default, 'Applied')
        values = [c[0] for c in field.choices]
        self.assertEqual(set(values), {'Applied', 'Approved', 'Not Approved'})

    def test_unique_together(self):
        self.assertIn(
            ('highschool_application', 'course'),
            HighSchoolInterestedCourse._meta.unique_together,
        )


class HighSchoolApplicationCourseReviewModelTest(TestCase):
    def test_fk_targets_and_on_delete(self):
        ic_field = HighSchoolApplicationCourseReview._meta.get_field('interested_course')
        self.assertEqual(ic_field.related_model, HighSchoolInterestedCourse)
        self.assertEqual(ic_field.remote_field.related_name, 'reviews')
        self.assertEqual(ic_field.remote_field.on_delete, dj_models.PROTECT)

        rev_field = HighSchoolApplicationCourseReview._meta.get_field('reviewer')
        self.assertEqual(rev_field.related_model._meta.label, settings.AUTH_USER_MODEL)
        self.assertEqual(rev_field.remote_field.on_delete, dj_models.PROTECT)

    def test_status_default_and_choices(self):
        field = HighSchoolApplicationCourseReview._meta.get_field('status')
        self.assertEqual(field.default, 'Pending')
        values = [c[0] for c in field.choices]
        self.assertEqual(
            set(values),
            {'Pending', 'Approved', 'Approved and Waitlisted',
             'Not Approved', 'Need more information'},
        )

    def test_unique_together(self):
        self.assertIn(
            ('interested_course', 'reviewer'),
            HighSchoolApplicationCourseReview._meta.unique_together,
        )


class SchoolApplicationNoteModelTest(TestCase):
    def test_create_and_relationship(self):
        app = HighSchoolApplication.objects.create(name='Test HS')
        note = SchoolApplicationNote.objects.create(
            highschool_application=app, message='a note',
        )
        self.assertEqual(note.type, 'note')
        self.assertIsNone(note.created_by)
        self.assertEqual(list(app.notes.all()), [note])

    def test_fk_on_delete(self):
        app_field = SchoolApplicationNote._meta.get_field('highschool_application')
        self.assertEqual(app_field.remote_field.on_delete, dj_models.CASCADE)
        cb_field = SchoolApplicationNote._meta.get_field('created_by')
        self.assertEqual(cb_field.remote_field.on_delete, dj_models.SET_NULL)
