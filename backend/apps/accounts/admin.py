from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "code")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("name",)
    list_display = ("name", "phone", "email", "role", "is_active", "is_staff")
    search_fields = ("name", "phone", "email")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal info", {"fields": ("name", "email", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "name", "email", "role", "password1", "password2"),
        }),
    )
    readonly_fields = ("date_joined",)
