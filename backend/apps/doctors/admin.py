from django.contrib import admin

from .models import Assistant, Doctor, DoctorAvailability, DoctorScheduleException


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "registration_no", "specialization", "is_active")
    search_fields = ("user__name", "registration_no")


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("doctor", "branch", "day_of_week", "start_time", "end_time", "effective_from", "effective_to")
    list_filter = ("branch", "day_of_week")


@admin.register(DoctorScheduleException)
class DoctorScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ("doctor", "date", "is_available", "start_time", "end_time")
    list_filter = ("is_available",)


@admin.register(Assistant)
class AssistantAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active")
