import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.db import models


class Role(models.Model):
    """
    Business-level role (distinct from Django's own permission system).
    Enforcement of what each role can do/see lands in Phase 3; the roles
    themselves are named now because accounts.User.role is referenced
    everywhere (created_by/approved_by FKs) from Phase 1 onward.
    """

    OWNER = "owner"
    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    DENTAL_ASSISTANT = "dental_assistant"
    LAB_TECHNICIAN = "lab_technician"
    ACCOUNTANT = "accountant"

    id = models.SmallAutoField(primary_key=True)
    code = models.CharField(max_length=32, unique=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.code


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, name, password=None, **extra_fields):
        if not phone:
            raise ValueError("Users must have a phone number")
        if not name:
            raise ValueError("Users must have a name")
        user = self.model(phone=phone, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, name, password, **extra_fields)

    def create_superuser(self, phone, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(phone, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model, set as AUTH_USER_MODEL from the very first migration.
    Every staff login (reception, doctors, assistants, lab, accounts, admin)
    is one row here; role-specific detail tables (doctors.Doctor,
    doctors.Assistant, ...) have a OneToOne back to this.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name} ({self.phone})"
