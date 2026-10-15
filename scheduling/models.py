from datetime import datetime, time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clinic.models import Doctor, Resource, Treatment
from core.fields import EncryptedTextField


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    class Title(models.TextChoices):
        DR = "Dr.", "Dr."
        MR = "Mr.", "Mr."
        MRS = "Mrs.", "Mrs."
        MISS = "Miss", "Miss"
        MASTER = "Master", "Master"
        BABY = "Baby", "Baby"

    class ReferralSource(models.TextChoices):
        NEWSPRINT = "newsprint", "News print"
        AI = "ai", "AI (ChatGPT, Gemini, etc.)"
        WEBSITE = "website", "Clinic website"
        SOCIAL_MEDIA = "social_media", "Social media"
        GOOGLE = "google", "Google"
        SIGNAGE = "signage", "Building signage"
        CAMP = "camp", "Camp"
        REFERENCE_OTHER = "reference_other", "Reference / other"

    class CorporateReferral(models.TextChoices):
        SHAR = "SHAR", "SHAR"
        TVS = "TVS", "TVS"
        WABCO = "WABCO", "WABCO"

    uhid = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    title = models.CharField(max_length=10, choices=Title.choices, blank=True)
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

    referral_source = models.CharField(max_length=20, choices=ReferralSource.choices, blank=True)
    referral_detail = models.CharField(
        max_length=150, blank=True, help_text="Who referred them, if 'Reference / other'"
    )
    corporate_referral = models.CharField(
        max_length=10, choices=CorporateReferral.choices, blank=True
    )

    # Medical history checklist, one yes/no per item on the intake form —
    # kept as individual fields (rather than folded into medical_history)
    # so staff can filter/flag by condition, e.g. before a procedure.
    mh_respiratory = models.BooleanField(default=False, help_text="Asthma, TB")
    mh_endocrine = models.BooleanField(default=False, help_text="Diabetes, thyroid")
    mh_tobacco_use = models.BooleanField(default=False, help_text="Tobacco / smoking use")
    mh_kidney_disease = models.BooleanField(default=False)
    mh_heart_conditions = models.BooleanField(
        default=False,
        help_text=(
            "BP, heart attack, angioplasty, rheumatic heart disease, CABG, "
            "artificial heart valve, congenital heart disease, pacemaker"
        ),
    )
    mh_blood_disorders = models.BooleanField(
        default=False, help_text="Anaemia, transfusions, bleeding issues"
    )
    mh_allergies = models.BooleanField(default=False, help_text="Medicines, metals, others")
    mh_neuro_psychiatric = models.BooleanField(
        default=False, help_text="Stroke, epilepsy, mental health"
    )
    mh_digestive_liver = models.BooleanField(
        default=False, help_text="Jaundice, hepatitis, acid reflux"
    )
    current_medications = EncryptedTextField(blank=True)

    medical_history = EncryptedTextField(
        blank=True, help_text="Anything else not covered by the checklist above"
    )

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

    MEDICAL_HISTORY_LABELS = {
        "mh_respiratory": "Respiratory (Asthma, TB)",
        "mh_endocrine": "Endocrine (Diabetes, thyroid)",
        "mh_tobacco_use": "Tobacco / smoking use",
        "mh_kidney_disease": "Kidney disease",
        "mh_heart_conditions": "Heart conditions",
        "mh_blood_disorders": "Blood disorders",
        "mh_allergies": "Allergies",
        "mh_neuro_psychiatric": "Neurological / psychiatric",
        "mh_digestive_liver": "Digestive / liver",
    }

    def __str__(self):
        return f"{self.full_name} ({self.uhid})" if self.uhid else self.full_name

    @property
    def flagged_medical_history(self):
        """Human-readable labels for every medical-history checklist item
        ticked 'yes' — used on the patient detail page so staff see a short
        flagged list instead of nine yes/no rows."""
        return [label for field, label in self.MEDICAL_HISTORY_LABELS.items() if getattr(self, field)]

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.uhid:
            self.uhid = f"RD-{self.pk:05d}"
            super().save(update_fields=["uhid"])


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
