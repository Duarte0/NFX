from __future__ import annotations

from argparse import ArgumentParser

from django.core.management.base import BaseCommand, CommandError

from nfx.backup.models import BackupState
from nfx.backup.services import BackupError, BackupService


class Command(BaseCommand):
    help = "Creates a verified local NFX backup without exposing secrets."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--kind", choices=("daily", "weekly", "monthly"), default="daily")
        parser.add_argument("--idempotency-key", default="")

    def handle(self, *args: object, **options: object) -> None:
        del args
        try:
            result = BackupService().create_backup(
                str(options["kind"]), idempotency_key=str(options["idempotency_key"])
            )
        except BackupError as exc:
            raise CommandError("Backup failed safely") from exc
        if result.state != BackupState.COMPLETE:
            raise CommandError(f"Backup failed safely: {result.safe_error or 'capture_failed'}")
        self.stdout.write(self.style.SUCCESS(f"Backup complete: {result.id}"))
