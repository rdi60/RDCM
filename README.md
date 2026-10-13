# RDCM — Raja Dental Clinic Management

A clinic management system: admin panel (doctors, users, roles, MIS reports),
appointment scheduling across chairs/OTs, billing (invoices & receipts),
inventory, and links out to HRMS and the patient queue board.

Built with Django + PostgreSQL. See the project roadmap for the full phase
plan; this repo currently covers:

**Phase 0 — foundations**
- Custom user model (`accounts.User`), ready for later per-role profiles
  (Doctor, Employee, ...) to extend
- Default role groups (Clinic Admin, Doctor, Receptionist, Accountant,
  Nurse/Assistant) via `manage.py seed_roles` — permissions for each module
  attach to these groups as that module is built
- Login/logout, a dashboard shell listing upcoming modules, Django Admin
  wired up as the back-office screen for user/role management
- Docker Compose setup (Django/Gunicorn + PostgreSQL + Nginx) for deploying
  to a VPS

**Phase 1 — admin core** (`clinic` app)
- Doctor enrollment: name, registration number, specialties, consultation
  fee, and multiple degrees/qualifications per doctor (inline on the admin
  form) — a doctor doesn't need a login account to be enrolled
- Chairs & OTs as bookable `Resource` records, seeded via
  `manage.py seed_resources` (defaults to your 16 chairs + 2 OTs, flags
  let you change the counts)
- Treatment price catalog (name, category, default duration, price)
- All managed through Django Admin; the dashboard's "Clinic setup" section
  (staff only) links straight to each changelist

## Running locally

Requires Python 3.12+ and a PostgreSQL server.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit DJANGO_SECRET_KEY and the POSTGRES_* values
                        # to match a database you've created locally

python manage.py migrate
python manage.py seed_roles
python manage.py seed_resources   # creates Chair 1-16 and OT 1-2
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`, sign in, and `/admin/` for the back-office
screens (users, groups/roles).

## Running with Docker (closer to the VPS setup)

```bash
cp .env.example .env   # edit values; set DJANGO_SETTINGS_MODULE=config.settings.prod
                        # and DJANGO_ALLOWED_HOSTS to your real domain/IP
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
```

Nginx listens on port 80 and proxies to the Django app; static/media files
are served by Nginx from shared volumes. The `web` container's entrypoint
runs migrations and `seed_roles` automatically on every start.

## Project layout

```
config/            Django settings (base/dev/prod), root URLs, WSGI/ASGI
accounts/          Custom user model, role groups, Django Admin customization
clinic/            Doctors, specialties, qualifications, chairs/OTs, treatments
core/              Dashboard shell, clinic-wide template context
templates/, static/  Shared templates and CSS
docker/, nginx/    Deployment: entrypoint script, Nginx reverse-proxy config
```

Each later phase (appointments, billing, inventory, MIS reports) adds its
own Django app alongside `accounts` and `core`, following the same pattern.
