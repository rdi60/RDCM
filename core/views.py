from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

# Modules land here phase by phase (see the project roadmap). Marking a module
# available=True and setting its url is literally all a later phase needs
# to do to "turn it on" in the nav — this view doesn't otherwise change.
MODULES = [
    {"name": "Appointments", "phase": "Phase 2", "available": True, "url_name": "calendar"},
    {"name": "Patients", "phase": "Phase 2", "available": True, "url_name": "patient_list"},
    {"name": "Billing", "phase": "Phase 4", "available": True, "url_name": "invoice_list"},
    {"name": "Inventory", "phase": "Phase 5", "available": True, "url_name": "stock_levels"},
    {"name": "MIS Reports", "phase": "Phase 6", "available": True, "url_name": "reports_hub"},
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
    ("Suppliers", "admin:inventory_supplier_changelist"),
    ("Items", "admin:inventory_item_changelist"),
    ("Stock locations", "admin:inventory_stocklocation_changelist"),
]


@login_required
def home(request):
    setup_links = None
    if request.user.is_staff:
        setup_links = [(label, reverse(name)) for label, name in SETUP_LINKS]

    modules = []
    for m in MODULES:
        module = dict(m)
        if module["available"]:
            module["url"] = reverse(module["url_name"])
        modules.append(module)

    return render(request, "core/home.html", {"modules": modules, "setup_links": setup_links})
