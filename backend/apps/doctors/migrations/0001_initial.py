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
            name="Doctor",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("registration_no", models.CharField(blank=True, max_length=100)),
                ("specialization", models.CharField(blank=True, max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT, related_name="doctor_profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "doctors"},
        ),
        migrations.CreateModel(
            name="Assistant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(default=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT, related_name="assistant_profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "assistants"},
        ),
        migrations.CreateModel(
            name="DoctorAvailability",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("day_of_week", models.PositiveSmallIntegerField(choices=[
                    (0, "Sunday"), (1, "Monday"), (2, "Tuesday"), (3, "Wednesday"),
                    (4, "Thursday"), (5, "Friday"), (6, "Saturday"),
                ])),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("effective_from", models.DateField()),
                ("effective_to", models.DateField(blank=True, help_text="NULL = still in effect", null=True)),
                ("branch", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="doctor_availability", to="clinic.branch",
                )),
                ("doctor", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="availability", to="doctors.doctor",
                )),
            ],
            options={"db_table": "doctor_availability"},
        ),
        migrations.CreateModel(
            name="DoctorScheduleException",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("date", models.DateField()),
                ("is_available", models.BooleanField(help_text="False = on leave that day")),
                ("start_time", models.TimeField(blank=True, help_text="NULL if unavailable all day", null=True)),
                ("end_time", models.TimeField(blank=True, null=True)),
                ("reason", models.CharField(blank=True, max_length=300)),
                ("doctor", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="schedule_exceptions", to="doctors.doctor",
                )),
            ],
            options={"db_table": "doctor_schedule_exceptions"},
        ),
        migrations.AddConstraint(
            model_name="doctoravailability",
            constraint=models.CheckConstraint(
                check=models.Q(day_of_week__gte=0) & models.Q(day_of_week__lte=6), name="ck_availability_dow",
            ),
        ),
        migrations.AddConstraint(
            model_name="doctoravailability",
            constraint=models.CheckConstraint(
                check=models.Q(end_time__gt=models.F("start_time")), name="ck_availability_time_order",
            ),
        ),
        migrations.AddConstraint(
            model_name="doctorscheduleexception",
            constraint=models.UniqueConstraint(fields=("doctor", "date"), name="uq_doctor_exception_date"),
        ),
    ]
