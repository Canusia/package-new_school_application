# New School Application — CLAUDE.md

Guidance for working in the `new_school_application` app (claude.ai/code). See `README.md` for host install steps.

## What this app is

A MyCE feature app that handles the full **new high school application** lifecycle:

```
public 2-step intake  →  CE review console  →  faculty per-course review  →  approval + PDF letter  →  provision into a real HighSchool
```

Ported from the `pass` tenant's in-tree feature and **neutralized of Syracuse/SUPA specifics** (e.g. the primary-contact provisioning position is "Program Coordinator", not "SUPA Coordinator"; all email routing is settings-driven, no hardcoded addresses).

## Dual-layer package structure

This is a pip-installable submodule with the same outer/inner layout as `class_visit` / `ethos`:

```
new_school_application/                  ← outer package root (this dir)
├── CLAUDE.md, README.md
├── setup.cfg, pyproject.toml, MANIFEST.in
├── __init__.py                          # outer marker (no imports)
├── models.py                            # proxy: re-exports inner models for `from new_school_application.models import …`
└── new_school_application/              ← inner Django app  (app_label = new_school_application)
    ├── apps.py        # NewSchoolApplicationConfig (prod) + DevNewSchoolApplicationConfig (dev); CONFIGURATORS + REPORTS
    ├── models.py      # HighSchoolApplication, HighSchoolInterestedCourse, HighSchoolApplicationCourseReview, SchoolApplicationNote
    ├── signals.py     # reviewer assignment + alerts + create/submitted notifiers (wired in apps.ready())
    ├── permissions.py # CISUserOnly, FacultyUserOnly (DRF)
    ├── countries.py   # static country list for the intake dropdown (no SIS/Location dependency)
    ├── forms/         # public.py (intake), ce.py (edit + approval-notification), faculty.py (course review)
    ├── views/         # public.py, ce.py, faculty.py
    ├── urls/          # public.py, ce.py, faculty.py  (distinct app_names — see below)
    ├── serializers/   # ce.py (ApplicationListSerializer, NoteSerializer), faculty.py (ReviewSerializer)
    ├── services/      # emails.py (send_app_email gate + notifiers), pdf.py (approval letter)
    ├── settings/      # new_school_application.py (email-template + gate configurator)
    ├── reports/       # school_applications.py (CSV export, status + date filters)
    ├── templates/new_school_application/{public,ce,ce/tabs,faculty}/
    ├── migrations/    # 0001 models, 0002 CE menu, 0003 faculty menu (data migrations)
    └── tests/
```

**Importable as** `new_school_application.new_school_application` in the editable submodule layout (dev), or `new_school_application` when pip-installed (prod). Django derives `app_label = new_school_application` for both configs.

## Conventions (important)

- **Relative imports inside the package** (`from ..models import …`, `from .services import emails`). Absolute 2-deep paths (`new_school_application.new_school_application.x`) only resolve in dev and break the pip install. Tests use the absolute path (correct for test discovery).
- **Cross-app references**: use string FKs (`'cis.Course'`, `settings.AUTH_USER_MODEL`) in models so `cis` is never imported at model-definition time. `PrivateMediaStorage` is imported directly from `cis.backends.storage_backend` (same as `class_visit`). Views/forms/services may import `cis` helpers (`cis.utils.user_has_cis_role`/`user_has_faculty_role`, `cis.menu.draw_menu`, `cis.models.course.Course`).
- **URL namespaces are distinct per portal**: public = `new_school_application`, CE = `new_school_application_ce`, faculty = `new_school_application_faculty`. Use the right one in `reverse()`.
- **Email is gated**: every send goes through `services.emails.send_app_email`, which honors the `new_school_application` Setting's `is_active` (`No` = suppress, `Debug` = redirect to `debug_email_list`, `Yes` = live; Django `DEBUG` also forces the debug list). Default `is_active='No'`, so a fresh install sends nothing until configured. Never call `send_html_mail`/`send_mail` directly.
- **The intake country field** is a self-contained `ChoiceField` over `countries.py` — it must NOT depend on `cis.Location` (which is SIS-populated and empty on a fresh DB).
- **Migrations**: cross-app deps use `('cis', '__first__')` (portable across tenants). The `0002`/`0003` data migrations mutate the per-role menu Setting (`cis.settings.menu`), whose `<role>_menu` values are JSON **strings** — `json.loads`/`json.dumps` them. The `submod-migration-deps` and `submod-package-manifest` skills apply here; run the manifest check before tagging a release.

## How it's wired into the host (see README for the lines)

- `INSTALLED_APPS`: a `find_spec` switch picks `DevNewSchoolApplicationConfig` (dev) or `NewSchoolApplicationConfig` (prod).
- `myce/urls.py`: `_nsa` find_spec var + three includes — `new_school_application/` (public), `ce/new_school_applications/` (CE), `faculty/new_school_application/` (faculty).
- `register_settings` registers the email-template configurator (apps `CONFIGURATORS`); `register_reports` registers the CSV report (apps `REPORTS`). Both are deploy-time mgmt commands.
- Nav items are installed by migrations `0002` (CE) / `0003` (faculty).

## Testing

Run inside the container (the repo is live-mounted at `/app`):

```bash
docker exec -w /app/webapp django_web_ewu python manage.py test new_school_application -v 1
```

Test conventions used throughout:
- CE/faculty users via Django groups: `user.groups.add(Group.objects.get_or_create(name='ce')[0])`. `CustomUser.get_roles()` reads group names.
- `create_user(username=…, email=…)` — this tenant's user manager requires `username`.
- Disconnect `django_login_history.post_login` in `setUpClass` before `force_login` (it crashes on the test request's `None` IP). See `tests/test_ce_views.py` for the pattern.
- The captcha comes from the tenant's `cis.captcha.CaptchaField` (`new_school_application/captcha.py`; reCAPTCHA or ALTCHA by the tenant's `CAPTCHA_PROVIDER`, ewu#87). The container sets `CAPTCHA_TESTING=True`, so the anonymous intake POST passes the captcha without a real solve.
- Minimal `Course` fixture: `Cohort.objects.create(name=…, designator=…)` + `Course.objects.create(name, title, cohort, catalog_number, credit_hours)`. Avoid building deep Course graphs — assert FK wiring via `_meta` where possible (mirrors `class_visit`).
- File uploads / report CSV writes hit S3 (`PrivateMediaStorage`); mock the storage in tests (see `tests/test_report.py`, `tests/test_public_forms.py`).

## Key models

- **HighSchoolApplication** — the application; `status` workflow (`In Progress → Submitted → Under Review → Decision Made` / `Withdrawn` / `Closed`), with status history recorded in `save()` via a shared `_StatusHistoryModel` base. JSON fields `school_contacts` / `district_contacts` / `information` hold the intake data. Helpers: `add_reviewers`, `has_all_courses_reviewed`, `import_as_highschool`, `notify_application_approved`, `ce_url`, `approval_letter_url`.
- **HighSchoolInterestedCourse** — FK to `cis.Course` (PROTECT) + the application; per-course `status`.
- **HighSchoolApplicationCourseReview** — a faculty reviewer's decision per interested course (PROTECT FKs).
- **SchoolApplicationNote** — app-owned notes (CASCADE to the application).

## Deferred-from-source / neutralized

- No hardcoded personal emails (the source's `DEBUG → kadaji@gmail.com`); routing is settings-driven.
- "Program Coordinator" position label (was "SUPA Coordinator").
- Country dropdown is self-contained (not `cis.Location`).
