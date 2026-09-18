import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("clinic", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Patient",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("uhid", models.CharField(
                    help_text="Clinic-facing patient number, sequential per branch", max_length=32, unique=True,
                )),
                ("name", models.CharField(max_length=200)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("gender", models.CharField(
                    blank=True, choices=[("male", "Male"), ("female", "Female"), ("other", "Other")], max_length=10,
                )),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("address", models.TextField(blank=True)),
                ("referred_by", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("merged", "Merged")], default="active", max_length=10,
                )),
                ("created_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="+", to=settings.AUTH_USER_MODEL,
                )),
                ("merged_into", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="absorbed_duplicates", to="patients.patient",
                )),
                ("registered_at_branch", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="patients_registered", to="clinic.branch",
                )),
            ],
            options={"db_table": "patients"},
        ),
        migrations.CreateModel(
            name="PatientMerge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("reason", models.TextField()),
                ("merged_at", models.DateTimeField(auto_now_add=True)),
                ("merged_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL,
                )),
                ("source_patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="merge_as_source", to="patients.patient",
                )),
                ("target_patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="merge_as_target", to="patients.patient",
                )),
            ],
            options={"db_table": "patient_merges"},
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(fields=["phone"], name="patients_phone_idx"),
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(fields=["name"], name="patients_name_idx"),
        ),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.CheckConstraint(
                check=models.Q(status="active") | models.Q(merged_into__isnull=False),
                name="ck_patient_merged_has_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="patientmerge",
            constraint=models.CheckConstraint(
                check=~models.Q(source_patient=models.F("target_patient")), name="ck_merge_source_ne_target",
            ),
        ),
    ]
