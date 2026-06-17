import datetime
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from new_school_application.new_school_application.models import HighSchoolApplication
from new_school_application.new_school_application.reports import school_applications as mod
from new_school_application.new_school_application.reports.school_applications import (
    school_applications,
)


class _FakeStorage:
    def __init__(self):
        self.saved_bytes = None

    def save(self, path, content_file):
        self.saved_bytes = content_file.read()
        return path

    def url(self, path):
        return f'https://example.test/{path}'


class SchoolApplicationsReportTest(TestCase):
    def setUp(self):
        self.a = HighSchoolApplication.objects.create(name='Alpha HS', status='Submitted')
        self.b = HighSchoolApplication.objects.create(name='Beta HS', status='Decision Made')
        # created_on is auto_now_add; backdate Beta via .update() to test date filters
        HighSchoolApplication.objects.filter(pk=self.b.pk).update(
            created_on=datetime.datetime(2020, 1, 1, 12, 0))

    def test_filter_by_status(self):
        qs = school_applications()._get_queryset({'status': ['Submitted']})
        self.assertEqual(list(qs), [self.a])

    def test_filter_by_date_range(self):
        # only Beta (2020) falls before this end date
        qs = school_applications()._get_queryset({'end_date': ['2020-06-01']})
        self.assertEqual(list(qs), [self.b])
        # only Alpha (today) falls on/after this start date
        qs = school_applications()._get_queryset(
            {'start_date': [datetime.date.today().isoformat()]})
        self.assertEqual(list(qs), [self.a])

    def test_no_filters_returns_all(self):
        qs = school_applications()._get_queryset({'status': ['']})
        self.assertEqual(qs.count(), 2)

    def test_run_writes_csv(self):
        fake = _FakeStorage()
        with mock.patch.object(mod, 'PrivateMediaStorage', return_value=fake):
            url = school_applications().run(SimpleNamespace(id='task123'), {'status': ['']})
        self.assertIn('task123', url)
        text = fake.saved_bytes.decode('utf-8')
        self.assertIn('High School', text)        # header
        self.assertIn('Alpha HS', text)
        self.assertIn('Beta HS', text)

    def test_run_respects_status_filter(self):
        fake = _FakeStorage()
        with mock.patch.object(mod, 'PrivateMediaStorage', return_value=fake):
            school_applications().run(SimpleNamespace(id='t'), {'status': ['Submitted']})
        text = fake.saved_bytes.decode('utf-8')
        self.assertIn('Alpha HS', text)
        self.assertNotIn('Beta HS', text)
