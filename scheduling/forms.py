from django import forms

from clinic.models import Doctor, Resource, Treatment

from .models import Appointment, Patient

# HTML5 datetime-local inputs require this exact format; Django's own
# default DATETIME_INPUT_FORMATS use a space instead of "T" and include
# seconds, so without this a browser renders the field blank and a
# submitted value fails to parse.
DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "full_name",
            "phone",
            "email",
            "date_of_birth",
            "gender",
            "address",
            "medical_history",
            "referral_source",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "medical_history": forms.Textarea(attrs={"rows": 3}),
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
