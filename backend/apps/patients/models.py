import uuid

from django.conf import settings
from django.db import models

from apps.clinic.models import Branch


class Patient(models.Model):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    GENDER_CHOICES = [(MALE, "Male"), (FEMALE, "Female"), (OTHER, "Other")]

    ACTIVE = "active"
    MERGED = "merged"
    STATUS_CHOICES = [(ACTIVE, "Active"), (MERGED, "Merged")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uhid = models.CharField(max_length=32, unique=True, help_text="Clinic-facing patient number, sequential per branch")
    registered_at_branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT, null=True, blank=True, related_name="patients_registered",
    )
    name = models.CharField(max_length=200)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    referred_by = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Duplicate-registration handling — see patients.services.merge_patients
    # and docs/ARCHITECTURE.md §8. A duplicate is merged, never deleted.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    merged_into = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="absorbed_duplicates",
    )

    class Meta:
        db_table = "patients"
        constraints = [
            models.CheckConstraint(
                check=models.Q(status="active") | models.Q(merged_into__isnull=False),
                name="ck_patient_merged_has_target",
            ),
        ]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.uhid} - {self.name}"


class PatientMerge(models.Model):
    """Audit record of a duplicate-patient merge. See
    patients.services.merge_patients — this is inserted in the same
    transaction that repoints the source patient's appointments/bills/etc.
    to the target and tombstones the source."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="merge_as_source")
    target_patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="merge_as_target")
    reason = models.TextField()
    merged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    merged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patient_merges"
        constraints = [
            models.CheckConstraint(
                check=~models.Q(source_patient=models.F("target_patient")), name="ck_merge_source_ne_target",
            ),
        ]
