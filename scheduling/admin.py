from django.contrib import admin

from .models import Appointment, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["full_name", "uhid", "phone", "email", "created_at"]
    search_fields = ["full_name", "uhid", "phone", "email"]
    readonly_fields = ["uhid", "created_at"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["start_time", "patient", "doctor", "resource", "status", "token_number"]
    list_filter = ["status", "doctor", "resource"]
    search_fields = ["patient__full_name", "patient__uhid", "patient__phone"]
    date_hierarchy = "start_time"
    readonly_fields = ["token_number", "created_by", "created_at", "updated_at"]
