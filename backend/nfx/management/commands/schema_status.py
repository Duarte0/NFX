from django.core.management.base import BaseCommand, CommandError

from nfx.infrastructure.schema import schema_status


class Command(BaseCommand):
    help = "Reports whether the database schema matches this NFX application version."

    def handle(self, *args: object, **options: object) -> None:
        status = schema_status()
        if status.compatible:
            version = status.required[-1] if status.required else "none"
            self.stdout.write(self.style.SUCCESS(f"Schema compatible: {version}"))
            return
        if status.missing:
            self.stderr.write(f"Schema missing migrations: {', '.join(status.missing)}")
        if status.unexpected:
            self.stderr.write(f"Schema incompatible migrations: {', '.join(status.unexpected)}")
        raise CommandError("Database schema is incompatible")
