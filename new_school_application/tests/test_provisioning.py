from django.contrib.auth.models import Group
from django.test import TestCase

from cis.models.highschool import HighSchool
from cis.models.highschool_administrator import HSAdministratorPosition
from new_school_application.new_school_application.models import HighSchoolApplication


class ImportAsHighSchoolTest(TestCase):
    def setUp(self):
        # The HSAdministratorPosition post_save signal requires this group.
        Group.objects.get_or_create(name='highschool_admin')
        self.app = HighSchoolApplication.objects.create(
            name='Lincoln High',
            information={'address': {
                'address': '1 Main St', 'city': 'Town', 'state': 'WA',
                'postal_code': '99001', 'country': 'United States', 'code': 'CEEB1'}},
            school_contacts={
                'submitted_by': {'name': 'Jo Sub', 'email': 'jo@example.com'},
                'principal': {'name': 'Dr. Jane Roe', 'email': 'p@example.com'},
                'guidance': {'name': 'Gee Idance', 'email': 'g@example.com'},
                'primary_contact': {'name': 'Prim Contact', 'email': 'pc@example.com'}},
            district_contacts={'superintendent': {'name': 'Sue Per', 'email': 's@example.com'}},
        )

    def test_creates_highschool(self):
        hs = self.app.import_as_highschool()
        self.assertIsInstance(hs, HighSchool)
        self.assertEqual(hs.name, 'Lincoln High')
        self.assertEqual(hs.city, 'Town')
        self.assertEqual(hs.status, 'Active')

    def test_creates_administrator_positions(self):
        hs = self.app.import_as_highschool()
        positions = set(HSAdministratorPosition.objects.filter(
            highschool=hs).values_list('position__name', flat=True))
        self.assertIn('Principal', positions)
        self.assertIn('Director of Guidance', positions)
        self.assertIn('Superintendent', positions)
        self.assertIn('Program Coordinator', positions)

    def test_idempotent_on_existing_highschool(self):
        self.app.import_as_highschool()
        hs2 = self.app.import_as_highschool()
        self.assertEqual(HighSchool.objects.filter(name__iexact='Lincoln High').count(), 1)
