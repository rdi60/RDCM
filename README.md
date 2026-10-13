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

**Phase 2 — patients & scheduling** (`scheduling` app)
- Patient registration (contact details, medical history/allergies) with an
  auto-generated UHID (`RD-00001`, ...), and a searchable patient list
- Day view: a custom chair/OT resource grid (16 chairs + 2 OTs as columns,
  time down the rows) — built in-house rather than on FullCalendar's paid
  Premium plugin, which is what resource-timeline views normally require
- Week view: appointment counts per doctor per day, click through to that
  day's full grid
- Booking, rescheduling and cancelling, with double-booking on the same
  chair/OT or the same doctor rejected server-side (`Appointment.clean()`),
  not just hidden in the UI
- A daily per-clinic token number assigned on booking, and a status
  lifecycle (scheduled → confirmed/arrived → in chair → completed, or
  cancelled/no-show) enforced through an explicit allowed-transitions table
  so a stray request can't skip straight from "scheduled" to "completed"

**Phase 4 — billing** (`billing` app)
- Invoices: draft → issued → partially paid/paid, or void. Draft invoices
  hold editable line items (free-text or linked to a `Treatment`); "+ Create
  invoice" from a completed appointment auto-adds its treatment as the first
  line item
- Numbered invoices (`INV-00001`) and receipts (`RCT-00001`), same
  auto-numbering pattern as the patient UHID
- Payments: cash/card/UPI/cheque/insurance, full or partial, with the
  invoice's status recomputed automatically — rejected server-side
  (`Payment.clean()`) if it would overpay the invoice or land on a
  draft/void invoice, not just hidden in the UI
- Voiding is blocked once any payment exists, so a paid invoice can't be
  erased from the record (no refund/credit-note flow yet — a real gap to
  revisit if you need one)
- Print-friendly invoice and receipt pages (clinic letterhead, line items,
  totals) for browser print-to-PDF or paper — no PDF-generation library
  added, since WeasyPrint-style tools need extra system packages that
  complicate the Docker build for not much benefit over a print stylesheet
- Outstanding dues report: every unpaid/partially-paid invoice with its
  balance, plus a running total

**Phase 5 — inventory & procurement** (`inventory` app)
- Full purchasing workflow: `PurchaseOrder` (draft → sent → partially
  received/received, or cancelled) with editable lines while draft, and
  `GoodsReceiptNote`/`GoodsReceiptLine` for receiving against a PO —
  receiving creates a `StockBatch` (with batch number, expiry date, cost
  price) and a stock-in transaction automatically
- Suppliers and Items are master data managed through Django Admin, same
  pattern as Doctors/Resources/Treatments; `StockLocation` records (central
  store, clinical rooms) are too — none are auto-seeded, since the room
  layout wasn't specified, unlike the 16 chairs + 2 OTs
- Every stock movement (receipt, transfer, consumption, future adjustments)
  is a signed row in one `StockTransaction` ledger — current quantity is
  always computed by summing these, never a separately maintained balance
  field, the same approach `Invoice.paid_amount` already uses for payments
- Store → clinical room transfers and per-room consumption are requested by
  item + quantity, not by batch number — staff shouldn't need to know batch
  numbers to move or use stock, so both pick batches oldest-expiry-first
  automatically (`inventory/services.py`), and both reject a request that
  exceeds what's actually available at that location
- Consumption can optionally link to an appointment, so a treatment's
  stock cost is traceable later — not yet rolled up into MIS reports
- Low-stock alerts (below each item's reorder level, clinic-wide) and an
  expiring-within-60-days batch list

Two things intentionally deferred: there's no bill-of-materials linking a
`Treatment` to the items it should auto-consume (consumption is recorded by
hand), and GST-style HSN/SAC codes aren't modeled on `Item`.

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
scheduling/        Patients, appointments, the day/week calendar grid
billing/           Invoices, line items, payments, print pages, dues report
inventory/         Suppliers, items, purchase orders, GRNs, stock ledger
core/              Dashboard shell, clinic-wide template context
templates/, static/  Shared templates and CSS
docker/, nginx/    Deployment: entrypoint script, Nginx reverse-proxy config
```

MIS reports (Phase 6) will be the last app, following the same pattern.
