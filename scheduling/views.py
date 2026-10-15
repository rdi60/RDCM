import math
from datetime import datetime, time, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from audit.utils import log_view
from clinic.models import Doctor, Resource

from .forms import AppointmentForm, PatientForm
from .models import Appointment, Patient

SLOT_MINUTES = settings.CLINIC_SLOT_MINUTES


# ---- Patients ---------------------------------------------------------

@login_required
@permission_required("scheduling.view_patient", raise_exception=True)
def patient_list(request):
    query = request.GET.get("q", "").strip()
    patients = Patient.objects.all()
    if query:
        patients = patients.filter(
            Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(uhid__icontains=query)
        )
    return render(request, "scheduling/patient_list.html", {"patients": patients[:200], "query": query})


@login_required
@permission_required("scheduling.add_patient", raise_exception=True)
def patient_create(request):
    next_url = request.GET.get("next", "")
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.registered_by = request.user
            if patient.consent_given and not patient.consent_date:
                patient.consent_date = timezone.localdate()
            patient.save()
            messages.success(request, f"Registered {patient.full_name} ({patient.uhid}).")
            if next_url:
                sep = "&" if "?" in next_url else "?"
                return redirect(f"{next_url}{sep}patient={patient.pk}")
            return redirect("patient_detail", pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, "scheduling/patient_form.html", {"form": form, "next": next_url})


@login_required
@permission_required("scheduling.view_patient", raise_exception=True)
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    log_view(request, patient)
    appointments = patient.appointments.select_related("doctor", "resource", "treatment").order_by(
        "-start_time"
    )
    return render(
        request, "scheduling/patient_detail.html", {"patient": patient, "appointments": appointments}
    )


# ---- Calendar -----------------------------------------------------------

def _day_bounds(day):
    open_dt = timezone.make_aware(datetime.combine(day, time(settings.CLINIC_OPEN_HOUR, 0)))
    close_dt = timezone.make_aware(datetime.combine(day, time(settings.CLINIC_CLOSE_HOUR, 0)))
    return open_dt, close_dt


def _day_slots(day):
    open_dt, close_dt = _day_bounds(day)
    slots = []
    cur = open_dt
    while cur < close_dt:
        slots.append(cur)
        cur += timedelta(minutes=SLOT_MINUTES)
    return slots, open_dt, close_dt


@login_required
@permission_required("scheduling.view_appointment", raise_exception=True)
def calendar_view(request):
    view = request.GET.get("view", "day")
    date_str = request.GET.get("date")
    selected_date = parse_date(date_str) if date_str else None
    if not selected_date:
        selected_date = timezone.localdate()

    if view == "week":
        return _week_view(request, selected_date)
    return _day_view(request, selected_date)


