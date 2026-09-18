import datetime
import uuid

from django.conf import settings
from django.db import models

from apps.clinic.models import Branch, Chair
from apps.doctors.models import Assistant, Doctor
from apps.patients.models import Patient
from apps.procedures.models import Procedure


class TreatmentPlan(models.Model):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    STATUS_CHOICES = [(ACTIVE, "Active"), (COMPLETED, "Completed"), (ABANDONED, "Abandoned")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="treatment_plans")
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="treatment_plans")
    title = models.CharField(max_length=300, help_text="e.g. 'RCT - tooth 36'")
    planned_sittings = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "treatment_plans"

    def __str__(self):
        return f"{self.title} ({self.patient.uhid})"


class Appointment(models.Model):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    STATUS_CHOICES = [
        (SCHEDULED, "Scheduled"), (CHECKED_IN, "Checked in"), (IN_PROGRESS, "In progress"),
        (COMPLETED, "Completed"), (CANCELLED, "Cancelled"), (NO_SHOW, "No-show"),
    ]
    INACTIVE_STATUSES = [CANCELLED, NO_SHOW]

    REGULAR = "regular"
    WALK_IN = "walk_in"
    EMERGENCY = "emergency"
    BOOKING_TYPE_CHOICES = [(REGULAR, "Regular"), (WALK_IN, "Walk-in"), (EMERGENCY, "Emergency")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="appointments")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="appointments")
    chair = models.ForeignKey(Chair, on_delete=models.PROTECT, related_name="appointments")
    treatment_plan = models.ForeignKey(
        TreatmentPlan, on_delete=models.PROTECT, null=True, blank=True, related_name="visits",
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    buffer_minutes = models.PositiveIntegerField(default=10)
    # Kept in sync in Python (see save(), below) so Django's own writes are
    # always correct; a BEFORE INSERT/UPDATE trigger (migration 0002,
    # validated in db/schema.sql) recomputes it again in the database, so
    # it's still correct even for a write that bypasses Django entirely.
    # It has to be a plain column, not a Postgres GENERATED column: adding
    # an interval to a timestamptz is timezone-dependent (STABLE), and
    # Postgres requires GENERATED expressions to be IMMUTABLE.
    blocked_until = models.DateTimeField(editable=False)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=SCHEDULED)
    booking_type = models.CharField(max_length=16, choices=BOOKING_TYPE_CHOICES, default=REGULAR)

    notes = models.TextField(blank=True)
    cancelled_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "appointments"
        constraints = [
            models.CheckConstraint(check=models.Q(end_time__gt=models.F("start_time")), name="ck_appointment_time_order"),
            # The actual double-booking guarantee (chair + doctor exclusion
            # constraints) is added in migration 0002 via raw SQL, because
            # it needs tstzrange()/GiST, which predates reliable ORM-level
            # support for this exact shape. See db/schema.sql §6 for the
            # hand-validated SQL this mirrors, and ARCHITECTURE.md §4.
        ]
        indexes = [
            models.Index(fields=["branch", "start_time"], name="idx_appt_branch_start"),
            models.Index(fields=["doctor", "start_time"], name="idx_appt_doctor_start"),
            models.Index(fields=["chair", "start_time"], name="idx_appt_chair_start"),
        ]

    def save(self, *args, **kwargs):
        self.blocked_until = self.end_time + datetime.timedelta(minutes=self.buffer_minutes)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient.uhid} @ {self.start_time:%Y-%m-%d %H:%M} ({self.chair.code})"


class AppointmentProcedure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="appointment_procedures")
    procedure = models.ForeignKey(Procedure, on_delete=models.PROTECT, related_name="+")
    tooth_numbers = models.JSONField(default=list, blank=True, help_text="FDI notation, e.g. ['36']")

    class Meta:
        db_table = "appointment_procedures"


class AppointmentAssistant(models.Model):
    """Optional third resource — empty today by design (see
    apps.doctors.models.Assistant); not enforced against overlap yet."""

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="assistant_links")
    assistant = models.ForeignKey(Assistant, on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "appointment_assistants"
        constraints = [
            models.UniqueConstraint(fields=["appointment", "assistant"], name="uq_appointment_assistant"),
        ]
