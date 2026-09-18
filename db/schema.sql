-- RDCM database schema — design draft for review (see docs/ARCHITECTURE.md)
-- Covers: branches/rooms/chairs, doctors, patients, appointments (dual-resource
-- constraint), procedures, bills, payments, dues, audit log.
-- Not yet wired into Django migrations — this is the reviewable design artifact
-- requested before Phase 1 application code.

CREATE EXTENSION IF NOT EXISTS btree_gist;   -- required for EXCLUDE USING gist below
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()

-- =====================================================================
-- 1. ORGANIZATION: branches, rooms, chairs
-- =====================================================================

CREATE TABLE branches (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    address         text,
    phone           text,
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- A physical room; a room has a type that governs which procedures may be
-- booked into any chair inside it (e.g. only OT rooms host surgical procedures).
CREATE TABLE rooms (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       uuid NOT NULL REFERENCES branches(id),
    name            text NOT NULL,               -- e.g. "First Floor - Room 4"
    floor           text NOT NULL,                -- 'ground' | 'first' | 'cdrf' | 'ot'
    room_type       text NOT NULL DEFAULT 'general'
                        CHECK (room_type IN ('general', 'ot', 'cdrf')),
    is_active       boolean NOT NULL DEFAULT true,
    UNIQUE (branch_id, name)
);

-- The bookable unit. Most rooms have one chair; some may have more.
CREATE TABLE chairs (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id           uuid NOT NULL REFERENCES branches(id),
    room_id             uuid NOT NULL REFERENCES rooms(id),
    code                text NOT NULL,            -- short label shown in the UI, e.g. "OT-1"
    default_buffer_minutes integer NOT NULL DEFAULT 10,  -- chair turnaround/cleaning time
    status              text NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'inactive', 'maintenance')),
    UNIQUE (branch_id, code)
);

-- =====================================================================
-- 2. USERS, ROLES, STAFF (stub now; full RBAC enforcement in Phase 3)
-- =====================================================================

CREATE TABLE roles (
    id      smallint PRIMARY KEY,
    code    text UNIQUE NOT NULL   -- 'owner' | 'admin' | 'doctor' | 'receptionist'
                                     -- | 'dental_assistant' | 'lab_technician' | 'accountant'
);

CREATE TABLE users (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    phone           text UNIQUE,
    email           text UNIQUE,
    password_hash   text NOT NULL,
    role_id         smallint NOT NULL REFERENCES roles(id),
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Staff-to-branch assignment (a user can work at more than one branch).
CREATE TABLE staff_branches (
    user_id     uuid NOT NULL REFERENCES users(id),
    branch_id   uuid NOT NULL REFERENCES branches(id),
    PRIMARY KEY (user_id, branch_id)
);

CREATE TABLE doctors (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL UNIQUE REFERENCES users(id),
    registration_no     text,
    specialization      text,
    is_active           boolean NOT NULL DEFAULT true
);

-- Recurring weekly availability, e.g. "Dr. Rao is at Branch A, Room type any,
-- Mon/Wed/Fri 10:00-14:00". Concrete one-off exceptions (leave, extra day) are
-- layered on top in doctor_schedule_exceptions.
CREATE TABLE doctor_availability (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id       uuid NOT NULL REFERENCES doctors(id),
    branch_id       uuid NOT NULL REFERENCES branches(id),
    day_of_week     smallint NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Sunday
    start_time      time NOT NULL,
    end_time        time NOT NULL,
    effective_from  date NOT NULL,
    effective_to    date,                          -- NULL = still in effect
    CHECK (end_time > start_time)
);

CREATE TABLE doctor_schedule_exceptions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id       uuid NOT NULL REFERENCES doctors(id),
    date            date NOT NULL,
    is_available    boolean NOT NULL,              -- false = on leave that day
    start_time      time,                           -- NULL if unavailable all day
    end_time        time,
    reason          text,
    UNIQUE (doctor_id, date)
);

