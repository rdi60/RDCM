from django.contrib import admin

from .models import Procedure


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "default_duration_minutes", "requires_room_type", "default_rate", "is_active")
    search_fields = ("code", "name")
    list_filter = ("category", "requires_room_type", "is_active")
