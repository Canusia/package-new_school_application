# New School Application

A MyCE feature app for the **new high school application** lifecycle — a public intake form, a CE review/approval console, a faculty per-course review workflow, settings-driven email notifications, an approval-letter PDF, provisioning of an approved application into a real `HighSchool`, and a CSV export report.

It is a **pip-installable Django submodule** with a dual outer/inner layout (the same pattern as `class_visit` / `ethos`): the importable app is `new_school_application.new_school_application` when used as an editable submodule (development) and `new_school_application` when pip-installed (production). The app label is `new_school_application` in both modes.

---

## Features

- **Public 2-step intake** (`/new_school_application/`, unauthenticated) — school + contacts, then course selection + curriculum answers + course-guide upload. Captcha-protected for anonymous users (the tenant's `cis.captcha.CaptchaField`).
- **CE admin console** (`/ce/new_school_applications/`) — filterable DataTable list; a detail page (opens in the shared modal) with a contact-card Info tab (mailto + copy-to-clipboard + "email a note"), an Interested-Courses tab (read-only curriculum + edit-courses), and a DRF-backed Notes tab.
- **Faculty review** (`/faculty/new_school_application/`) — reviewers (course administrators) submit a per-course decision; assignment + in-app alerts are signal-driven.
- **Approval + provisioning** — send an approval notification, download the approval-letter PDF, and "Import as New High School" (creates a `HighSchool` + `HSAdministrator`/`HSAdministratorPosition` records).
- **CSV report** — "School Applications Export", filterable by status and created date range (under the CE Reports area).

---

## Requirements

- Django ≥ 3.2 (built/tested on Django 5.2)
- The host MyCE app providing the `cis` core app (`Course`, `HighSchool`, `HSAdministrator`, `Location`, `Setting`, `CustomUser`, `cis.utils`, `cis.menu`, `cis.backends.storage_backend`), the `alerts` app, the `report` app, `crispy_forms`, the captcha package its `CAPTCHA_PROVIDER` needs (`django_recaptcha` or `django_altcha`), `django-model-utils`, `django-multiselectfield`, `django-mailer`, and `rest_framework` + `rest_framework_datatables`.

---

## Install / host integration

### 1. Add the package (production)

In the host `webapp/requirements.txt`, pin the published package (CalVer/tag per the Canusia convention):

```
git+https://github.com/Canusia/package-new_school_application@vX.Y.Z
```

For local development, add the submodule under `webapp/new_school_application/` (editable layout). `settings.py` auto-detects it via `find_spec`.

### 2. Register the app

In `webapp/myce/settings.py`, add to `INSTALLED_APPS` (mirrors the `class_visit` switch):

```python
    'new_school_application.new_school_application.apps.DevNewSchoolApplicationConfig'
    if importlib.util.find_spec('new_school_application.new_school_application')
    else 'new_school_application.apps.NewSchoolApplicationConfig',
```

### 3. Wire the URLs

In `webapp/myce/urls.py`, next to the other `find_spec` package-name vars:

```python
_nsa = 'new_school_application.new_school_application' if importlib.util.find_spec('new_school_application.new_school_application') else 'new_school_application'
```

and in `urlpatterns`:

```python
    path('new_school_application/', include(f'{_nsa}.urls.public')),          # public intake (unauthenticated)
    path('ce/new_school_applications/', include(f'{_nsa}.urls.ce')),          # CE admin console
    path('faculty/new_school_application/', include(f'{_nsa}.urls.faculty')),  # faculty reviews
```

URL namespaces: `new_school_application` (public), `new_school_application_ce` (CE), `new_school_application_faculty` (faculty).

### 4. Migrate

```bash
docker exec -w /app/webapp django_web_ewu python manage.py migrate new_school_application
```

Migrations:
| Migration | What it does |
|-----------|--------------|
| `0001_initial` | The four models (cross-app dep pinned to `('cis','__first__')`) |
| `0002_ce_menu_item` | Adds the **CE** "New School Applications" nav item (under High Schools) |
| `0003_faculty_menu_item` | Adds the **faculty** "Application Reviews" nav item |

> The menu migrations no-op gracefully if the `cis.settings.menu` Setting (or the `highschools` group) isn't present yet.

### 5. Register settings + the report

```bash
docker exec -w /app/webapp django_web_ewu python manage.py register_settings   # email-template configurator
docker exec -w /app/webapp django_web_ewu python manage.py register_reports    # "School Applications Export" CSV report
```

`register_settings` surfaces the **New School Application Language & Emails** settings page; `register_reports` adds the CSV report to the CE Reports area.

### 6. Configure email + captcha

- Open the **New School Application Language & Emails** settings page and set **Email Status** (`is_active`): `Yes` (send live), `Debug` (redirect to the debug list), or `No` (suppress — the default). Fill the email templates + the internal recipient list, and the approval-letter template.
- The public intake form uses the tenant's `cis.captcha.CaptchaField` (cis ≥ v0.1.27a; older cis falls back to django-recaptcha). Configure the provider the tenant uses: `RECAPTCHA_PUBLIC_KEY` / `RECAPTCHA_PRIVATE_KEY` for reCAPTCHA, or `CAPTCHA_PROVIDER = 'altcha'` + `ALTCHA_HMAC_KEY` + a shared cache for ALTCHA. (For local/dev/preview, set env `CAPTCHA_TESTING=True` to bypass.)
- The approval-letter PDF requires `pdfkit` + `wkhtmltopdf` in the runtime.

---

## Configuration (the `new_school_application` Setting)

Stored under the Setting key `new_school_application`. Notable fields:

| Field | Purpose |
|-------|---------|
| `is_active` | Email gate: `Yes` / `Debug` / `No` |
| `debug_email_list` | Recipients used when `is_active=Debug` |
| `app_start_page_header`, `app_course_page_header` | Intake page intro copy |
| `app_started_email_recipient` | Internal notification recipient(s) |
| `new_applicant_email[_subject]` | Welcome-to-submitter email |
| `app_submitted_email[_subject]` | Internal "submitted/under review" notice |
| `app_ready_email[_subject]` | Reviewer-assigned email |
| `app_reviewed_email[_subject]` | Review-decision notice to staff |
| `app_approved_email[_subject]` | Approval email |
| `app_approved_letter` | Approval-letter PDF template (HTML; `{{highschool_name}}`, `{{principal_firstname}}`, `{{interested_courses_status}}`, …) |

Email templates render with Django `{{ shortcode }}` variables; user-supplied data is auto-escaped.

---

## Portals & endpoints

| Portal | Mount | Namespace | Gate |
|--------|-------|-----------|------|
| Public intake | `/new_school_application/` | `new_school_application` | none (captcha) |
| CE admin | `/ce/new_school_applications/` | `new_school_application_ce` | `user_has_cis_role` / `CISUserOnly` |
| Faculty review | `/faculty/new_school_application/` | `new_school_application_faculty` | `user_has_faculty_role` / `FacultyUserOnly` |

---

## Running tests

```bash
docker exec -w /app/webapp django_web_ewu python manage.py test new_school_application -v 1
```

See `CLAUDE.md` for the test conventions (group-based role users, the `django_login_history` signal disconnect, `CAPTCHA_TESTING`, the minimal `Course` fixture, storage mocking).

---

## Releasing (package maintainers)

This app follows the Canusia submodule release flow (like `class_visit`):

1. Commit changes in the submodule; run the `submod-package-manifest` check (ensure new template/static/data dirs ship).
2. Tag a release and push to `Canusia/package-new_school_application`.
3. Bump the host `requirements.txt` pin (and the submodule pointer on `dev`).

Migrations that reference `cis` must depend on `('cis', '__first__')` (not a tenant-specific migration number) — see the `submod-migration-deps` convention.