-- Optional third resource. Empty/unused today; appointment_assistants exists
-- now specifically so adding assistant-booking later needs no restructuring.
CREATE TABLE assistants (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL UNIQUE REFERENCES users(id),
    is_active       boolean NOT NULL DEFAULT true
);

-- =====================================================================
-- 3. PATIENTS (demographics only here; medical history/dental chart are
--    Phase-later but the FK anchor point is established now)
-- =====================================================================

CREATE TABLE patients (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    uhid                text UNIQUE NOT NULL,       -- clinic-facing patient number
    registered_at_branch_id uuid REFERENCES branches(id),
    name                text NOT NULL,
    date_of_birth       date,
    gender              text CHECK (gender IN ('male', 'female', 'other')),
    phone               text,
    email               text,
    address             text,
    referred_by         text,
    created_by          uuid REFERENCES users(id),
    created_at          timestamptz NOT NULL DEFAULT now()
);
-- Patients are shared across branches by design (§2 of ARCHITECTURE.md) —
-- a patient registered at one branch can be booked/billed at another.

-- =====================================================================
-- 4. PROCEDURES & RATES
-- =====================================================================

CREATE TABLE procedures (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code                    text UNIQUE NOT NULL,
    name                    text NOT NULL,
    category                text,
    default_duration_minutes integer NOT NULL,
    requires_room_type      text CHECK (requires_room_type IN ('ot', 'cdrf')), -- NULL = any room
    default_rate            numeric(10,2) NOT NULL,
    is_active               boolean NOT NULL DEFAULT true
);

-- Per-doctor or per-plan (e.g. insurance/corporate) rate override.
CREATE TABLE procedure_rate_overrides (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    procedure_id    uuid NOT NULL REFERENCES procedures(id),
    doctor_id       uuid REFERENCES doctors(id),      -- NULL = applies to all doctors
    plan_name       text,                              -- NULL = not plan-specific; e.g. 'ABC Insurance'
    rate            numeric(10,2) NOT NULL,
    effective_from  date NOT NULL,
    effective_to    date
);

-- =====================================================================
-- 5. TREATMENT PLANS (multi-visit, e.g. RCT over 3 sittings)
-- =====================================================================

CREATE TABLE treatment_plans (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      uuid NOT NULL REFERENCES patients(id),
    doctor_id       uuid NOT NULL REFERENCES doctors(id),
    title           text NOT NULL,                    -- e.g. "RCT - tooth 36"
    planned_sittings integer NOT NULL DEFAULT 1,
    status          text NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'completed', 'abandoned')),
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- =====================================================================
-- 6. APPOINTMENTS — the dual-resource (chair + doctor) core
-- =====================================================================

CREATE TABLE appointments (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id           uuid NOT NULL REFERENCES branches(id),
    patient_id          uuid NOT NULL REFERENCES patients(id),
    doctor_id           uuid NOT NULL REFERENCES doctors(id),
    chair_id            uuid NOT NULL REFERENCES chairs(id),
    treatment_plan_id   uuid REFERENCES treatment_plans(id),   -- NULL for standalone visits

    start_time          timestamptz NOT NULL,
    end_time             timestamptz NOT NULL,
    buffer_minutes       integer NOT NULL DEFAULT 10,
    -- Generated column: the chair is reserved until end_time + buffer.
    -- Doctor exclusion (below) uses end_time directly, with no buffer.
    blocked_until        timestamptz GENERATED ALWAYS AS (end_time + make_interval(mins => buffer_minutes)) STORED,

    status              text NOT NULL DEFAULT 'scheduled'
                            CHECK (status IN ('scheduled', 'checked_in', 'in_progress',
                                               'completed', 'cancelled', 'no_show')),
    booking_type        text NOT NULL DEFAULT 'regular'
                            CHECK (booking_type IN ('regular', 'walk_in', 'emergency')),

    notes               text,
    cancelled_reason    text,
    cancelled_by        uuid REFERENCES users(id),
    cancelled_at        timestamptz,

    created_by          uuid NOT NULL REFERENCES users(id),
    created_at          timestamptz NOT NULL DEFAULT now(),

    CHECK (end_time > start_time),

    -- ---- THE double-booking guarantee (see ARCHITECTURE.md §4) ----
    -- A chair cannot host two overlapping *active* appointments.
    -- A doctor cannot be in two places at once, either.
    -- Both are enforced here, at the database level, independent of the UI
    -- or application code — this is what makes it safe under concurrent
    -- receptionists booking in the same second.
    EXCLUDE USING gist (
        chair_id WITH =,
        tstzrange(start_time, blocked_until) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'no_show')),

    EXCLUDE USING gist (
        doctor_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'no_show'))
);

