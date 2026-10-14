from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Clinic profile", {"fields": ("phone",)}),
    )
    list_display = ("username", "get_full_name", "email", "is_staff", "is_active")
    list_filter = DjangoUserAdmin.list_filter + ("groups",)
