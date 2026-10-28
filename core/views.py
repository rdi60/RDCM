import io

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from scheduling.models import SelfRegistration

from .forms import TOTPTokenForm

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

    pending_self_registrations = None
    if request.user.has_perm("scheduling.add_patient"):
        pending_self_registrations = SelfRegistration.objects.filter(
            status=SelfRegistration.Status.PENDING
        ).count()
        modules.append(
            {
                "name": "Patient self sign-ups",
                "available": True,
                "url": reverse("self_registration_list"),
                "status_label": (
                    f"{pending_self_registrations} awaiting review"
                    if pending_self_registrations
                    else "All caught up"
                ),
            }
        )

    return render(
        request,
        "core/home.html",
        {
            "modules": modules,
            "setup_links": setup_links,
            "pending_self_registrations": pending_self_registrations,
        },
    )


@login_required
def mfa_setup(request):
    """First-time TOTP enrollment. Reached automatically by
    RequireOTPMiddleware for any authenticated user with no confirmed
    device yet — there's no way to opt out of MFA from here."""
    if not settings.REQUIRE_MFA or request.user.is_verified():
        return redirect("home")
    if request.user.totpdevice_set.filter(confirmed=True).exists():
        return redirect("mfa_verify")

    device, _ = TOTPDevice.objects.get_or_create(
        user=request.user, confirmed=False, defaults={"name": "default"}
    )

    if request.method == "POST":
        form = TOTPTokenForm(request.POST)
        if form.is_valid():
            if device.verify_token(form.cleaned_data["token"]):
                device.confirmed = True
                device.save(update_fields=["confirmed"])
                otp_login(request, device)
                messages.success(request, "Two-factor authentication is now enabled on your account.")
                return redirect("home")
            form.add_error("token", "That code didn't match. Check the time on your phone and try again.")
    else:
        form = TOTPTokenForm()

    return render(request, "core/mfa_setup.html", {"form": form})


@login_required
def mfa_qr(request):
    """PNG QR code for the authenticator app to scan — only ever the
    requesting user's own unconfirmed device, never anyone else's."""
    device = TOTPDevice.objects.filter(user=request.user, confirmed=False).order_by("-id").first()
    if not device:
        raise Http404
    image = qrcode.make(device.config_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@login_required
def mfa_verify(request):
    """Per-session TOTP challenge for a user who already has a confirmed
    device (every login after the first, since OTPMiddleware's verified
    state doesn't persist across sessions by design)."""
    if not settings.REQUIRE_MFA or request.user.is_verified():
        return redirect("home")
    device = request.user.totpdevice_set.filter(confirmed=True).first()
    if not device:
        return redirect("mfa_setup")

    if request.method == "POST":
        form = TOTPTokenForm(request.POST)
        if form.is_valid():
            if device.verify_token(form.cleaned_data["token"]):
                otp_login(request, device)
                return redirect("home")
            form.add_error("token", "That code didn't match. Check the time on your phone and try again.")
    else:
        form = TOTPTokenForm()

    return render(request, "core/mfa_verify.html", {"form": form})
