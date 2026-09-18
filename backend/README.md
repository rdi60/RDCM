# RDCM backend — Phase 1

Django + DRF API covering patient records and appointment booking with the
dual-resource (chair + doctor) constraint. See `../docs/ARCHITECTURE.md` for
the decisions behind this, and `../db/schema.sql` for the reviewed schema
this implements.

## Running it

```
cp ../.env.example ../.env   # edit POSTGRES_PASSWORD / DJANGO_SECRET_KEY
docker compose -f ../docker-compose.yml up -d --build
docker compose -f ../docker-compose.yml exec backend python manage.py migrate
docker compose -f ../docker-compose.yml exec backend python manage.py createsuperuser
docker compose -f ../docker-compose.yml exec backend python manage.py seed_demo_data   # optional, fake data for smoke-testing
```

The API is then at `http://<server-lan-ip>:8000/api/...` and the Django
admin at `http://<server-lan-ip>:8000/admin/`.

## Endpoints (Phase 1)

- `GET/POST /api/patients/` — list/search (`?q=`) and register patients.
- `POST /api/patients/{id}/merge/` — merge a duplicate into another patient.
- `GET /api/scheduling/appointments/?branch=&date=` — day view by chair
  (group the response by `chair` client-side).
- `GET /api/scheduling/appointments/?branch=&date=&doctor=` — day view by doctor.
- `GET /api/scheduling/appointments/?doctor=&week_start=` — week view by doctor.
- `POST /api/scheduling/appointments/` — book (chair + doctor + procedures required).
- `POST /api/scheduling/appointments/{id}/reschedule/`
- `POST /api/scheduling/appointments/{id}/cancel/` — requires `reason`.
- `POST /api/scheduling/appointments/{id}/check-in/`, `/start/`, `/complete/`, `/no-show/`
- `GET/POST /api/scheduling/treatment-plans/`

Auth: DRF session auth (log into `/admin/` in a browser, then the browsable
API works) or token auth — token auth isn't wired to an obtain-token
endpoint yet; add `rest_framework.authtoken` and its URL when a real
frontend needs it.

## A note on how this was built and verified

This sandbox's network egress allowlist does not include PyPI, so `pip
install` for Django/DRF/psycopg could not run here — meaning `manage.py
check`, `makemigrations --check`, and the test suite could not be run
against this code in this environment. What **was** verified directly,
against a real local PostgreSQL 16 instance (no network required):

- The full schema in `../db/schema.sql` applies cleanly.
- The chair and doctor exclusion constraints actually reject overlapping
  bookings (including the buffer window), accept a booking that starts
  exactly when the previous one's buffer ends, and don't block rebooking
  a chair/doctor slot freed by cancelling the appointment that held it.
- The `blocked_until` trigger computes the right value (this caught a real
  bug: `timestamptz + interval` is Postgres-`STABLE`, not `IMMUTABLE`, so
  it can't be a `GENERATED` column — see the migration's comments).

The Django migrations in this app mirror that validated SQL as closely as
possible (in `0002_appointment_double_booking_guard.py`, the trigger and
exclusion-constraint SQL is copied verbatim), but the Django layer itself
(model definitions, hand-written migration operations, serializers, views)
has only been reviewed by hand, not executed. **Before relying on this in
the clinic, run it against a real Django install** — at minimum:
`python manage.py migrate`, `python manage.py check`, and a walk through
the booking/reschedule/cancel/merge endpoints — and treat anything that
doesn't match this description as a bug to report back, not a hidden
assumption to work around.
