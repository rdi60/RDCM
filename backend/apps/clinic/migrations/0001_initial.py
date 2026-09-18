import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Branch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(help_text="Short prefix used in UHIDs, e.g. 'RDC1'", max_length=16, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("address", models.TextField(blank=True)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "branches"},
        ),
        migrations.CreateModel(
            name="BranchPatientSequence",
            fields=[
                ("branch", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    primary_key=True,
                    serialize=False,
                    to="clinic.branch",
                )),
                ("last_patient_no", models.IntegerField(default=0)),
            ],
            options={"db_table": "branch_patient_sequences"},
        ),
        migrations.CreateModel(
            name="Room",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("floor", models.CharField(max_length=50)),
                ("room_type", models.CharField(
                    choices=[("general", "General"), ("ot", "Operating Theatre"), ("cdrf", "CDRF")],
                    default="general", max_length=16,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("branch", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="rooms", to="clinic.branch",
                )),
            ],
            options={"db_table": "rooms"},
        ),
        migrations.CreateModel(
            name="Chair",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(help_text="Short label shown in the UI, e.g. 'OT-1'", max_length=32)),
                ("default_buffer_minutes", models.PositiveIntegerField(default=10)),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("inactive", "Inactive"), ("maintenance", "Maintenance")],
                    default="active", max_length=16,
                )),
                ("branch", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="chairs", to="clinic.branch",
                )),
                ("room", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="chairs", to="clinic.room",
                )),
            ],
            options={"db_table": "chairs"},
        ),
        migrations.CreateModel(
            name="StaffBranch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="staff_assignments", to="clinic.branch",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="branch_assignments",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "staff_branches"},
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.UniqueConstraint(fields=("branch", "name"), name="uq_room_branch_name"),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(
                check=models.Q(room_type__in=["general", "ot", "cdrf"]), name="ck_room_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="chair",
            constraint=models.UniqueConstraint(fields=("branch", "code"), name="uq_chair_branch_code"),
        ),
        migrations.AddConstraint(
            model_name="chair",
            constraint=models.CheckConstraint(
                check=models.Q(status__in=["active", "inactive", "maintenance"]), name="ck_chair_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="staffbranch",
            constraint=models.UniqueConstraint(fields=("user", "branch"), name="uq_staff_branch"),
        ),
    ]
