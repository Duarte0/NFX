import os

from django.core.management.base import BaseCommand, CommandError

from nfx.identity.services import bootstrap_first_administrator


class Command(BaseCommand):
    help = "Idempotently creates the installation administrator from an external secret."

    def handle(self, *args: object, **options: object) -> None:
        password = os.getenv("NFX_BOOTSTRAP_ADMIN_PASSWORD")
        if password is None or not password.strip() or "CHANGE_ME" in password:
            raise CommandError("Invalid bootstrap configuration: NFX_BOOTSTRAP_ADMIN_PASSWORD")
        try:
            _, created = bootstrap_first_administrator(password)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(
            self.style.SUCCESS(
                "Bootstrap administrator created"
                if created
                else "Bootstrap administrator unchanged"
            )
        )
