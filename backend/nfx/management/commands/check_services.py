from django.core.management.base import BaseCommand, CommandError

from nfx.infrastructure.dependencies import dependencies_from_environment


class Command(BaseCommand):
    help = "Checks PostgreSQL and MinIO readiness without disclosing connection details."

    def handle(self, *args: object, **options: object) -> None:
        result = dependencies_from_environment().check()
        if not result.ready:
            raise CommandError(f"Dependencies unavailable: {', '.join(result.unavailable)}")
        self.stdout.write(self.style.SUCCESS("Dependencies ready"))
