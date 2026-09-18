# RDCM — Architecture & Design Decisions

Decisions confirmed with the clinic owner on 2026-09-18. This document
is the reference point for every phase that follows — if a later
decision contradicts something here, update this file in the same
commit that makes the change, and say why.

## 1. Deployment model: on-premise LAN server

The clinic must keep booking, billing, and the queue board working
with **zero internet dependency**. This rules out pure cloud SaaS and
rules out "cloud + offline sync," which is a much harder engineering
problem (conflict resolution on the dual-resource booking constraint
across disconnected replicas is genuinely hard to get right, and is
one of the most expensive things to retrofit if we get it wrong now).

Instead:

- A single server (Linux box, on-site) runs Postgres + the
  application backend, on the clinic's LAN.
- All terminals — reception, doctor rooms, accounts, the TV queue
  board — are thin clients (a browser) pointed at the server's LAN
  address. No install, no per-terminal state.
- Internet is only needed for: off-site backup upload, SMS/WhatsApp
  appointment reminders, and (optionally) remote access/VPN for the
  owner to check reports from home.
- Runs via Docker Compose for reproducibility (`db`, `backend`,
  `nginx` reverse proxy containers). One `docker compose up` restores
  the whole stack on replacement hardware.

**Consequence:** we own backup and hardware failure, not a cloud
provider. Automated nightly `pg_dump` to a second local disk *and* an
encrypted off-site copy (cloud storage, uploaded when internet is up)
is non-negotiable — see §6.

## 2. Multi-branch from day one

Schema threads `branch_id` through every branch-scoped table (chairs,
rooms, appointments, bills, payments, staff assignments) from the
first migration. Patients, procedures master list, and user accounts
are **not** branch-scoped — a patient or a procedure code is shared
across branches; a receptionist's/doctor's assignment to a branch is
a separate join table so staff can work at more than one branch.

Retrofitting a tenant/branch column onto a live system with real
patient and financial data is high-risk (easy to miss a table, easy
to leak data across branches in a forgotten query). Paying that cost
now, while the schema is empty, is far cheaper.

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Database | **PostgreSQL 16** | The double-booking constraint ("prevent this at the database level, not just the UI") is solved cleanly with a Postgres `EXCLUDE USING gist` constraint over time ranges — see §4. No other mainstream open-source DB does this natively. This one feature justifies the choice on its own. |
| Backend | **Python + Django + Django REST Framework** | Batteries-included: auth, migrations, the built-in admin site (genuinely useful for a small ops team doing back-office data fixes without needing a custom UI for everything), and a mature permissions framework we extend for RBAC. Large hiring pool, boring and well-documented — the right trade for a small team maintaining this for years, not a startup optimizing for cleverness. |
| Realtime (queue board) | **Django Channels** (WebSockets) over the LAN | The now-serving board needs to update the instant reception calls a patient or the lab marks "patient waiting" — polling is an acceptable fallback but a LAN WebSocket is cheap here since there's no internet-scale concern. |
| Frontend | **React + TypeScript SPA**, calling the DRF API | Day/week calendar views with drag-to-reschedule are genuinely easier in a proper frontend framework than server-rendered pages. Kept thin — no heavy state-management framework; React Query (or equivalent) for server state is enough. |
| Deployment | Docker Compose on one on-site Linux server, Nginx reverse proxy, terminals as browsers on the LAN | See §1. |
| Backups | `pg_dump` nightly cron → local second disk + encrypted off-site upload; monthly restore drill | See §6. |

Rejected alternatives worth naming: MySQL/MariaDB (no equivalent to
`EXCLUDE USING gist`; the double-booking guarantee would have to live
in application-level locking, which is the exact thing the brief
asked us to avoid). A Node/TypeScript backend was also viable and
would work fine — Django wins mainly on the built-in admin and a more
opinionated, harder-to-misuse permissions/migrations story for a
small team.

## 4. Preventing double-booking at the database level

This is the load-bearing decision in the whole schema. Two
`EXCLUDE USING gist` constraints (Postgres `btree_gist` extension) on
the `appointments` table:

