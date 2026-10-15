from django import forms

from clinic.models import Doctor, Resource, Treatment

from .models import Appointment, Patient

# HTML5 datetime-local inputs require this exact format; Django's own
# default DATETIME_INPUT_FORMATS use a space instead of "T" and include
# seconds, so without this a browser renders the field blank and a
# submitted value fails to parse.
DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


MEDICAL_HISTORY_FIELDS = [
    "mh_respiratory",
    "mh_endocrine",
    "mh_tobacco_use",
    "mh_kidney_disease",
    "mh_heart_conditions",
    "mh_blood_disorders",
    "mh_allergies",
    "mh_neuro_psychiatric",
    "mh_digestive_liver",
]


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "title",
            "full_name",
            "date_of_birth",
            "age_years",
            "gender",
            "nationality",
            "phone",
            "email",
            "address",
            "area",
            "city",
            "pin_code",
            "emergency_contact",
            "chief_complaint",
            "has_dental_fear",
            "referral_source",
            "referral_detail",
            "corporate_referral",
            *MEDICAL_HISTORY_FIELDS,
            "current_medications",
            "medical_history",
            "consent_given",
            "consent_date",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "chief_complaint": forms.Textarea(attrs={"rows": 2}),
            "current_medications": forms.Textarea(attrs={"rows": 2}),
            "medical_history": forms.Textarea(attrs={"rows": 3}),
            "consent_date": forms.DateInput(attrs={"type": "date"}),
        }


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["patient", "doctor", "resource", "treatment", "start_time", "end_time", "notes"]
        widgets = {
            "start_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format=DATETIME_LOCAL_FORMAT
            ),
            "end_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format=DATETIME_LOCAL_FORMAT
            ),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = Doctor.objects.filter(is_active=True)
        self.fields["resource"].queryset = Resource.objects.filter(status=Resource.Status.ACTIVE)
        self.fields["treatment"].queryset = Treatment.objects.filter(is_active=True)
        self.fields["treatment"].required = False
        self.fields["start_time"].input_formats = [DATETIME_LOCAL_FORMAT]
        self.fields["end_time"].input_formats = [DATETIME_LOCAL_FORMAT]
