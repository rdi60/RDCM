import uuid

from django.db import models


class Procedure(models.Model):
    """Minimal procedure master for Phase 1 (booking needs duration and
    room-type requirement). Rate overrides and billing-specific fields are
    Phase 2 — see docs/ARCHITECTURE.md."""

    OT = "ot"
    CDRF = "cdrf"
    ROOM_TYPE_CHOICES = [(OT, "Operating Theatre"), (CDRF, "CDRF")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    default_duration_minutes = models.PositiveIntegerField()
    requires_room_type = models.CharField(
        max_length=16, choices=ROOM_TYPE_CHOICES, null=True, blank=True,
        help_text="NULL = any room",
    )
    default_rate = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "procedures"
        constraints = [
            models.CheckConstraint(
                check=models.Q(requires_room_type__isnull=True) | models.Q(requires_room_type__in=[OT, CDRF]),
                name="ck_procedure_room_type",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
