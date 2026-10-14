# Security & HIPAA Compliance

RDCM implements a set of **technical safeguards** aligned with the HIPAA
Security Rule (45 CFR §164.312). This document lists what the application
code does, and — just as importantly — what it deliberately does **not**
and **cannot** do, because those pieces are organizational, physical, legal,
or infrastructure decisions that belong to the clinic running this system,
not to the codebase.

**This document is not legal advice and does not by itself make this
deployment "HIPAA compliant."** Compliance is a property of an
organization's people, policies, and infrastructure as a whole, not of any
one piece of software. Get a qualified compliance/legal review before
treating any US patient data under HIPAA.

## What the code does (technical safeguards, §164.312)

| Safeguard | Requirement | Implementation |
|---|---|---|
| Access control — unique user ID | §164.312(a)(2)(i) | Django's built-in per-user accounts (`accounts.User`) |
| Access control — automatic logoff | §164.312(a)(2)(iii) | Sliding session idle timeout (`SESSION_IDLE_TIMEOUT_SECONDS`, default 15 min) |
| Access control — encryption/decryption | §164.312(a)(2)(iv) | Field-level encryption at rest (`core.fields.EncryptedTextField`, Fernet/AES) for `Patient.medical_history` and `Appointment.notes`; TLS in transit (see deployment notes below) |
| Access control — person/entity authentication | §164.312(d) | Password login + mandatory TOTP multi-factor authentication (`core.middleware.RequireOTPMiddleware`), enforced for every account with no opt-out; account lockout after repeated failed logins (`django-axes`) |
| Access control — minimum necessary | §164.312(a)(1), Privacy Rule | Role-based access control via Django's permission system — five roles (Clinic Admin, Doctor, Receptionist, Accountant, Nurse/Assistant), each granted only the model-level permissions its job needs (`accounts/management/commands/seed_roles.py`), enforced on every view with `@permission_required` |
| Audit controls | §164.312(b) | `audit` app: every create/update/delete of a PHI or financial record, every PHI detail-page view, and every login/logout/failed-login is logged with user, timestamp, IP, and record identity. Read-only in Django Admin — audit rows cannot be edited or deleted through the app, including by admins |
| Integrity | §164.312(c)(1) | Supported by the audit trail above (who changed what, when) and by signed-ledger patterns in billing/inventory (balances are always derived from transaction history, never a mutable running total) |
| Transmission security | §164.312(e)(1) | HTTPS enforced in production settings; the WhatsApp recall reminder omits treatment/doctor details by default (`WHATSAPP_INCLUDE_CLINICAL_DETAILS`, off unless you have a Business Associate Agreement with a WhatsApp Business Solution Provider — standard consumer WhatsApp has none) |

## What is NOT covered by code — your organization's responsibility

HIPAA's Security Rule also requires **administrative** and **physical**
safeguards (§164.308, §164.310), none of which software can satisfy on its
own:

- **Business Associate Agreements (BAAs).** Every third party that could
  touch PHI needs one before you use them for that purpose: your hosting/VPS
  provider, any backup storage provider, any SMS/WhatsApp/email provider you
  use for patient communication, any analytics or monitoring service. This
  deployment does not include any such vendor relationship — you select and
  contract with them.
- **Risk analysis & risk management plan** (§164.308(a)(1)). A documented,
  periodically-updated assessment of where PHI lives, what could go wrong,
  and what you're doing about it. Required before you can say you're
  compliant, and no application can do this for you.
- **Designated Security Officer and Privacy Officer** (§164.308(a)(2),
  §164.530(a)). Named individuals responsible for this program.
- **Workforce training & sanction policy** (§164.308(a)(5)). Staff need to
  be trained on what PHI is, how to handle it, and what happens if they
  don't — covering things no amount of RBAC can prevent, like photographing
  a screen or discussing a patient in a waiting room.
- **Contingency plan** (§164.308(a)(7)): tested backups, a documented
  disaster-recovery procedure, and an emergency-access procedure for when
  normal login isn't available. This repository includes a Docker Compose
  deployment but no backup schedule or restore drill — set one up and test
  it before go-live.
- **Facility & device security** (§164.310): physical access control to
  wherever the server/VPS actually runs, workstation security policies for
  front-desk and clinical terminals, and secure disposal procedures for any
  retired hardware or media that ever held PHI.
- **Key management.** `FIELD_ENCRYPTION_KEY` must live only in your
  environment's secrets (not in source control, not in a plaintext file
  anyone can read) and you need your own process for who can access it, how
  it's backed up, and how you'd rotate it if it were ever exposed. Losing
  this key permanently loses access to every encrypted field; leaking it
  defeats the encryption entirely. Rotation requires re-encrypting existing
  rows with the new key (a maintenance task, not an automatic one).
- **Breach notification procedure** (§164.400s). A plan for what you're
  legally required to do if PHI is exposed — who you notify, within what
  deadlines, and how.
- **Ongoing access reviews.** RBAC is only as good as its upkeep — someone
  needs to periodically confirm role assignments are still correct
  (an ex-employee's account disabled promptly, a role change reflected,
  etc.) and that the audit log is actually being reviewed, not just
  collected.
- **Patch & vulnerability management.** Keeping the OS, Python, Django, and
  every dependency in this project up to date against known
  vulnerabilities is an ongoing operational task, not a one-time setup
  step.
- **Legal/compliance review.** Whether HIPAA applies to your specific
  situation, whether this technical implementation is sufficient for your
  risk profile, and what your BAAs need to say are all questions for
  qualified counsel, not this document.

## Operational notes for whoever runs this in production

- Set `FIELD_ENCRYPTION_KEY` once per deployment and never change it without
  a planned re-encryption migration.
- Set `SESSION_IDLE_TIMEOUT_SECONDS`, `AXES_FAILURE_LIMIT`, and
  `AXES_COOLOFF_HOURS` to match your own risk tolerance — the defaults
  (900s / 5 attempts / 1 hour) are reasonable starting points, not
  requirements.
- Review `audit.AuditLog` regularly (it's in Django Admin, read-only) —
  logging without review satisfies the letter of §164.312(b) but not its
  intent.
- Every new user must enroll in TOTP MFA on first login; there is
  intentionally no way to disable this per-user from within the app.
