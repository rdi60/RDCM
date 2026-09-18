from django.db import transaction

from apps.clinic.models import BranchPatientSequence

from .models import Patient, PatientMerge


def generate_uhid(branch) -> str:
    """Atomically allocate the next sequential patient number for a branch.
    Locks the branch's sequence row (SELECT ... FOR UPDATE) so two
    receptionists registering at the same branch in the same second still
    get distinct numbers. Must run inside the same transaction as the
    Patient insert that uses the result — see register_patient below."""
    seq, _ = BranchPatientSequence.objects.select_for_update().get_or_create(branch=branch)
    seq.last_patient_no += 1
    seq.save(update_fields=["last_patient_no"])
    return f"{branch.code}-{seq.last_patient_no:06d}"


@transaction.atomic
def register_patient(*, branch, name, created_by, date_of_birth=None, gender="",
                      phone="", email="", address="", referred_by=""):
    uhid = generate_uhid(branch)
    return Patient.objects.create(
        uhid=uhid,
        registered_at_branch=branch,
        name=name,
        date_of_birth=date_of_birth,
        gender=gender,
        phone=phone,
        email=email,
        address=address,
        referred_by=referred_by,
        created_by=created_by,
    )


@transaction.atomic
def merge_patients(*, source: Patient, target: Patient, reason: str, merged_by) -> PatientMerge:
    """Merge a duplicate patient record into the surviving one. Re-points
    every FK to the source patient onto the target, tombstones the source
    (status='merged'), and records the merge. Never deletes the source row
    — its UHID must keep resolving to old paperwork/receipts.

    Only re-points what exists as of Phase 1 (appointments, treatment
    plans). Phase 2 must extend this with bills/payments/payment
    allocations once those models exist — a duplicate merged before then
    would otherwise leave billing history stuck on the old patient_id.
    """
    if source.pk == target.pk:
        raise ValueError("Cannot merge a patient into itself")
    if source.status == Patient.MERGED:
        raise ValueError("Source patient is already merged")
    if target.status == Patient.MERGED:
        raise ValueError("Target patient is itself a merged (non-surviving) record")

    from apps.scheduling.models import Appointment, TreatmentPlan

    Appointment.objects.filter(patient=source).update(patient=target)
    TreatmentPlan.objects.filter(patient=source).update(patient=target)

    source.status = Patient.MERGED
    source.merged_into = target
    source.save(update_fields=["status", "merged_into"])

    return PatientMerge.objects.create(
        source_patient=source, target_patient=target, reason=reason, merged_by=merged_by,
    )
