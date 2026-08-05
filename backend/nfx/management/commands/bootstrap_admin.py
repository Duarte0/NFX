import os

from django.core.management.base import BaseCommand, CommandError

from nfx.identity.services import bootstrap_first_administrator


class Command(BaseCommand):
    help = "Idempotently creates the installation administrator from an external secret."

    def handle(self, *args: object, **options: object) -> None:
        password = os.getenv("NFX_BOOTSTRAP_ADMIN_PASSWORD")
        if not password:
            raise CommandError("NFX_BOOTSTRAP_ADMIN_PASSWORD must be supplied externally")
        _, created = bootstrap_first_administrator(password)
        self.stdout.write(self.style.SUCCESS("Bootstrap administrator created" if created else "Bootstrap administrator unchanged"))
