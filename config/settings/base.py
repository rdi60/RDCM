"""
Settings shared by every environment. Environment-specific values (DEBUG,
ALLOWED_HOSTS, database credentials, ...) come from environment variables
via django-environ — see .env.example for the full list.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "axes",
    "accounts",
    "core",
    "clinic",
    "scheduling",
    "billing",
    "inventory",
    "reports",
    "audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "axes.middleware.AxesMiddleware",
    "core.middleware.RequireOTPMiddleware",
    "audit.middleware.CurrentRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.clinic",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# --- HIPAA technical safeguards -------------------------------------------
# These cover 45 CFR 164.312's access control, audit, and transmission
# security requirements as far as application code can. They do NOT by
# themselves make this deployment "HIPAA compliant" — see SECURITY.md for
# the administrative, physical, and Business Associate Agreement
# requirements that are organizational, not code.

# Access control: automatic logoff (164.312(a)(2)(iii)). SESSION_SAVE_EVERY_REQUEST
# makes Django refresh the session's expiry on every request, turning
# SESSION_COOKIE_AGE into a sliding idle timeout rather than a fixed one.
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = env.int("SESSION_IDLE_TIMEOUT_SECONDS", default=900)  # 15 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # the CSRF cookie must be readable by JS that sets the header; it isn't the session

# Access control: account lockout (django-axes) after repeated failed logins.
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = env.int("AXES_COOLOFF_HOURS", default=1)  # hours
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True

# Access control: MFA (django-otp TOTP), enforced by
# core.middleware.RequireOTPMiddleware for every authenticated request.
# OTP_TOTP_ISSUER is set below, once CLINIC_NAME exists.
#
# REQUIRE_MFA defaults to True — HIPAA's person-or-entity authentication
# requirement (164.312(d)) needs it on for any deployment handling real
# patient data. Set REQUIRE_MFA=False in .env only for a throwaway test
# environment with no real PHI in it, and turn it back on before go-live.
REQUIRE_MFA = env.bool("REQUIRE_MFA", default=True)

# Field-level encryption at rest for the most sensitive free-text fields
# (Patient.medical_history, Appointment.notes) — see core/fields.py. The key
# lives only in the environment, never in the database or source control.
# Generate one with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

# The recall report's WhatsApp reminder (reports/utils.py) sends its message
# over wa.me, which has no Business Associate Agreement available on
# standard WhatsApp. Leave this off unless you have a BAA with a WhatsApp
# Business Solution Provider; with it off, the message omits treatment and
# doctor name (still reveals the clinic + that this number has an account
# there, which can't be avoided while using this channel at all).
WHATSAPP_INCLUDE_CLINICAL_DETAILS = env.bool("WHATSAPP_INCLUDE_CLINICAL_DETAILS", default=False)

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Clinic-level settings, read by templates (core.context_processors.clinic)
CLINIC_NAME = env("CLINIC_NAME", default="Raja Dental")
HRMS_URL = env("HRMS_URL", default="")

OTP_TOTP_ISSUER = CLINIC_NAME

# Operating hours the day-view calendar grid is drawn across.
CLINIC_OPEN_HOUR = env.int("CLINIC_OPEN_HOUR", default=9)
CLINIC_CLOSE_HOUR = env.int("CLINIC_CLOSE_HOUR", default=20)
CLINIC_SLOT_MINUTES = env.int("CLINIC_SLOT_MINUTES", default=30)
