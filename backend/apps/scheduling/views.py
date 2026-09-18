import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.dateparse import parse_date
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Appointment, TreatmentPlan
from .serializers import (
    AppointmentBookSerializer,
    AppointmentCancelSerializer,
    AppointmentRescheduleSerializer,
    AppointmentSerializer,
    TreatmentPlanSerializer,
)


class TreatmentPlanViewSet(viewsets.ModelViewSet):
    serializer_class = TreatmentPlanSerializer
    queryset = TreatmentPlan.objects.select_related("patient", "doctor")


class AppointmentViewSet(viewsets.ModelViewSet):
    """Appointment booking API.

    List supports the three views asked for in Phase 1:
      - day view by chair:   ?branch=<id>&date=YYYY-MM-DD  (group client-side by `chair`)
      - day view by doctor:  ?branch=<id>&date=YYYY-MM-DD&doctor=<id>
      - week view by doctor: ?doctor=<id>&week_start=YYYY-MM-DD (7 days from week_start)
    Cancelled/no-show appointments are included unless ?active_only=1 is passed,
    since the day view still needs to show a cancelled slot as available context.
    """

    queryset = Appointment.objects.select_related(
        "patient", "doctor__user", "chair", "branch", "treatment_plan",
    ).prefetch_related("appointment_procedures__procedure")

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentBookSerializer
        return AppointmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        branch = params.get("branch")
        if branch:
            qs = qs.filter(branch_id=branch)

        doctor = params.get("doctor")
        if doctor:
            qs = qs.filter(doctor_id=doctor)

        chair = params.get("chair")
        if chair:
            qs = qs.filter(chair_id=chair)

        patient = params.get("patient")
        if patient:
            qs = qs.filter(patient_id=patient)

        date_str = params.get("date")
        if date_str:
            day = parse_date(date_str)
            if day is None:
                raise drf_serializers.ValidationError({"date": "Expected YYYY-MM-DD."})
            qs = qs.filter(start_time__date=day)

        week_start_str = params.get("week_start")
        if week_start_str:
            week_start = parse_date(week_start_str)
            if week_start is None:
                raise drf_serializers.ValidationError({"week_start": "Expected YYYY-MM-DD."})
            week_end = week_start + datetime.timedelta(days=7)
            qs = qs.filter(start_time__date__gte=week_start, start_time__date__lt=week_end)

        if params.get("active_only") in ("1", "true", "True"):
            qs = qs.exclude(status__in=Appointment.INACTIVE_STATUSES)

        return qs.order_by("start_time")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

    def _run_action(self, request, action_serializer_class):
        appointment = self.get_object()
        context = {"request": request, "appointment": appointment}
        serializer = action_serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(AppointmentSerializer(updated).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        return self._run_action(request, AppointmentRescheduleSerializer)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._run_action(request, AppointmentCancelSerializer)

    def _simple_transition(self, request, service_fn):
        appointment = self.get_object()
        try:
            updated = service_fn(appointment=appointment)
        except DjangoValidationError as exc:
            raise drf_serializers.ValidationError(exc.message if hasattr(exc, "message") else exc.messages)
        return Response(AppointmentSerializer(updated).data)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        return self._simple_transition(request, services.check_in)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._simple_transition(request, services.start_appointment)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._simple_transition(request, services.complete_appointment)

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        return self._simple_transition(request, services.mark_no_show)
