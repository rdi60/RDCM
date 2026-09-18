from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.clinic.models import Branch, Chair
from apps.doctors.models import Doctor
from apps.patients.models import Patient
from apps.procedures.models import Procedure

from . import services
from .models import Appointment, AppointmentProcedure, TreatmentPlan


class TreatmentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentPlan
        fields = ["id", "patient", "doctor", "title", "planned_sittings", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class AppointmentProcedureSerializer(serializers.ModelSerializer):
    procedure_code = serializers.CharField(source="procedure.code", read_only=True)
    procedure_name = serializers.CharField(source="procedure.name", read_only=True)

    class Meta:
        model = AppointmentProcedure
        fields = ["id", "procedure", "procedure_code", "procedure_name", "tooth_numbers"]


class AppointmentSerializer(serializers.ModelSerializer):
    """Read representation. Appointments are created/modified through the
    dedicated action serializers below, which call apps.scheduling.services
    — never through a plain .save(), because booking has to run the
    room-type check and the duration/buffer calculation first."""

    procedures = AppointmentProcedureSerializer(source="appointment_procedures", many=True, read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    patient_uhid = serializers.CharField(source="patient.uhid", read_only=True)
    doctor_name = serializers.CharField(source="doctor.user.name", read_only=True)
    chair_code = serializers.CharField(source="chair.code", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "branch", "patient", "patient_name", "patient_uhid", "doctor", "doctor_name",
            "chair", "chair_code", "treatment_plan", "start_time", "end_time", "buffer_minutes",
            "status", "booking_type", "notes", "cancelled_reason", "cancelled_by", "cancelled_at",
            "created_by", "created_at", "procedures",
        ]
        read_only_fields = [
            "id", "end_time", "status", "cancelled_reason", "cancelled_by", "cancelled_at",
            "created_by", "created_at",
        ]


class AppointmentBookSerializer(serializers.Serializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.filter(is_active=True))
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.filter(status=Patient.ACTIVE))
    doctor = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.filter(is_active=True))
    chair = serializers.PrimaryKeyRelatedField(queryset=Chair.objects.filter(status=Chair.ACTIVE))
    treatment_plan = serializers.PrimaryKeyRelatedField(queryset=TreatmentPlan.objects.all(), required=False, allow_null=True)
    start_time = serializers.DateTimeField()
    procedure_ids = serializers.PrimaryKeyRelatedField(
        source="procedures", queryset=Procedure.objects.filter(is_active=True), many=True,
    )
    buffer_minutes = serializers.IntegerField(required=False, min_value=0, allow_null=True)
    booking_type = serializers.ChoiceField(choices=Appointment.BOOKING_TYPE_CHOICES, default=Appointment.REGULAR)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def save(self, **kwargs):
        request = self.context["request"]
        data = self.validated_data
        try:
            return services.book_appointment(
                branch=data["branch"], patient=data["patient"], doctor=data["doctor"], chair=data["chair"],
                start_time=data["start_time"], procedures=list(data["procedures"]),
                buffer_minutes=data.get("buffer_minutes"), booking_type=data["booking_type"],
                treatment_plan=data.get("treatment_plan"), notes=data.get("notes", ""),
                created_by=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message if hasattr(exc, "message") else exc.messages)


class AppointmentRescheduleSerializer(serializers.Serializer):
    chair = serializers.PrimaryKeyRelatedField(queryset=Chair.objects.filter(status=Chair.ACTIVE), required=False)
    doctor = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.filter(is_active=True), required=False)
    start_time = serializers.DateTimeField(required=False)
    buffer_minutes = serializers.IntegerField(required=False, min_value=0)

    def save(self, **kwargs):
        try:
            return services.reschedule_appointment(appointment=self.context["appointment"], **self.validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message if hasattr(exc, "message") else exc.messages)


class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField()

    def save(self, **kwargs):
        request = self.context["request"]
        try:
            return services.cancel_appointment(
                appointment=self.context["appointment"], reason=self.validated_data["reason"],
                cancelled_by=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message if hasattr(exc, "message") else exc.messages)