CREATE INDEX idx_appointments_branch_start ON appointments (branch_id, start_time);
CREATE INDEX idx_appointments_doctor_start ON appointments (doctor_id, start_time);
CREATE INDEX idx_appointments_chair_start ON appointments (chair_id, start_time);
CREATE INDEX idx_appointments_patient ON appointments (patient_id);

-- One appointment can cover multiple procedures (and multiple teeth per
-- procedure, in FDI notation, e.g. {'36','37'}).
CREATE TABLE appointment_procedures (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id  uuid NOT NULL REFERENCES appointments(id),
    procedure_id    uuid NOT NULL REFERENCES procedures(id),
    tooth_numbers   text[]                              -- FDI notation, e.g. {'36'}
);

-- Optional third resource (see ARCHITECTURE.md §7 / assistants above).
-- Empty today by design; no schema change needed to start using it.
CREATE TABLE appointment_assistants (
    appointment_id  uuid NOT NULL REFERENCES appointments(id),
    assistant_id    uuid NOT NULL REFERENCES assistants(id),
    PRIMARY KEY (appointment_id, assistant_id)
);

-- No-show tracking is just status = 'no_show' on the appointment itself
-- (queryable directly; no separate table needed).

-- =====================================================================
-- 7. BILLING — append-only (see ARCHITECTURE.md §5)
-- =====================================================================

