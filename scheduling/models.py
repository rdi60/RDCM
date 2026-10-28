from datetime import datetime, time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clinic.models import Doctor, DrugAllergySymptom, MedicalHistoryCondition, Resource, Treatment
from core.fields import EncryptedTextField


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    uhid = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    # Title, referral source and corporate referral used to be hardcoded
    # choices here. They're now plain text fed from admin-managed lookup
    # tables (clinic.PatientTitle, clinic.ReferralSource) so staff can add
    # a new option without a code change — see PatientForm.__init__.
    title = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age_years = models.PositiveIntegerField(
        null=True, blank=True, help_text="Only if the exact date of birth isn't known"
    )
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    nationality = models.CharField(max_length=50, blank=True, default="Indian")

    address = models.TextField(blank=True)
    area = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    pin_code = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(
        max_length=150, blank=True, help_text="Name and phone number"
    )

    chief_complaint = EncryptedTextField(blank=True, help_text="Reason for this visit")
    has_dental_fear = models.BooleanField(default=False)

    referral_source = models.CharField(max_length=100, blank=True)
    referral_detail = models.CharField(
        max_length=150, blank=True, help_text="Who referred them, if 'Reference / other'"
    )
    corporate_referral = models.CharField(max_length=100, blank=True)

    current_medications = EncryptedTextField(blank=True)

    medical_history = EncryptedTextField(
        blank=True, help_text="Anything else not covered by the checklist above"
    )

    has_drug_allergy = models.BooleanField(default=False)
    drug_allergy_detail = EncryptedTextField(blank=True, help_text="Which drug(s) they're allergic to")

    consent_given = models.BooleanField(
        default=False, help_text="Patient confirmed the information above is accurate"
    )
    consent_date = models.DateField(null=True, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.uhid})" if self.uhid else self.full_name

    @property
    def flagged_medical_history(self):
        """Human-readable labels for every medical-history checklist item
        ticked 'yes', with whichever sub-items were specified — used on the
        patient detail page so staff see a short flagged list instead of a
        full condition-by-condition table."""
        labels = []
        for entry in self.medical_conditions.select_related("condition"):
            if entry.sub_items:
                labels.append(f"{entry.condition.name} ({entry.sub_items})")
            else:
                labels.append(entry.condition.name)
        return labels

    @property
    def drug_allergy_symptom_list(self):
        return [entry.symptom.name for entry in self.drug_allergy_symptoms.select_related("symptom")]

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.uhid:
            self.uhid = f"RD-{self.pk:05d}"
            super().save(update_fields=["uhid"])


class PatientMedicalCondition(models.Model):
    """One ticked medical-history checklist item for a patient. A separate
    table (rather than one boolean column per condition on Patient) so new
    conditions can be added via Django Admin (clinic.MedicalHistoryCondition)
    without a schema migration."""

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medical_conditions")
    condition = models.ForeignKey(MedicalHistoryCondition, on_delete=models.PROTECT, related_name="+")
    sub_items = models.CharField(
        max_length=255, blank=True, help_text="Which sub-items were ticked, comma-separated"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["patient", "condition"], name="unique_patient_condition")
        ]
        ordering = ["condition__sort_order"]

    def __str__(self):
        return f"{self.patient} - {self.condition}"


class PatientDrugAllergySymptom(models.Model):
    """One ticked symptom on a patient's drug-allergy checklist. Same
    join-table pattern as PatientMedicalCondition, so new symptoms can be
    added via Django Admin (clinic.DrugAllergySymptom) without a migration."""

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="drug_allergy_symptoms"
    )
    symptom = models.ForeignKey(DrugAllergySymptom, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["patient", "symptom"], name="unique_patient_drug_allergy_symptom")
        ]
        ordering = ["symptom__sort_order"]

    def __str__(self):
        return f"{self.patient} - {self.symptom}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        ARRIVED = "arrived", "Arrived"
        IN_CHAIR = "in_chair", "In chair"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    # What status a booking may move to next, enforced server-side in the
    # appointment_set_status view (not just hidden/shown in the template).
    NEXT_STATUSES = {
        Status.SCHEDULED: [Status.CONFIRMED, Status.ARRIVED, Status.CANCELLED],
        Status.CONFIRMED: [Status.ARRIVED, Status.CANCELLED],
        Status.ARRIVED: [Status.IN_CHAIR, Status.NO_SHOW, Status.CANCELLED],
        Status.IN_CHAIR: [Status.COMPLETED],
        Status.COMPLETED: [],
        Status.CANCELLED: [],
        Status.NO_SHOW: [],
    }

    # Statuses that still hold the resource/doctor — used for overlap checks.
    BLOCKING_STATUSES = [
        Status.SCHEDULED,
        Status.CONFIRMED,
        Status.ARRIVED,
        Status.IN_CHAIR,
        Status.COMPLETED,
    ]

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="appointments")
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="appointments")
    treatment = models.ForeignKey(
        Treatment, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointments"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    token_number = models.PositiveIntegerField(null=True, blank=True, editable=False)
    follow_up_date = models.DateField(
        null=True, blank=True, help_text="When this patient should be recalled, if at all."
    )
    notes = EncryptedTextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.patient} with {self.doctor} @ {timezone.localtime(self.start_time):%Y-%m-%d %H:%M}"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")
        if self.start_time and self.end_time and self.resource_id and self.doctor_id:
            conflict = self.conflicting_appointments().first()
            if conflict:
                raise ValidationError(
                    f"Conflicts with {conflict.patient.full_name}'s appointment on "
                    f"{conflict.resource} with {conflict.doctor} at "
                    f"{timezone.localtime(conflict.start_time):%H:%M}–"
                    f"{timezone.localtime(conflict.end_time):%H:%M}."
                )

    def conflicting_appointments(self):
        qs = Appointment.objects.filter(
            models.Q(resource=self.resource) | models.Q(doctor=self.doctor)
        ).filter(status__in=self.BLOCKING_STATUSES)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.filter(start_time__lt=self.end_time, end_time__gt=self.start_time)

    def save(self, *args, **kwargs):
        if self._state.adding and self.token_number is None:
            self.token_number = self._next_token_number()
        super().save(*args, **kwargs)

    def _next_token_number(self):
        local_date = timezone.localtime(self.start_time).date()
        day_start = timezone.make_aware(datetime.combine(local_date, time.min))
        day_end = timezone.make_aware(datetime.combine(local_date, time.max))
        last = (
            Appointment.objects.filter(start_time__gte=day_start, start_time__lte=day_end)
            .exclude(token_number=None)
            .order_by("-token_number")
            .first()
        )
        return (last.token_number if last else 0) + 1
