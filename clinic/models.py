from django.conf import settings
from django.db import models


class Specialty(models.Model):
    """A dental specialty a doctor can practice (Orthodontics, Endodontics, ...)."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Specialties"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Doctor(models.Model):
    """
    A doctor enrolled at the clinic. Deliberately not the same thing as a
    login account: a doctor can be enrolled (for scheduling, billing,
    reports) before anyone creates them a User, and a User is created
    separately (Django Admin) with a role group when they need to log in.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctor_profile",
        help_text="Link to a login account, once one exists for this doctor.",
    )
    full_name = models.CharField(max_length=150)
    registration_number = models.CharField(
        max_length=50, blank=True, help_text="Dental Council registration number."
    )
    specialties = models.ManyToManyField(Specialty, blank=True, related_name="doctors")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class DoctorQualification(models.Model):
    """One degree/qualification of a doctor's — a doctor can have several."""

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="qualifications")
    degree = models.CharField(max_length=100, help_text="e.g. BDS, MDS - Orthodontics")
    institution = models.CharField(max_length=200, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["year", "degree"]

    def __str__(self):
        return self.degree


class Resource(models.Model):
    """A bookable clinical resource: a dental chair or an operation theatre."""

    class ResourceType(models.TextChoices):
        CHAIR = "chair", "Chair"
        OT = "ot", "OT"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        MAINTENANCE = "maintenance", "Under maintenance"

    type = models.CharField(max_length=10, choices=ResourceType.choices)
    name = models.CharField(max_length=50, help_text="e.g. Chair 1, OT 2")
    number = models.PositiveIntegerField(
        default=0, help_text="Used only to sort resources in order (1, 2, 3, ...) instead of alphabetically."
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["type", "number", "name"]
        constraints = [
            models.UniqueConstraint(fields=["type", "name"], name="unique_resource_type_name")
        ]

    def __str__(self):
        return self.name


class Treatment(models.Model):
    """A treatment/procedure offered, with its default price and duration."""

    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=100, blank=True)
    default_duration_minutes = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class PatientTitle(models.Model):
    """An honorific option on the patient registration form (Dr., Mr., ...).
    A plain lookup table rather than a hardcoded choices list, so staff can
    add a new one from Django Admin without a code change or redeploy."""

    name = models.CharField(max_length=20, unique=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ReferralSource(models.Model):
    """A 'how did you hear about us?' option on patient registration.
    Corporate referral partners (SHAR, TVS, ...) use the same table, flagged
    by `is_corporate`, so both lists are managed in one place."""

    name = models.CharField(max_length=100, unique=True)
    is_corporate = models.BooleanField(
        default=False, help_text="Shown in the separate 'Corporate referral' list instead."
    )
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class MedicalHistoryCondition(models.Model):
    """One item on the patient intake medical-history checklist. `sub_items`
    holds the bracketed examples from the paper form (e.g. "Asthma" /
    "TB") — one per line — shown as their own tickable options once this
    condition is checked. Leave blank for a condition with no sub-items
    (e.g. "Tobacco / smoking use")."""

    name = models.CharField(max_length=100, unique=True)
    sub_items = models.TextField(
        blank=True, help_text="One sub-item per line, e.g. Asthma (new line) TB. Leave blank for none."
    )
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def sub_item_list(self):
        return [line.strip() for line in self.sub_items.splitlines() if line.strip()]


class DrugAllergySymptom(models.Model):
    """One tickable symptom on the drug-allergy checklist (Skin Rashes,
    Swelling, ...), shown when a patient answers 'yes' to having a drug
    allergy. Admin-managed like the other patient-registration lookups, so
    new symptoms can be added without a code change."""

    name = models.CharField(max_length=100, unique=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
