import calendar as calendar_module
from urllib.parse import quote

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date


def resolve_period(request):
    """Today / this week / this month / a custom range, read from ?period=
    and (for custom) ?start=&end=. Shared by every MIS report so they all
    filter the same way."""
    period = request.GET.get("period", "today")
    today = timezone.localdate()

    if period == "week":
        start = today - timezone.timedelta(days=today.weekday())
        end = start + timezone.timedelta(days=6)
    elif period == "month":
        start = today.replace(day=1)
        last_day = calendar_module.monthrange(today.year, today.month)[1]
        end = today.replace(day=last_day)
    elif period == "custom":
        start = parse_date(request.GET.get("start", "")) or today
        end = parse_date(request.GET.get("end", "")) or today
    else:
        period = "today"
        start = end = today

    return period, start, end


def normalize_phone(raw):
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = "91" + digits[1:]
    return digits


def whatsapp_link(phone, message):
    digits = normalize_phone(phone)
    if not digits:
        return None
    return f"https://wa.me/{digits}?text={quote(message)}"


def recall_message(patient, doctor, treatment):
    treatment_bit = f" ({treatment.name})" if treatment else ""
    return (
        f"Hi {patient.full_name}, this is a reminder from {settings.CLINIC_NAME} for your "
        f"follow-up{treatment_bit} with {doctor.full_name}. Please call us to book your "
        f"appointment. Thank you!"
    )
