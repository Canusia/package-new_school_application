"""Inject the New School Applications nav item into the CE `menu` setting.

The portal menus are pulled (by ``cis.menu.draw_menu``) from the DB-backed
``cis.settings.menu`` Setting. Each ``<role>_menu`` entry is stored as a JSON
*string* (a list of top-level nav dicts). This data migration adds a
``New School Applications`` sub-item under the existing ``highschools`` top-level
item in ``ce_menu`` so the CE console link appears without manual config.

Idempotent: re-running makes no further changes. No-ops gracefully if the menu
Setting row doesn't exist yet (fresh install before ``register_settings``) or if
the ``highschools`` top-level item isn't present.
"""
import json

from django.db import migrations

MENU_SETTING_KEY = 'cis.settings.menu'
NAV_ITEM = {
    'label': 'New School Applications',
    'name': 'new_school_applications',
    'url': 'new_school_application_ce:index',
}


def _load(value, role):
    raw = value.get(f'{role}_menu')
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def add_menu_item(apps, schema_editor):
    Setting = apps.get_model('cis', 'Setting')
    try:
        setting = Setting.objects.get(key=MENU_SETTING_KEY)
    except Setting.DoesNotExist:
        return

    value = setting.value or {}
    items = _load(value, 'ce')
    if items is None:
        return

    changed = False
    for top in items:
        if top.get('name') == 'highschools':
            sub = top.setdefault('sub_menu', [])
            if not any(i.get('name') == NAV_ITEM['name'] for i in sub):
                sub.append(dict(NAV_ITEM))
                changed = True
            break

    if changed:
        value['ce_menu'] = json.dumps(items)
        setting.value = value
        setting.save()


def remove_menu_item(apps, schema_editor):
    Setting = apps.get_model('cis', 'Setting')
    try:
        setting = Setting.objects.get(key=MENU_SETTING_KEY)
    except Setting.DoesNotExist:
        return

    value = setting.value or {}
    items = _load(value, 'ce')
    if items is None:
        return

    changed = False
    for top in items:
        if top.get('name') == 'highschools':
            sub = top.get('sub_menu', [])
            pruned = [i for i in sub if i.get('name') != NAV_ITEM['name']]
            if len(pruned) != len(sub):
                top['sub_menu'] = pruned
                changed = True
            break

    if changed:
        value['ce_menu'] = json.dumps(items)
        setting.value = value
        setting.save()


class Migration(migrations.Migration):
    dependencies = [
        ('new_school_application', '0001_initial'),
        ('cis', '__first__'),
    ]
    operations = [migrations.RunPython(add_menu_item, remove_menu_item)]
