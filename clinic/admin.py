from django.contrib import admin

from .models import (
    Doctor,
    DoctorQualification,
    MedicalHistoryCondition,
    PatientTitle,
    ReferralSource,
    Resource,
    Specialty,
    Treatment,
)


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class DoctorQualificationInline(admin.TabularInline):
    model = DoctorQualification
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    inlines = [DoctorQualificationInline]
    filter_horizontal = ["specialties"]
    list_display = ["full_name", "specialty_list", "registration_number", "phone", "is_active"]
    list_filter = ["is_active", "specialties"]
    search_fields = ["full_name", "registration_number", "phone", "email"]

    @admin.display(description="Specialties")
    def specialty_list(self, obj):
        return ", ".join(s.name for s in obj.specialties.all())


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "number", "status"]
    list_filter = ["type", "status"]
    search_fields = ["name"]


@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "default_duration_minutes", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "category"]


@admin.register(PatientTitle)
class PatientTitleAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    ordering = ["sort_order", "name"]


@admin.register(ReferralSource)
class ReferralSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "is_corporate", "sort_order", "is_active"]
    list_filter = ["is_corporate", "is_active"]
    list_editable = ["sort_order", "is_active"]
    ordering = ["sort_order", "name"]


@admin.register(MedicalHistoryCondition)
class MedicalHistoryConditionAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    search_fields = ["name"]
    ordering = ["sort_order", "name"]
