import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Appointment, AppointmentProcedure

CHAIR_CONSTRAINT_NAME = "appointments_chair_excl"
DOCTOR_CONSTRAINT_NAME = "appointments_doctor_excl"

NOT_RESCHEDULABLE = {Appointment.CANCELLED, Appointment.NO_SHOW, Appointment.COMPLETED}


def _validate_room_type(chair, procedures):
    required = {p.requires_room_type for p in procedures if p.requires_room_type}
    if not required:
        return
    if len(required) > 1:
        raise ValidationError("The selected procedures require different, incompatible room types.")
    required_type = required.pop()
    if chair.room.room_type != required_type:
        raise ValidationError(
            f"This procedure requires a {chair.room.get_room_type_display()} room; "
            f"chair {chair.code} is in a {chair.room.get_room_type_display()} room."
        )


def _friendly_conflict_message(exc):
    text = str(exc)
    if CHAIR_CONSTRAINT_NAME in text:
        return "That chair is already booked for an overlapping time (including its cleaning/turnaround buffer)."
    if DOCTOR_CONSTRAINT_NAME in text:
        return "That doctor already has an overlapping appointment."
    return "This slot conflicts with an existing booking."


@transaction.atomic
def book_appointment(*, branch, patient, doctor, chair, start_time, procedures, created_by,
                      buffer_minutes=None, booking_type=Appointment.REGULAR,
                      treatment_plan=None, notes=""):
    """Book an appointment against a chair + doctor. The room-type check and
    the pre-flight duration calc are for a good error message; the actual
    double-booking guarantee is the database exclusion constraint caught
    below (see docs/ARCHITECTURE.md §4) — it's what's still correct if two
    receptionists submit this at the same moment.
    """
    if not procedures:
        raise ValidationError("At least one procedure is required.")
    _validate_room_type(chair, procedures)

    duration_minutes = sum(p.default_duration_minutes for p in procedures)
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    if buffer_minutes is None:
        buffer_minutes = chair.default_buffer_minutes

    appointment = Appointment(
        branch=branch, patient=patient, doctor=doctor, chair=chair,
        treatment_plan=treatment_plan, start_time=start_time, end_time=end_time,
        buffer_minutes=buffer_minutes, booking_type=booking_type, notes=notes, created_by=created_by,
    )
    try:
        appointment.save()
    except IntegrityError as exc:
        raise ValidationError(_friendly_conflict_message(exc)) from exc

    AppointmentProcedure.objects.bulk_create([
        AppointmentProcedure(appointment=appointment, procedure=p) for p in procedures
    ])
    return appointment


@transaction.atomic
def reschedule_appointment(*, appointment, chair=None, doctor=None, start_time=None, buffer_minutes=None):
    """Move an existing appointment to a new chair/doctor/time, keeping its
    original duration unless the caller also changes the procedures
    separately. Emergency insertion uses this same path: find (or clear) a
    genuinely free slot first — the exclusion constraints mean an
    appointment can never truly overlap another, emergency or not."""
    if appointment.status in NOT_RESCHEDULABLE:
        raise ValidationError(f"Cannot reschedule an appointment that is already {appointment.status}.")

    duration = appointment.end_time - appointment.start_time
    if chair is not None:
        appointment.chair = chair
    if doctor is not None:
        appointment.doctor = doctor
    if start_time is not None:
        appointment.start_time = start_time
        appointment.end_time = start_time + duration
    if buffer_minutes is not None:
        appointment.buffer_minutes = buffer_minutes

    procedures = [ap.procedure for ap in appointment.appointment_procedures.select_related("procedure")]
    _validate_room_type(appointment.chair, procedures)

    try:
        appointment.save()
    except IntegrityError as exc:
        raise ValidationError(_friendly_conflict_message(exc)) from exc
    return appointment


def cancel_appointment(*, appointment, reason, cancelled_by):
    if appointment.status in (Appointment.CANCELLED, Appointment.COMPLETED):
        raise ValidationError(f"Appointment is already {appointment.status}.")
    if not reason:
        raise ValidationError("A cancellation reason is required.")
    appointment.status = Appointment.CANCELLED
    appointment.cancelled_reason = reason
    appointment.cancelled_by = cancelled_by
    appointment.cancelled_at = timezone.now()
    appointment.save(update_fields=["status", "cancelled_reason", "cancelled_by", "cancelled_at"])
    return appointment


def check_in(*, appointment):
    if appointment.status != Appointment.SCHEDULED:
        raise ValidationError("Only a scheduled appointment can be checked in.")
    appointment.status = Appointment.CHECKED_IN
    appointment.save(update_fields=["status"])
    return appointment


def start_appointment(*, appointment):
    if appointment.status != Appointment.CHECKED_IN:
        raise ValidationError("Only a checked-in appointment can be started.")
    appointment.status = Appointment.IN_PROGRESS
    appointment.save(update_fields=["status"])
    return appointment


def complete_appointment(*, appointment):
    if appointment.status not in (Appointment.IN_PROGRESS, Appointment.CHECKED_IN):
        raise ValidationError("Only a checked-in or in-progress appointment can be completed.")
    appointment.status = Appointment.COMPLETED
    appointment.save(update_fields=["status"])
    return appointment


def mark_no_show(*, appointment):
    if appointment.status not in (Appointment.SCHEDULED, Appointment.CHECKED_IN):
        raise ValidationError("Only a scheduled or checked-in appointment can be marked no-show.")
    appointment.status = Appointment.NO_SHOW
    appointment.save(update_fields=["status"])
    return appointment
