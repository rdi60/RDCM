from django.contrib import admin

from .models import Branch, BranchPatientSequence, Chair, Room, StaffBranch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "floor", "room_type", "is_active")
    list_filter = ("branch", "room_type")


@admin.register(Chair)
class ChairAdmin(admin.ModelAdmin):
    list_display = ("code", "branch", "room", "status", "default_buffer_minutes")
    list_filter = ("branch", "status")


@admin.register(StaffBranch)
class StaffBranchAdmin(admin.ModelAdmin):
    list_display = ("user", "branch")


admin.site.register(BranchPatientSequence)
