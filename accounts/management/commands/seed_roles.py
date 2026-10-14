from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

# Phase 0 only created the groups themselves. This now also assigns each
# group Django's built-in per-model permissions (view/add/change/delete),
# on the "minimum necessary" principle HIPAA's Privacy Rule expects:
# every role gets only the access its job requires, nothing more. Doctor
# etc. don't need delete rights at all — nothing below grants them to
# anyone but Clinic Admin.
DEFAULT_ROLES = [
    "Clinic Admin",
    "Doctor",
    "Receptionist",
    "Accountant",
    "Nurse/Assistant",
]

# (app_label, model_name) -> permission actions, per group. "Clinic Admin"
# is handled separately below: it gets every permission that exists on
# every model in this map (plus the master-data models), full stop.
ROLE_MODEL_PERMS = {
    "Doctor": [
        ("clinic", "doctor", ["view"]),
        ("clinic", "resource", ["view"]),
        ("clinic", "treatment", ["view"]),
        ("clinic", "specialty", ["view"]),
        ("scheduling", "patient", ["view", "change"]),
        ("scheduling", "appointment", ["view", "change"]),
        ("billing", "invoice", ["view"]),
        ("billing", "invoicelineitem", ["view"]),
        ("billing", "payment", ["view"]),
        ("inventory", "item", ["view"]),
        ("inventory", "stockbatch", ["view"]),
        ("inventory", "stocktransaction", ["view", "add"]),
    ],
    "Receptionist": [
        ("clinic", "doctor", ["view"]),
        ("clinic", "resource", ["view"]),
        ("clinic", "treatment", ["view"]),
        ("clinic", "specialty", ["view"]),
        ("scheduling", "patient", ["view", "add", "change"]),
        ("scheduling", "appointment", ["view", "add", "change"]),
        ("billing", "invoice", ["view", "add", "change"]),
        ("billing", "invoicelineitem", ["view", "add", "change", "delete"]),
        ("billing", "payment", ["view", "add"]),
    ],
    "Accountant": [
        ("scheduling", "patient", ["view"]),
        ("scheduling", "appointment", ["view"]),
        ("billing", "invoice", ["view", "add", "change", "delete"]),
        ("billing", "invoicelineitem", ["view", "add", "change", "delete"]),
        ("billing", "payment", ["view", "add", "change", "delete"]),
        ("inventory", "supplier", ["view"]),
        ("inventory", "item", ["view"]),
        ("inventory", "stockbatch", ["view"]),
        ("inventory", "stocktransaction", ["view"]),
        ("inventory", "purchaseorder", ["view"]),
        ("inventory", "purchaseorderline", ["view"]),
        ("inventory", "goodsreceiptnote", ["view"]),
        ("inventory", "goodsreceiptline", ["view"]),
    ],
    "Nurse/Assistant": [
        ("clinic", "doctor", ["view"]),
        ("clinic", "resource", ["view"]),
        ("clinic", "treatment", ["view"]),
        ("scheduling", "patient", ["view"]),
        ("scheduling", "appointment", ["view", "change"]),
        ("inventory", "item", ["view"]),
        ("inventory", "stockbatch", ["view"]),
        ("inventory", "stocklocation", ["view"]),
        ("inventory", "stocktransaction", ["view", "add"]),
        ("inventory", "stocktransfer", ["view", "add"]),
        ("inventory", "purchaseorder", ["view"]),
    ],
}

# Every model Clinic Admin's blanket grant covers (tracked + master data).
ALL_MODELS = [
    ("clinic", "specialty"),
    ("clinic", "doctor"),
    ("clinic", "doctorqualification"),
    ("clinic", "resource"),
    ("clinic", "treatment"),
    ("scheduling", "patient"),
    ("scheduling", "appointment"),
    ("billing", "invoice"),
    ("billing", "invoicelineitem"),
    ("billing", "payment"),
    ("inventory", "supplier"),
    ("inventory", "stocklocation"),
    ("inventory", "item"),
    ("inventory", "stockbatch"),
    ("inventory", "stocktransaction"),
    ("inventory", "purchaseorder"),
    ("inventory", "purchaseorderline"),
    ("inventory", "goodsreceiptnote"),
    ("inventory", "goodsreceiptline"),
    ("inventory", "stocktransfer"),
]


def _permissions_for(app_label, model_name, actions):
    try:
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
    except ContentType.DoesNotExist:
        return Permission.objects.none()
    codenames = [f"{action}_{model_name}" for action in actions]
    return Permission.objects.filter(content_type=ct, codename__in=codenames)


class Command(BaseCommand):
    help = "Create the clinic's default role groups and assign their permissions (idempotent)."

    def handle(self, *args, **options):
        groups = {}
        for name in DEFAULT_ROLES:
            group, created = Group.objects.get_or_create(name=name)
            groups[name] = group
            status = "created" if created else "already exists"
            self.stdout.write(f"{name}: {status}")

        admin_group = groups["Clinic Admin"]
        admin_perms = []
        for app_label, model_name in ALL_MODELS:
            admin_perms.extend(_permissions_for(app_label, model_name, ["view", "add", "change", "delete"]))
        admin_group.permissions.set(admin_perms)
        self.stdout.write(f"Clinic Admin: {len(admin_perms)} permissions assigned")

        for role_name, model_perms in ROLE_MODEL_PERMS.items():
            group = groups[role_name]
            perms = []
            for app_label, model_name, actions in model_perms:
                perms.extend(_permissions_for(app_label, model_name, actions))
            group.permissions.set(perms)
            self.stdout.write(f"{role_name}: {len(perms)} permissions assigned")
