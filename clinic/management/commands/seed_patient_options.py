from django.core.management.base import BaseCommand

from clinic.models import MedicalHistoryCondition, PatientTitle, ReferralSource

TITLES = ["Dr.", "Mr.", "Mrs.", "Miss", "Master", "Baby"]

REFERRAL_SOURCES = [
    "News print",
    "AI (ChatGPT, Gemini, etc.)",
    "Clinic website",
    "Social media",
    "Google",
    "Building signage",
    "Camp",
    "Reference / other",
]

CORPORATE_REFERRALS = ["SHAR", "TVS", "WABCO"]

MEDICAL_HISTORY_CONDITIONS = [
    ("Respiratory", "Asthma\nTB"),
    ("Blood disorders", "Anaemia\nTransfusions\nBleeding issues"),
    ("Endocrine", "Diabetes\nThyroid"),
    ("Allergies", "Medicines\nMetals\nOthers"),
    ("Tobacco / smoking use", ""),
    ("Neurological / psychiatric", "Stroke\nEpilepsy\nMental health"),
    ("Kidney disease", ""),
    ("Digestive / liver", "Jaundice\nHepatitis\nAcid reflux"),
    (
        "Heart conditions",
        "BP\nHeart attack\nAngioplasty\nRheumatic heart disease\n"
        "CABG\nArtificial heart valve\nCongenital heart disease\nPacemaker",
    ),
]


class Command(BaseCommand):
    help = (
        "Seed the default patient-registration options (titles, referral sources, "
        "medical-history checklist) — idempotent. Add more later from Django Admin, "
        "not by re-running this."
    )

    def handle(self, *args, **options):
        for i, name in enumerate(TITLES):
            _, created = PatientTitle.objects.get_or_create(name=name, defaults={"sort_order": i})
            self.stdout.write(f"Title {name}: {'created' if created else 'already exists'}")

        for i, name in enumerate(REFERRAL_SOURCES):
            _, created = ReferralSource.objects.get_or_create(
                name=name, defaults={"sort_order": i, "is_corporate": False}
            )
            self.stdout.write(f"Referral source {name}: {'created' if created else 'already exists'}")

        for i, name in enumerate(CORPORATE_REFERRALS):
            _, created = ReferralSource.objects.get_or_create(
                name=name, defaults={"sort_order": i, "is_corporate": True}
            )
            self.stdout.write(f"Corporate referral {name}: {'created' if created else 'already exists'}")

        for i, (name, sub_items) in enumerate(MEDICAL_HISTORY_CONDITIONS):
            _, created = MedicalHistoryCondition.objects.get_or_create(
                name=name, defaults={"sort_order": i, "sub_items": sub_items}
            )
            self.stdout.write(f"Medical history condition {name}: {'created' if created else 'already exists'}")
