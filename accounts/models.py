from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model (set as AUTH_USER_MODEL from project start, per Django's
    own recommendation, so later apps — Doctor, Employee, etc. — can safely
    extend it with a OneToOneField).

    Role is represented with Django's built-in Groups (Clinic Admin, Doctor,
    Receptionist, Accountant, Nurse/Assistant — see seed_roles command), not a
    separate field: that lets each module gate screens with the standard
    permission system instead of hand-rolled role checks.
    """

    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username
