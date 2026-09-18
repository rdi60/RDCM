import uuid

from django.conf import settings
from django.db import models


class Branch(models.Model):
    """A clinic location. See docs/ARCHITECTURE.md §2 — threaded through
    every branch-scoped table from day one, even though there's one branch
    to start with."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=16, unique=True, help_text="Short prefix used in UHIDs, e.g. 'RDC1'")
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "branches"

    def __str__(self):
        return self.name


class BranchPatientSequence(models.Model):
    """Backs sequential-per-branch UHID generation. See
    apps.patients.services.generate_uhid — the UPDATE ... RETURNING against
    this row is what makes numbering safe under concurrent registrations."""

    branch = models.OneToOneField(Branch, on_delete=models.PROTECT, primary_key=True)
    last_patient_no = models.IntegerField(default=0)

    class Meta:
        db_table = "branch_patient_sequences"


class Room(models.Model):
    GENERAL = "general"
    OT = "ot"
    CDRF = "cdrf"
    ROOM_TYPE_CHOICES = [(GENERAL, "General"), (OT, "Operating Theatre"), (CDRF, "CDRF")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="rooms")
    name = models.CharField(max_length=200)
    floor = models.CharField(max_length=50)
    room_type = models.CharField(max_length=16, choices=ROOM_TYPE_CHOICES, default=GENERAL)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "rooms"
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="uq_room_branch_name"),
            models.CheckConstraint(
                check=models.Q(room_type__in=[GENERAL, OT, CDRF]),
                name="ck_room_type",
            ),
        ]

    def __str__(self):
        return f"{self.branch.code} / {self.name}"


class Chair(models.Model):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    STATUS_CHOICES = [(ACTIVE, "Active"), (INACTIVE, "Inactive"), (MAINTENANCE, "Maintenance")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="chairs")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="chairs")
    code = models.CharField(max_length=32, help_text="Short label shown in the UI, e.g. 'OT-1'")
    default_buffer_minutes = models.PositiveIntegerField(default=10)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=ACTIVE)

    class Meta:
        db_table = "chairs"
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], name="uq_chair_branch_code"),
            models.CheckConstraint(
                check=models.Q(status__in=[ACTIVE, INACTIVE, MAINTENANCE]),
                name="ck_chair_status",
            ),
        ]

    def __str__(self):
        return self.code


class StaffBranch(models.Model):
    """A staff member's assignment to a branch (a user can work at more
    than one)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="branch_assignments")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="staff_assignments")

    class Meta:
        db_table = "staff_branches"
        constraints = [
            models.UniqueConstraint(fields=["user", "branch"], name="uq_staff_branch"),
        ]