CREATE TABLE bills (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       uuid NOT NULL REFERENCES branches(id),
    patient_id      uuid NOT NULL REFERENCES patients(id),
    bill_no         text NOT NULL UNIQUE,
    bill_date       date NOT NULL DEFAULT CURRENT_DATE,
    status          text NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'finalized', 'cancelled')),
    created_by      uuid NOT NULL REFERENCES users(id),
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- A line item: one procedure, on one visit, at the rate actually charged.
-- Once a bill is finalized, rows here are never updated or deleted —
-- corrections go into bill_adjustments instead.
CREATE TABLE bill_items (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id             uuid NOT NULL REFERENCES bills(id),
    appointment_id      uuid REFERENCES appointments(id),   -- NULL if billed without a visit record
    procedure_id        uuid NOT NULL REFERENCES procedures(id),
    doctor_id           uuid NOT NULL REFERENCES doctors(id),  -- for revenue attribution
    tooth_numbers       text[],
    quantity            integer NOT NULL DEFAULT 1,
    rate                numeric(10,2) NOT NULL,
    discount_amount     numeric(10,2) NOT NULL DEFAULT 0,
    discount_reason     text,
    discount_approved_by uuid REFERENCES users(id),
    net_amount          numeric(10,2) NOT NULL,       -- (rate * quantity) - discount_amount
    created_by          uuid NOT NULL REFERENCES users(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    CHECK (discount_amount >= 0 AND discount_amount <= rate * quantity)
);

CREATE TABLE discount_approval_thresholds (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         smallint NOT NULL REFERENCES roles(id),
    max_percent     numeric(5,2),      -- role can self-approve up to this % without escalation
    max_amount      numeric(10,2)
);

-- A payment transaction. total_amount = sum of its payment_modes rows.
CREATE TABLE payments (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       uuid NOT NULL REFERENCES branches(id),
    patient_id      uuid NOT NULL REFERENCES patients(id),
    payment_date    timestamptz NOT NULL DEFAULT now(),
    total_amount    numeric(10,2) NOT NULL,
    received_by     uuid NOT NULL REFERENCES users(id),
    notes           text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Split payments across modes on a single payment (e.g. part cash, part card).
CREATE TABLE payment_modes (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id      uuid NOT NULL REFERENCES payments(id),
    mode            text NOT NULL CHECK (mode IN ('cash', 'card', 'upi', 'bank_transfer', 'insurance')),
    amount          numeric(10,2) NOT NULL CHECK (amount > 0),
    reference_no    text                                  -- txn id / cheque no / auth code
);

-- A payment can be allocated across multiple bills — this is how an old due
-- from a previous visit gets recovered alongside today's bill from a single
-- payment at reception.
CREATE TABLE payment_allocations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id      uuid NOT NULL REFERENCES payments(id),
    bill_id         uuid NOT NULL REFERENCES bills(id),
    amount_allocated numeric(10,2) NOT NULL CHECK (amount_allocated > 0)
);

-- Refunds, write-offs, and post-finalization corrections. Never edit
-- bill_items/payments directly — insert an adjustment instead.
CREATE TABLE bill_adjustments (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id         uuid NOT NULL REFERENCES bills(id),
    type            text NOT NULL CHECK (type IN ('refund', 'write_off', 'correction', 'cancellation')),
    amount          numeric(10,2) NOT NULL,
    reason          text NOT NULL,
    approved_by     uuid NOT NULL REFERENCES users(id),
    created_by      uuid NOT NULL REFERENCES users(id),
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Outstanding dues, net billed, and collected are always *computed*, never
-- stored as a mutable balance. Example (per patient):
--
--   SELECT
--       p.id,
--       COALESCE(billed.total, 0)      AS net_billed,
--       COALESCE(collected.total, 0)   AS collected,
--       COALESCE(adjustments.total, 0) AS adjustments,
--       COALESCE(billed.total, 0) - COALESCE(collected.total, 0)
--           - COALESCE(adjustments.total, 0) AS outstanding_due
--   FROM patients p
--   LEFT JOIN (SELECT b.patient_id, SUM(bi.net_amount) total
--              FROM bills b JOIN bill_items bi ON bi.bill_id = b.id
--              WHERE b.status != 'cancelled' GROUP BY b.patient_id) billed
--          ON billed.patient_id = p.id
--   LEFT JOIN (SELECT pay.patient_id, SUM(pa.amount_allocated) total
--              FROM payment_allocations pa
--              JOIN payments pay ON pay.id = pa.payment_id
--              GROUP BY pay.patient_id) collected
--          ON collected.patient_id = p.id
--   LEFT JOIN (SELECT b.patient_id, SUM(ba.amount) total
--              FROM bill_adjustments ba JOIN bills b ON b.id = ba.bill_id
--              WHERE ba.type IN ('write_off') GROUP BY b.patient_id) adjustments
--          ON adjustments.patient_id = p.id;
--
-- (Refunds reduce `collected`, not `billed` — modeled as a negative
-- payment_allocation-equivalent in the real query; exact SQL will be
-- finalized as a Django view/queryset in Phase 2, this is the shape.)

-- =====================================================================
-- 8. AUDIT LOG
-- =====================================================================

CREATE TABLE audit_log (
    id              bigserial PRIMARY KEY,
    table_name      text NOT NULL,
    record_id       uuid NOT NULL,
    action          text NOT NULL CHECK (action IN ('insert', 'update', 'delete')),
    user_id         uuid REFERENCES users(id),
    old_values      jsonb,
    new_values      jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_log_table_record ON audit_log (table_name, record_id);

-- Populated primarily via application middleware (has the request's user_id
-- available, which a raw DB trigger does not, unless we thread it through
-- session variables). A trigger-based backstop on bills/bill_items/payments/
-- bill_adjustments is added in Phase 2 specifically because those tables
-- must be provably tamper-evident even against a direct DB edit.
