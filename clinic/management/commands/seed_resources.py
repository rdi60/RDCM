from django.core.management.base import BaseCommand

from clinic.models import Resource


class Command(BaseCommand):
    help = "Create the clinic's chairs and OTs (idempotent). Defaults match your 16 chairs + 2 OTs."

    def add_arguments(self, parser):
        parser.add_argument("--chairs", type=int, default=16, help="Number of chairs to ensure exist.")
        parser.add_argument("--ots", type=int, default=2, help="Number of OTs to ensure exist.")

    def handle(self, *args, **options):
        for i in range(1, options["chairs"] + 1):
            self._ensure(Resource.ResourceType.CHAIR, f"Chair {i}", i)
        for i in range(1, options["ots"] + 1):
            self._ensure(Resource.ResourceType.OT, f"OT {i}", i)

    def _ensure(self, resource_type, name, number):
        resource, created = Resource.objects.get_or_create(
            type=resource_type, name=name, defaults={"number": number}
        )
        if not created and resource.number != number:
            resource.number = number
            resource.save(update_fields=["number"])
        status = "created" if created else "already exists"
        self.stdout.write(f"{name}: {status}")
