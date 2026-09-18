import uuid

from django.conf import settings
from django.db import models

from apps.clinic.models import Branch


class Doctor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="doctor_profile")
    registration_no = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "doctors"

    def __str__(self):
        return self.user.name


class DoctorAvailability(models.Model):
    """Recurring weekly availability, e.g. Mon/Wed/Fri 10:00-14:00 at Branch
    A. One-off overrides (leave, an extra day) live in
    DoctorScheduleException, layered on top when checking bookability."""

    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)
    DAY_CHOICES = [
        (SUNDAY, "Sunday"), (MONDAY, "Monday"), (TUESDAY, "Tuesday"), (WEDNESDAY, "Wednesday"),
        (THURSDAY, "Thursday"), (FRIDAY, "Friday"), (SATURDAY, "Saturday"),
    ]
    # 0=Sunday, matching Postgres EXTRACT(DOW FROM ...) and schema.sql.

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="availability")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="doctor_availability")
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True, help_text="NULL = still in effect")

    class Meta:
        db_table = "doctor_availability"
        constraints = [
            models.CheckConstraint(check=models.Q(day_of_week__gte=0) & models.Q(day_of_week__lte=6), name="ck_availability_dow"),
            models.CheckConstraint(check=models.Q(end_time__gt=models.F("start_time")), name="ck_availability_time_order"),
        ]


class DoctorScheduleException(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="schedule_exceptions")
    date = models.DateField()
    is_available = models.BooleanField(help_text="False = on leave that day")
    start_time = models.TimeField(null=True, blank=True, help_text="NULL if unavailable all day")
    end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "doctor_schedule_exceptions"
        constraints = [
            models.UniqueConstraint(fields=["doctor", "date"], name="uq_doctor_exception_date"),
        ]


class Assistant(models.Model):
    """Optional third booking resource (see docs/ARCHITECTURE.md). Not yet
    wired into the booking flow — appointment_assistants exists specifically
    so it can be turned on without restructuring."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assistant_profile")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "assistants"

    def __str__(self):
        return self.user.name
