from django import forms

from clinic.choices import corporate_referral_choices, referral_choices, title_choices
from clinic.models import Doctor, Resource, Treatment

from .models import Appointment, Patient, SelfRegistration

# HTML5 datetime-local inputs require this exact format; Django's own
# default DATETIME_INPUT_FORMATS use a space instead of "T" and include
# seconds, so without this a browser renders the field blank and a
# submitted value fails to parse.
DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"

COUNTRY_CODES = [
    ("+91", "+91 India"),
    ("+1", "+1 US/Canada"),
    ("+44", "+44 UK"),
    ("+61", "+61 Australia"),
    ("+65", "+65 Singapore"),
    ("+971", "+971 UAE"),
    ("+974", "+974 Qatar"),
    ("+966", "+966 Saudi Arabia"),
]


def _yes_no_field(label, widget_attrs=None):
    """A Yes/No TypedChoiceField coerced to a real bool, used wherever a
    plain BooleanField needs to look like a Yes/No pick on the paper form
    rather than a single checkbox (has_dental_fear, has_drug_allergy) —
    shared by PatientForm and SelfRegistrationForm."""
    return forms.TypedChoiceField(
        choices=[(False, "No"), (True, "Yes")],
        coerce=lambda v: str(v) == "True",
        widget=forms.RadioSelect(attrs=widget_attrs or {}),
        required=False,
        initial=False,
        label=label,
    )


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
            "current_medications",
            "medical_history",
            "has_drug_allergy",
            "drug_allergy_detail",
            "consent_given",
            "consent_date",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "chief_complaint": forms.Textarea(attrs={"rows": 2}),
            "current_medications": forms.Textarea(attrs={"rows": 2}),
            "medical_history": forms.Textarea(attrs={"rows": 3}),
            "drug_allergy_detail": forms.TextInput(attrs={"placeholder": "Enter drug allergy"}),
            "consent_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Title, referral source and corporate referral are admin-managed
        # lookup tables (clinic app) rather than hardcoded choices, so staff
        # can add a new option from Django Admin without a code change.
        # The model fields themselves are plain CharFields; these overrides
        # are what turn them into dropdowns sourced from those tables.
        self.fields["title"] = forms.ChoiceField(choices=title_choices(), required=False, label="Title")
        self.fields["referral_source"] = forms.ChoiceField(
            choices=referral_choices(), required=False, label="How did you hear about us?"
        )
        self.fields["corporate_referral"] = forms.ChoiceField(
            choices=corporate_referral_choices(), required=False, label="Corporate referral"
        )
        # Yes/No toggle rather than a plain checkbox, to match the paper
        # form; which drug(s) and which symptoms are only relevant once
        # "Yes" is picked, so they stay template-side next to this field.
        self.fields["has_drug_allergy"] = _yes_no_field(
            "Do you have drug allergies?", {"class": "radio-list"}
        )


class SelfRegistrationForm(forms.ModelForm):
    """The public, no-login kiosk/phone form a patient fills in themselves
    when enrolling (with staff-assisted fallback for elderly patients) —
    see scheduling.views.self_register. Saves to SelfRegistration, a
    staging record, not directly to Patient; front-desk staff review and
    approve it into a real Patient (scheduling.views.self_registration_review)."""

    country_code = forms.ChoiceField(
        choices=COUNTRY_CODES, required=False, initial="+91", label="Country code"
    )

    class Meta:
        model = SelfRegistration
        fields = [
            "title",
            "full_name",
            "date_of_birth",
            "age_years",
            "gender",
            "nationality",
            "phone",
            "email",
            "emergency_contact",
            "address",
            "area",
            "city",
            "pin_code",
            "chief_complaint",
            "has_dental_fear",
            "referral_source",
            "referral_detail",
            "corporate_referral",
            "current_medications",
            "medical_history",
            "has_drug_allergy",
            "drug_allergy_detail",
            "consent_given",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "full_name": forms.TextInput(attrs={"placeholder": "As per ID"}),
            "phone": forms.TextInput(attrs={"type": "tel", "placeholder": "Phone number"}),
            "email": forms.EmailInput(attrs={"placeholder": "optional"}),
            "emergency_contact": forms.TextInput(attrs={"placeholder": "Name and phone number"}),
            "address": forms.Textarea(attrs={"rows": 2, "placeholder": "House / street"}),
            "chief_complaint": forms.Textarea(attrs={"rows": 2, "placeholder": "What brings you in today?"}),
            "current_medications": forms.Textarea(attrs={"rows": 2, "placeholder": "If applicable"}),
            "medical_history": forms.Textarea(attrs={"rows": 3, "placeholder": "Anything else we should know"}),
            "drug_allergy_detail": forms.TextInput(attrs={"placeholder": "Enter drug allergy"}),
            "referral_detail": forms.TextInput(attrs={"placeholder": "Optional"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"] = forms.ChoiceField(choices=title_choices(), required=False, label="Title")
        # Referral and gender are tappable chip rows on this form (unlike
        # the staff form's dropdowns), so they need RadioSelect here
        # specifically — and with no blank option, since a blank choice's
        # "" value otherwise matches the model field's own blank default
        # and renders as a meaningless pre-selected chip.
        self.fields["referral_source"] = forms.ChoiceField(
            choices=referral_choices()[1:],
            required=False,
            label="How did you hear about us?",
            widget=forms.RadioSelect,
        )
        self.fields["gender"] = forms.ChoiceField(
            choices=Patient.Gender.choices, required=False, widget=forms.RadioSelect, label="Gender"
        )
        self.fields["corporate_referral"] = forms.ChoiceField(
            choices=corporate_referral_choices(), required=False, label="Corporate referral"
        )
        self.fields["has_dental_fear"] = _yes_no_field('Dental "fear" or "phobia"?')
        self.fields["has_drug_allergy"] = _yes_no_field("Do you have drug allergies?")
        self.fields["consent_given"].required = True
        self.fields["phone"].label = "Phone number"

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("country_code") or "+91"
        phone = (cleaned.get("phone") or "").strip()
        # Keep bare domestic numbers exactly as staff-entered patients look
        # (no "+91" prefix clutter); only prefix when it's not the default,
        # so international patients' numbers stay unambiguous.
        if phone and code != "+91":
            cleaned["phone"] = f"{code} {phone}"
        return cleaned


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
