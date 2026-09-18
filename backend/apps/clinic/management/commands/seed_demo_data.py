"""
DEV/DEMO ONLY. Creates a small, fake branch/rooms/chairs/doctor/patient/
procedure set so the booking API can be smoke-tested end to end. This is
NOT the real clinic layout (15 chairs, 2 of them OT, across ground/first
floor/CDRF/OT) — the owner should enter the real rooms/chairs/doctors via
the Django admin once this is deployed, since the exact room-by-room
breakdown hasn't been confirmed yet.

Usage: python manage.py seed_demo_data
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Role, User
from apps.clinic.models import Branch, Chair, Room
from apps.doctors.models import Doctor
from apps.procedures.models import Procedure


class Command(BaseCommand):
    help = "Create a small fake dataset for local smoke-testing (not real clinic data)."

    @transaction.atomic
    def handle(self, *args, **options):
        branch, _ = Branch.objects.get_or_create(code="RDC1", defaults={"name": "Main Clinic (demo)"})

        general_room, _ = Room.objects.get_or_create(
            branch=branch, name="Room 1 (demo)", defaults={"floor": "ground", "room_type": Room.GENERAL},
        )
        ot_room, _ = Room.objects.get_or_create(
            branch=branch, name="OT 1 (demo)", defaults={"floor": "ot", "room_type": Room.OT},
        )
        chair_general, _ = Chair.objects.get_or_create(branch=branch, code="GF-1", defaults={"room": general_room})
        chair_ot, _ = Chair.objects.get_or_create(branch=branch, code="OT-1", defaults={"room": ot_room})

        receptionist_role = Role.objects.get(code=Role.RECEPTIONIST)
        doctor_role = Role.objects.get(code=Role.DOCTOR)

        if not User.objects.filter(phone="9990000001").exists():
            User.objects.create_user(phone="9990000001", name="Demo Reception", role=receptionist_role, password="demo-pass-123")

        doctor_user, created = User.objects.get_or_create(
            phone="9990000002", defaults={"name": "Dr. Demo", "role": doctor_role},
        )
        if created:
            doctor_user.set_password("demo-pass-123")
            doctor_user.save()
        doctor, _ = Doctor.objects.get_or_create(user=doctor_user)

        Procedure.objects.get_or_create(
            code="CONS", defaults={"name": "Consultation", "default_duration_minutes": 15, "default_rate": 300},
        )
        Procedure.objects.get_or_create(
            code="RCT-SITTING", defaults={"name": "RCT (per sitting)", "default_duration_minutes": 45, "default_rate": 1500},
        )
        Procedure.objects.get_or_create(
            code="MINOR-SURGERY", defaults={
                "name": "Minor oral surgery", "default_duration_minutes": 60,
                "requires_room_type": Procedure.OT, "default_rate": 5000,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded demo data: branch={branch.code}, chairs=[{chair_general.code}, {chair_ot.code}], "
            f"doctor={doctor_user.name}, reception login=9990000001 / demo-pass-123"
        ))