- **Chair exclusion:** no two active appointments may overlap for the
  same `chair_id`, over the range `[start_time, blocked_until)` where
  `blocked_until = end_time + buffer_minutes` (buffer is chair
  turnaround/cleaning time, so it's part of the chair's reserved
  window, not the doctor's).
- **Doctor exclusion:** no two active appointments may overlap for
  the same `doctor_id`, over `[start_time, end_time)` — no buffer,
  since a doctor can walk straight to another chair.

Both constraints exclude cancelled/no-show rows via a `WHERE status IN
(...)` partial index, so a cancelled slot doesn't block rebooking.

This means: **a booking attempt that would double-book either
resource is rejected by Postgres itself**, with a clean, catchable
error (`23P01 exclusion_violation`), regardless of how many
receptionists hit "book" in the same second, regardless of any bug in
application-level validation. The UI still does a pre-check for a
good user experience (so the receptionist sees "slot taken" instantly
instead of a raw DB error), but the constraint is the actual
guarantee.

## 5. Financial records are append-only

No `UPDATE` or `DELETE` is ever issued against `bill_items`,
`payments`, or `payment_modes` once a bill is finalized. Every
correction — refund, discount reversal, write-off, cancellation — is
a new row in `bill_adjustments` that references what it adjusts and
carries a reason and an approver. A patient's or bill's "outstanding
due" is always a computed sum over the full history, never a mutable
balance field. This is what makes the audit trail true by
construction rather than by discipline — nobody can quietly edit
history, including us, including from the Django admin (write
permissions on those three tables are revoked for everyone; the admin
can *view* for troubleshooting, not edit).

## 6. Backup & restore

- Nightly `pg_dump` (custom format) to local disk, retained 30 days.
- Weekly copy uploaded off-site (encrypted) when internet is available;
  catches up automatically once connectivity returns.
- **Restore path is tested, not assumed**: a monthly scripted restore
  into a scratch database + row-count/checksum sanity check, logged.
  An untested backup is not a backup.

## 7. Roles (RBAC — enforced in Phase 3, named now because it shapes the schema)

| Role | Notes |
|---|---|
| `owner` | Full access, all branches. |
| `admin` | Full operational access, configurable per-branch. |
| `doctor` | Own clinical notes/charts (read-write), own schedule, own patients' history. Cannot approve their own discounts (enforced at the approval-workflow level, not just UI). |
| `receptionist` | Booking, patient demographics, billing/payments. **No access to clinical notes, dental chart, or medical history.** |
| `dental_assistant` | Clinical support view; scope TBD in Phase 3. |
| `lab_technician` | Lab job tracking, "patient waiting" flag. |
| `accountant` | Billing, payments, dues, revenue reports. No clinical access. |

Discount approval thresholds are a table keyed by role
(`discount_approval_thresholds`), not hardcoded, so the owner can
change them without a deployment.

## 8. Patient numbering & duplicate merge

- **UHID is sequential per branch**: `{branch.code}-{sequence:06d}`
  (e.g. `RDC1-000001`), generated via `branch_patient_sequences`
  (row-locked `UPDATE ... RETURNING` in the same transaction as the
  patient insert — safe under concurrent registrations).
- **Duplicate registrations are merged, never deleted.** A duplicate
  patient record is common at a busy reception desk. Deleting one and
  repointing history by hand is exactly the kind of thing that quietly
  corrupts financial/clinical history, so it's a first-class,
  audited operation instead: `patient_merges` records who merged what
  into what and why; the merge transaction re-points
  `appointments`/`bills`/`payments`/`treatment_plans` from the
  duplicate to the surviving record, marks the duplicate
  `status = 'merged'`, and logs every repointed row to `audit_log`.
  The old UHID keeps resolving (via `merged_into_patient_id`) since
  physical paperwork and old receipts reference it. Restricted to
  admin/owner.

## 9. Open items deferred to their phase

- Detailed permission matrix per role (Phase 3).
- Lab work tracking schema, inventory, recall reminders — noted as
  extension points below, not built yet.
- Report query design (Phase 4).
