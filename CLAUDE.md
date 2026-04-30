# Imams Connect — Claude Notes

## Project purpose
A Django web app that connects mosques with Jumuah khatibs (imams). Mosques request specific Fridays; an admin assigns imams; imams track their bookings and complete training.

## Stack
- Django 6.0.4, Python 3.14, PostgreSQL (psycopg2), Docker Compose
- No frontend build step — plain CSS in `<style>` blocks, no JS framework
- `ATOMIC_REQUESTS = True` in settings

## Running locally
```
docker compose up --build
```
App on :8000, Adminer (DB browser) on :8080.
Default superuser: username `a`, password `p` (set in docker-compose.yml env).
`entrypoint.sh` runs `makemigrations` + `migrate` + `createsuperuser --noinput` on every boot.

## Auth model (custom, not Django auth)
Portal auth uses Django sessions, not Django's auth system:
- `request.session["mosque_id"]` — logged-in mosque
- `request.session["imam_id"]` — logged-in imam
- Login = enter your ID as both username and password
- Decorators: `mosque_login_required`, `imam_login_required` (in views.py)
- Context processor `scheduler.context_processors.portal_session` exposes `session_mosque_id` / `session_imam_id` to all templates
- Admin pages use `@staff_member_required` (Django's decorator)

## Data model (scheduler/models.py)
Seven models:
- `Mosque` — name, address, phone, attendees, requires_imam, preferred_imam (nullable FK → Imam)
- `Imam` — name, address, phone; `.is_trained` property checks TrainingProgress count
- `TrainingVideo` — title, url (URLField), order; `.youtube_id()` extracts 11-char YouTube ID via regex
- `TrainingProgress` — (imam, video) unique_together; auto timestamp
- `ImamUnavailability` — (imam, jumuah_date) unique_together
- `WeekRequest` — (mosque, jumuah_date) unique_together; `.is_assigned` checks for related Assignment
- `Assignment` — OneToOne → WeekRequest, FK → Imam; enforces one imam per slot

## URL structure (scheduler/urls.py)
| Path | Name | Notes |
|---|---|---|
| `/` | home | |
| `/register/mosque/` | mosque_request | Public registration |
| `/register/imam/` | imam_application | Public registration |
| `/success/<kind>/<pk>/` | success | Post-registration |
| `/panel/` | admin_panel | Combined admin (schedule + mosque/imam lists + training) |
| `/login/mosque/` | mosque_login | |
| `/login/imam/` | imam_login | |
| `/logout/` | portal_logout | |
| `/portal/mosque/` | mosque_portal | |
| `/portal/mosque/request/` | request_friday | |
| `/portal/mosque/cancel/<pk>/` | cancel_week_request | |
| `/portal/mosque/preferred/` | set_preferred_imam | |
| `/portal/imam/` | imam_portal | |
| `/portal/imam/availability/` | toggle_unavailability | |
| `/portal/imam/training/` | imam_training | |
| `/portal/imam/training/done/<pk>/` | mark_video_done | |

## Admin panel (`/panel/`)
Single combined page with four anchor sections: `#schedule`, `#mosques`, `#imams`, `#training`.
All POST actions routed through one view via hidden `action` field: `assign`, `add_video`, `delete_video`.

Schedule sort order: `requires_imam` DESC (true first), then `attendees` DESC.
Preferred imam shown first in assignment dropdown (★ prefix). Unavailable imams labelled `(unavailable)` but NOT disabled — admin can override. Untrained and already-assigned imams ARE disabled (hard constraints).

## Key view helpers
```python
_get_friday(d)       # next Friday from date d (returns same day if already Friday)
_upcoming_fridays()  # list of Fridays from today up to 60 days ahead
_trained_imam_ids()  # set of imam PKs with full training; None if no videos exist
```

## Template conventions
- All templates extend `scheduler/base.html`
- Styles are inline `<style>` in `{% block extra_style %}` — no external CSS files
- Green brand colour: `#1b4332`; light green: `#d8f3dc`
- Badge classes: `badge-green`, `badge-amber`, `badge-red`, `badge-gray`, `badge-blue`
- YouTube embeds: `https://www.youtube.com/embed/<youtube_id>` in an `<iframe>`
- Template arithmetic limitations: compute derived values in the view (Django's `add` filter can't subtract)

## Migrations
Run inside Docker; `entrypoint.sh` handles it automatically. For manual runs:
```
docker compose exec imams python manage.py makemigrations scheduler
docker compose exec imams python manage.py migrate
```
