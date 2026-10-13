from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

# Modules land here phase by phase (see the project roadmap). Marking a module
# available=True and setting its url is literally all a later phase needs
# to do to "turn it on" in the nav — this view doesn't otherwise change.
MODULES = [
    {"name": "Appointments", "phase": "Phase 2", "available": False},
    {"name": "Patients", "phase": "Phase 2", "available": False},
    {"name": "Billing", "phase": "Phase 4", "available": False},
    {"name": "Inventory", "phase": "Phase 5", "available": False},
    {"name": "MIS Reports", "phase": "Phase 6", "available": False},
]

# Phase 1 master data is managed through Django Admin rather than custom
# screens (see the roadmap's "admin core" decision); these are just
# shortcuts into that admin so staff don't have to know the URLs.
SETUP_LINKS = [
    ("Doctors", "admin:clinic_doctor_changelist"),
    ("Specialties", "admin:clinic_specialty_changelist"),
    ("Chairs & OTs", "admin:clinic_resource_changelist"),
    ("Treatments", "admin:clinic_treatment_changelist"),
    ("Users & roles", "admin:accounts_user_changelist"),
]


@login_required
def home(request):
    setup_links = None
    if request.user.is_staff:
        setup_links = [(label, reverse(name)) for label, name in SETUP_LINKS]
    return render(request, "core/home.html", {"modules": MODULES, "setup_links": setup_links})
