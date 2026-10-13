from django.contrib.auth.decorators import login_required
from django.shortcuts import render

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


@login_required
def home(request):
    return render(request, "core/home.html", {"modules": MODULES})
