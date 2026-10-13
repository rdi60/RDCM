from django.conf import settings
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

# HIPAA access control: person-or-entity authentication (164.312(d)). Every
# authenticated user must verify a TOTP device for the session before
# reaching anything else. These are the only URL names exempt from that —
# the MFA flow itself, plus login/logout (handled before a user exists).
EXEMPT_URL_NAMES = {"login", "logout", "mfa_setup", "mfa_qr", "mfa_verify"}


class RequireOTPMiddleware:
    """Must sit after django_otp.middleware.OTPMiddleware (needs
    request.user.is_verified()) and after AuthenticationMiddleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_verified():
            if request.path_info.startswith(settings.STATIC_URL) or request.path_info.startswith(
                settings.MEDIA_URL
            ):
                return self.get_response(request)
            try:
                url_name = resolve(request.path_info).url_name
            except Resolver404:
                url_name = None
            if url_name not in EXEMPT_URL_NAMES:
                if user.totpdevice_set.filter(confirmed=True).exists():
                    return redirect("mfa_verify")
                return redirect("mfa_setup")
        return self.get_response(request)
