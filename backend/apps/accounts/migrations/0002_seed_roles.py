from django.db import migrations

ROLE_CODES = [
    "owner",
    "admin",
    "doctor",
    "receptionist",
    "dental_assistant",
    "lab_technician",
    "accountant",
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code in ROLE_CODES:
        Role.objects.get_or_create(code=code)


def unseed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(code__in=ROLE_CODES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
