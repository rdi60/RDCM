from django.core.management.base import BaseCommand

from library.models import Topic


class Command(BaseCommand):
    help = "Seed a few starter topics so a fresh install isn't empty."

    def handle(self, *args, **options):
        defaults = [
            ("Patients", "#4f46e5"),
            ("Billing", "#16a34a"),
            ("Marketing", "#db2777"),
            ("Admin", "#ea580c"),
        ]
        for name, color in defaults:
            topic, created = Topic.objects.get_or_create(name=name, defaults={"color": color})
            if created:
                self.stdout.write(f"Created topic: {name}")
        self.stdout.write(self.style.SUCCESS("Done."))