def _day_view(request, selected_date):
    slots, open_dt, close_dt = _day_slots(selected_date)
    resources = list(Resource.objects.filter(status=Resource.Status.ACTIVE).order_by("type", "number", "name"))
    col_for = {r.id: idx + 2 for idx, r in enumerate(resources)}

    appointments = (
        Appointment.objects.filter(start_time__lt=close_dt, end_time__gt=open_dt)
        .exclude(status=Appointment.Status.CANCELLED)
        .select_related("patient", "doctor", "resource")
    )

    blocks = []
    covered_by_resource = {r.id: set() for r in resources}
    for appt in appointments:
        if appt.resource_id not in col_for:
            continue
        start_idx = max(0, int((appt.start_time - open_dt).total_seconds() // 60 // SLOT_MINUTES))
        end_idx = math.ceil((appt.end_time - open_dt).total_seconds() / 60 / SLOT_MINUTES)
        end_idx = min(max(end_idx, start_idx + 1), len(slots))
        blocks.append(
            {
                "appt": appt,
                "col": col_for[appt.resource_id],
                "row_start": start_idx + 2,
                "span": end_idx - start_idx,
            }
        )
        covered_by_resource[appt.resource_id].update(range(start_idx, end_idx))

    empty_cells = []
    for r in resources:
        covered = covered_by_resource[r.id]
        for i, slot_time in enumerate(slots):
            if i not in covered:
                empty_cells.append(
                    {
                        "col": col_for[r.id],
                        "row": i + 2,
                        "resource_id": r.id,
                        "slot_iso": timezone.localtime(slot_time).strftime("%Y-%m-%dT%H:%M"),
                    }
                )

    time_labels = [
        {"row": i + 2, "label": timezone.localtime(s).strftime("%H:%M")} for i, s in enumerate(slots)
    ]

    context = {
        "view": "day",
        "selected_date": selected_date,
        "prev_date": selected_date - timedelta(days=1),
        "next_date": selected_date + timedelta(days=1),
        "resources": resources,
        "col_count": len(resources) + 1,
        "slot_count": len(slots),
        "time_labels": time_labels,
        "blocks": blocks,
        "empty_cells": empty_cells,
    }
    return render(request, "scheduling/calendar_day.html", context)


def _week_view(request, selected_date):
    week_start = selected_date - timedelta(days=selected_date.weekday())
    days = [week_start + timedelta(days=i) for i in range(7)]
    doctors = list(Doctor.objects.filter(is_active=True).order_by("full_name"))

    day_start = timezone.make_aware(datetime.combine(days[0], time.min))
    day_end = timezone.make_aware(datetime.combine(days[-1], time.max))
    appointments = (
        Appointment.objects.filter(start_time__gte=day_start, start_time__lte=day_end)
        .exclude(status=Appointment.Status.CANCELLED)
        .select_related("doctor")
    )
    counts = {}
    for appt in appointments:
        key = (appt.doctor_id, timezone.localtime(appt.start_time).date())
        counts[key] = counts.get(key, 0) + 1

    rows = []
    for doctor in doctors:
        cells = [{"date": day, "count": counts.get((doctor.id, day), 0)} for day in days]
        rows.append({"doctor": doctor, "cells": cells})

    context = {
        "view": "week",
        "selected_date": selected_date,
        "week_start": week_start,
        "prev_date": selected_date - timedelta(days=7),
        "next_date": selected_date + timedelta(days=7),
        "days": days,
        "rows": rows,
    }
    return render(request, "scheduling/calendar_week.html", context)


# ---- Appointments -------------------------------------------------------

@login_required
@permission_required("scheduling.add_appointment", raise_exception=True)
def appointment_create(request):
    resource_id = request.GET.get("resource", "")
    start_param = request.GET.get("start", "")
    patient_id = request.GET.get("patient", "")

    initial = {}
    if resource_id:
        initial["resource"] = resource_id
    if patient_id:
        initial["patient"] = patient_id
    if start_param:
        start_dt = parse_datetime(start_param)
        if start_dt:
            if timezone.is_naive(start_dt):
                start_dt = timezone.make_aware(start_dt)
            initial["start_time"] = start_dt
            initial["end_time"] = start_dt + timedelta(minutes=SLOT_MINUTES)

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.created_by = request.user
            appt.save()
            messages.success(request, f"Booked token #{appt.token_number} for {appt.patient.full_name}.")
            return redirect("calendar")
    else:
        form = AppointmentForm(initial=initial)

    params = {k: v for k, v in {"resource": resource_id, "start": start_param}.items() if v}
    register_next = reverse("appointment_create")
    if params:
        register_next += "?" + urlencode(params)

    return render(
        request,
        "scheduling/appointment_form.html",
        {"form": form, "mode": "create", "register_next": register_next, "query": request.GET.urlencode()},
    )


@login_required
@permission_required("scheduling.view_appointment", raise_exception=True)
def appointment_detail(request, pk):
    appt = get_object_or_404(
        Appointment.objects.select_related("patient", "doctor", "resource", "treatment"), pk=pk
    )
    log_view(request, appt)
    if request.method == "POST" and request.POST.get("action") in ("reschedule", "set_follow_up"):
        if not request.user.has_perm("scheduling.change_appointment"):
            raise PermissionDenied
    if request.method == "POST" and request.POST.get("action") == "reschedule":
        reschedule_form = AppointmentForm(request.POST, instance=appt)
        if reschedule_form.is_valid():
            reschedule_form.save()
            messages.success(request, "Appointment rescheduled.")
            return redirect("appointment_detail", pk=appt.pk)
    elif request.method == "POST" and request.POST.get("action") == "set_follow_up":
        if request.POST.get("clear"):
            follow_up_date = None
        else:
            follow_up_date = parse_date(request.POST.get("follow_up_date", ""))
        appt.follow_up_date = follow_up_date
        appt.save(update_fields=["follow_up_date"])
        messages.success(
            request,
            f"Follow-up set for {follow_up_date:%d %b %Y}." if follow_up_date else "Follow-up cleared.",
        )
        return redirect("appointment_detail", pk=appt.pk)
    else:
        reschedule_form = AppointmentForm(instance=appt)

    next_statuses = Appointment.NEXT_STATUSES.get(appt.status, [])
    next_status_choices = [(s.value, s.label) for s in next_statuses]
    return render(
        request,
        "scheduling/appointment_detail.html",
        {
            "appt": appt,
            "reschedule_form": reschedule_form,
            "next_status_choices": next_status_choices,
            "can_reschedule": appt.status in (Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED),
        },
    )


@login_required
@permission_required("scheduling.change_appointment", raise_exception=True)
def appointment_set_status(request, pk, new_status):
    if request.method != "POST":
        return redirect("appointment_detail", pk=pk)
    appt = get_object_or_404(Appointment, pk=pk)
    allowed = Appointment.NEXT_STATUSES.get(appt.status, [])
    if new_status not in allowed:
        messages.error(request, f"Can't move from {appt.get_status_display()} to that status.")
    else:
        appt.status = new_status
        appt.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Marked {appt.patient.full_name} as {appt.get_status_display()}.")
    return redirect("appointment_detail", pk=pk)
