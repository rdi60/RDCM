"""Shared option-list builders for the admin-managed patient lookups
(PatientTitle, ReferralSource). Used by both the staff registration form
(scheduling.forms.PatientForm) and the patient self-registration form
(scheduling.forms.SelfRegistrationForm) so the two stay in sync without
duplicating the query logic."""

from .models import PatientTitle, ReferralSource


def title_choices():
    return [("", "--")] + [(t.name, t.name) for t in PatientTitle.objects.filter(is_active=True)]


def referral_choices():
    return [("", "--")] + [
        (r.name, r.name) for r in ReferralSource.objects.filter(is_active=True, is_corporate=False)
    ]


def corporate_referral_choices():
    return [("", "None")] + [
        (r.name, r.name) for r in ReferralSource.objects.filter(is_active=True, is_corporate=True)
    ]
