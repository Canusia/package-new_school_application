from django.apps import AppConfig


_REPORTS_BASE = [
    {
        'name': 'school_applications',
        'title': 'School Applications Export',
        'description': 'Export new high school applications to CSV, filterable by status and date range.',
        'categories': ['High Schools'],
        'available_for': ['ce'],
    },
]


class NewSchoolApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'new_school_application'

    CONFIGURATORS = [
        {
            'app': 'new_school_application',
            'name': 'new_school_application',
            'title': 'New School Application Language & Emails',
            'description': '-',
            'categories': ['2'],
        },
    ]

    REPORTS = [{**entry, 'app': 'new_school_application'} for entry in _REPORTS_BASE]

    def ready(self):
        from . import signals  # noqa


class DevNewSchoolApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'new_school_application.new_school_application'
    label = 'new_school_application'

    CONFIGURATORS = [
        {**c, 'app': 'new_school_application.new_school_application'}
        for c in NewSchoolApplicationConfig.CONFIGURATORS
    ]

    REPORTS = [
        {**entry, 'app': 'new_school_application.new_school_application'}
        for entry in _REPORTS_BASE
    ]

    def ready(self):
        from . import signals  # noqa
