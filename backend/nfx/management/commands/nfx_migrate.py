from django.core.management.base import BaseCommand

from nfx.infrastructure.schema import SchemaMigrator


class Command(BaseCommand):
    help = "Applies pending migrations under the NFX PostgreSQL advisory lock."

    def handle(self, *args: object, **options: object) -> None:
        outcome = SchemaMigrator().migrate()
        if outcome.applied:
            self.stdout.write(self.style.SUCCESS(f"Applied: {', '.join(outcome.applied)}"))
        else:
            self.stdout.write(self.style.SUCCESS("Schema already current"))
