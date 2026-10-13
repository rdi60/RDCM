from datetime import datetime, time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from billing.models import Invoice, Payment
from clinic.models import Resource
from inventory.models import Item, StockBatch, StockTransaction
from scheduling.models import Appointment

from .utils import recall_message, resolve_period, whatsapp_link

ZERO = Decimal("0.00")


def _day_bounds(start_date, end_date):
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
    return start_dt, end_dt


@login_required
def reports_hub(request):
    return render(request, "reports/hub.html")


@login_required
def footfall_report(request):
    period, start, end = resolve_period(request)
    start_dt, end_dt = _day_bounds(start, end)

    appts = Appointment.objects.filter(start_time__gte=start_dt, start_time__lte=end_dt)
    total = appts.count()

    by_status = list(
        appts.values("status").annotate(count=Count("id")).order_by("-count")
    )
    status_labels = dict(Appointment.Status.choices)
    for row in by_status:
        row["label"] = status_labels.get(row["status"], row["status"])

    by_doctor = list(
        appts.values("doctor__full_name").annotate(count=Count("id")).order_by("-count")
    )
    by_treatment = list(
        appts.exclude(treatment__isnull=True)
        .values("treatment__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return render(
        request,
        "reports/footfall.html",
        {
            "period": period,
            "start": start,
            "end": end,
            "total": total,
            "by_status": by_status,
            "by_doctor": by_doctor,
            "by_treatment": by_treatment,
        },
    )


@login_required
def revenue_report(request):
    period, start, end = resolve_period(request)
    start_dt, end_dt = _day_bounds(start, end)

    invoices = (
        Invoice.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt)
        .exclude(status__in=[Invoice.Status.DRAFT, Invoice.Status.VOID])
        .select_related("appointment__doctor")
        .prefetch_related("line_items__treatment")
    )

    total_invoiced = ZERO
    by_doctor = {}
    by_treatment = {}
    for inv in invoices:
        total_invoiced += inv.total
        if inv.appointment_id and inv.appointment.doctor_id:
            name = inv.appointment.doctor.full_name
            by_doctor[name] = by_doctor.get(name, ZERO) + inv.total
        for item in inv.line_items.all():
            key = item.treatment.name if item.treatment_id else item.description
            by_treatment[key] = by_treatment.get(key, ZERO) + item.line_total

    payments = Payment.objects.filter(paid_at__gte=start_dt, paid_at__lte=end_dt)
    total_collected = ZERO
    by_mode = {}
    for p in payments:
        total_collected += p.amount
        by_mode[p.get_mode_display()] = by_mode.get(p.get_mode_display(), ZERO) + p.amount

    by_doctor_rows = sorted(by_doctor.items(), key=lambda row: row[1], reverse=True)
    by_treatment_rows = sorted(by_treatment.items(), key=lambda row: row[1], reverse=True)
    by_mode_rows = sorted(by_mode.items(), key=lambda row: row[1], reverse=True)

    return render(
        request,
        "reports/revenue.html",
        {
            "period": period,
            "start": start,
            "end": end,
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "by_doctor_rows": by_doctor_rows,
            "by_treatment_rows": by_treatment_rows,
            "by_mode_rows": by_mode_rows,
        },
    )


@login_required
def utilization_report(request):
    period, start, end = resolve_period(request)
    start_dt, end_dt = _day_bounds(start, end)

    num_days = (end - start).days + 1
    minutes_per_day = (settings.CLINIC_CLOSE_HOUR - settings.CLINIC_OPEN_HOUR) * 60
    available_minutes = minutes_per_day * num_days

    rows = []
    resources = Resource.objects.filter(status=Resource.Status.ACTIVE).order_by("type", "number", "name")
    for resource in resources:
        appts = Appointment.objects.filter(
            resource=resource, start_time__gte=start_dt, start_time__lte=end_dt
        ).exclude(status=Appointment.Status.CANCELLED)
        booked_minutes = sum(
            (a.end_time - a.start_time).total_seconds() / 60 for a in appts
        )
        utilization = (booked_minutes / available_minutes * 100) if available_minutes else 0
        rows.append(
            {
                "resource": resource,
                "appointment_count": appts.count(),
                "booked_minutes": round(booked_minutes),
                "available_minutes": available_minutes,
                "utilization": round(utilization, 1),
            }
        )

    return render(
        request,
        "reports/utilization.html",
        {"period": period, "start": start, "end": end, "rows": rows},
    )


@login_required
def inventory_report(request):
    period, start, end = resolve_period(request)
    start_dt, end_dt = _day_bounds(start, end)

    receipts = StockTransaction.objects.filter(
        tx_type=StockTransaction.TxType.RECEIPT, created_at__gte=start_dt, created_at__lte=end_dt
    ).select_related("batch")
    purchase_value = sum((tx.quantity * tx.batch.cost_price for tx in receipts), ZERO)

    consumption = StockTransaction.objects.filter(
        tx_type=StockTransaction.TxType.CONSUMPTION, created_at__gte=start_dt, created_at__lte=end_dt
    ).select_related("batch")
    consumption_value = sum((-tx.quantity * tx.batch.cost_price for tx in consumption), ZERO)

    stock_value = sum(
        (batch.quantity_remaining * batch.cost_price for batch in StockBatch.objects.all()), ZERO
    )
    low_stock_items = [
        item for item in Item.objects.filter(is_active=True, reorder_level__gt=0) if item.is_low_stock
    ]

    return render(
        request,
        "reports/inventory.html",
        {
            "period": period,
            "start": start,
            "end": end,
            "purchase_value": purchase_value,
            "consumption_value": consumption_value,
            "stock_value": stock_value,
            "low_stock_items": low_stock_items,
        },
    )


@login_required
def recall_report(request):
    period, start, end = resolve_period(request)

    candidates = (
        Appointment.objects.filter(
            status=Appointment.Status.COMPLETED,
            follow_up_date__gte=start,
            follow_up_date__lte=end,
        )
        .select_related("patient", "doctor", "treatment")
        .order_by("follow_up_date")
    )

    rows = []
    for appt in candidates:
        already_rebooked = (
            Appointment.objects.filter(patient=appt.patient, start_time__date__gt=appt.start_time.date())
            .exclude(status=Appointment.Status.CANCELLED)
            .exists()
        )
        if already_rebooked:
            continue
        message = recall_message(appt.patient, appt.doctor, appt.treatment)
        rows.append(
            {
                "appt": appt,
                "wa_link": whatsapp_link(appt.patient.phone, message),
                "message": message,
            }
        )

    return render(
        request,
        "reports/recall.html",
        {"period": period, "start": start, "end": end, "rows": rows},
    )
