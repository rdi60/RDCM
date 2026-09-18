from django.contrib import admin

from .models import Appointment, AppointmentAssistant, AppointmentProcedure, TreatmentPlan


class AppointmentProcedureInline(admin.TabularInline):
    model = AppointmentProcedure
    extra = 0


class AppointmentAssistantInline(admin.TabularInline):
    model = AppointmentAssistant
    extra = 0


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "chair", "start_time", "end_time", "status", "booking_type")
    list_filter = ("branch", "status", "booking_type")
    search_fields = ("patient__name", "patient__uhid")
    inlines = [AppointmentProcedureInline, AppointmentAssistantInline]
    # Financial-grade append-only isn't required for appointments (unlike
    # billing), but status changes should go through apps.scheduling.services
    # so the exclusion constraints and validation always run — the admin is
    # for read/troubleshooting, not for rescheduling by hand.
    readonly_fields = ("blocked_until", "created_at")


@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "patient", "doctor", "planned_sittings", "status")
    list_filter = ("status",)
