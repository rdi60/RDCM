from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    HIPAA Security Rule audit-controls record (45 CFR 164.312(b)): who did
    what, to which record, when, and from where. Rows are created only by
    audit.signals (on model writes and auth events) and audit.utils.log_view
    (on reads of PHI detail pages) — never edited or deleted through the
    app, including by admins (see AuditLogAdmin).
    """

    class Action(models.TextChoices):
        VIEW = "view", "Viewed"
        CREATE = "create", "Created"
        UPDATE = "update", "Updated"
        DELETE = "delete", "Deleted"
        LOGIN = "login", "Logged in"
        LOGIN_FAILED = "login_failed", "Login failed"
        LOGOUT = "logout", "Logged out"

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    username_attempted = models.CharField(
        max_length=150, blank=True, help_text="Set only for login_failed, where there may be no User to link."
    )
    action = models.CharField(max_length=15, choices=Action.choices)
    model_name = models.CharField(max_length=100, blank=True, help_text="e.g. scheduling.patient")
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        who = self.user or self.username_attempted or "anonymous"
        return f"{who} {self.action} {self.model_name} {self.object_id}".strip()
