import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("clinic", "0001_initial"),
        ("doctors", "0001_initial"),
        ("patients", "0001_initial"),
        ("procedures", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TreatmentPlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(help_text="e.g. 'RCT - tooth 36'", max_length=300)),
                ("planned_sittings", models.PositiveIntegerField(default=1)),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("completed", "Completed"), ("abandoned", "Abandoned")],
                    default="active", max_length=16,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("doctor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="treatment_plans", to="doctors.doctor",
                )),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="treatment_plans", to="patients.patient",
                )),
            ],
            options={"db_table": "treatment_plans"},
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("buffer_minutes", models.PositiveIntegerField(default=10)),
                ("blocked_until", models.DateTimeField(editable=False)),
                ("status", models.CharField(choices=[
                    ("scheduled", "Scheduled"), ("checked_in", "Checked in"), ("in_progress", "In progress"),
                    ("completed", "Completed"), ("cancelled", "Cancelled"), ("no_show", "No-show"),
                ], default="scheduled", max_length=16)),
                ("booking_type", models.CharField(choices=[
                    ("regular", "Regular"), ("walk_in", "Walk-in"), ("emergency", "Emergency"),
                ], default="regular", max_length=16)),
                ("notes", models.TextField(blank=True)),
                ("cancelled_reason", models.TextField(blank=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("branch", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="clinic.branch",
                )),
                ("cancelled_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="+", to=settings.AUTH_USER_MODEL,
                )),
                ("chair", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="clinic.chair",
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL,
                )),
                ("doctor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="doctors.doctor",
                )),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="patients.patient",
                )),
                ("treatment_plan", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="visits", to="scheduling.treatmentplan",
                )),
            ],
            options={"db_table": "appointments"},
        ),
        migrations.CreateModel(
            name="AppointmentProcedure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tooth_numbers", models.JSONField(blank=True, default=list, help_text="FDI notation, e.g. ['36']")),
                ("appointment", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="appointment_procedures",
                    to="scheduling.appointment",
                )),
                ("procedure", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="+", to="procedures.procedure",
                )),
            ],
            options={"db_table": "appointment_procedures"},
        ),
        migrations.CreateModel(
            name="AppointmentAssistant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("appointment", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="assistant_links",
                    to="scheduling.appointment",
                )),
                ("assistant", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="+", to="doctors.assistant",
                )),
            ],
            options={"db_table": "appointment_assistants"},
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["branch", "start_time"], name="idx_appt_branch_start"),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["doctor", "start_time"], name="idx_appt_doctor_start"),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["chair", "start_time"], name="idx_appt_chair_start"),
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.CheckConstraint(
                check=models.Q(end_time__gt=models.F("start_time")), name="ck_appointment_time_order",
            ),
        ),
        migrations.AddConstraint(
            model_name="appointmentassistant",
            constraint=models.UniqueConstraint(fields=("appointment", "assistant"), name="uq_appointment_assistant"),
        ),
    ]
