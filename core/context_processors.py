from django.conf import settings


def clinic(request):
    """Clinic-wide values every template can use without each view passing them."""
    return {
        "clinic_name": settings.CLINIC_NAME,
        "hrms_url": settings.HRMS_URL,
    }
