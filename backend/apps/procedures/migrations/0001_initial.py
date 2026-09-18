import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Procedure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("category", models.CharField(blank=True, max_length=100)),
                ("default_duration_minutes", models.PositiveIntegerField()),
                ("requires_room_type", models.CharField(
                    blank=True,
                    choices=[("ot", "Operating Theatre"), ("cdrf", "CDRF")],
                    help_text="NULL = any room", max_length=16, null=True,
                )),
                ("default_rate", models.DecimalField(decimal_places=2, max_digits=10)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "procedures"},
        ),
        migrations.AddConstraint(
            model_name="procedure",
            constraint=models.CheckConstraint(
                check=models.Q(("requires_room_type__isnull", True)) | models.Q(requires_room_type__in=["ot", "cdrf"]),
                name="ck_procedure_room_type",
            ),
        ),
    ]
