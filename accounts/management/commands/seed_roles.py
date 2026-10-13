from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

# Phase 0 only creates the groups themselves. Per-module permissions
# (e.g. "can_void_invoice", "can_manage_inventory") are attached to these
# groups as each module (billing, inventory, ...) is built, via migrations
# in that app — keeping each module responsible for its own access rules.
DEFAULT_ROLES = [
    "Clinic Admin",
    "Doctor",
    "Receptionist",
    "Accountant",
    "Nurse/Assistant",
]


class Command(BaseCommand):
    help = "Create the clinic's default role groups (idempotent)."

    def handle(self, *args, **options):
        for name in DEFAULT_ROLES:
            group, created = Group.objects.get_or_create(name=name)
            status = "created" if created else "already exists"
            self.stdout.write(f"{name}: {status}")
