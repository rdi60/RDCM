from django.contrib import admin

from .models import Patient, PatientMerge


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("uhid", "name", "phone", "registered_at_branch", "status", "created_at")
    search_fields = ("uhid", "name", "phone", "email")
    list_filter = ("registered_at_branch", "status")


@admin.register(PatientMerge)
class PatientMergeAdmin(admin.ModelAdmin):
    list_display = ("source_patient", "target_patient", "merged_by", "merged_at")
    readonly_fields = ("merged_at",)
