from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nfx.backup.models import RestoreState
from nfx.backup.services import BackupService, RestoreTarget


class Command(BaseCommand):
    help = "Validates a backup in explicitly isolated local storage."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("backup_id")
        parser.add_argument("--target-root", required=True)
        parser.add_argument("--runtime-root", required=True)

    def handle(self, *args: object, **options: object) -> None:
        del args
        operation = BackupService().restore(
            str(options["backup_id"]),
            RestoreTarget(
                root=Path(str(options["target_root"])),
                runtime_root=Path(str(options["runtime_root"])),
            ),
        )
        if operation.state != RestoreState.SUCCESS:
            raise CommandError(f"Restore failed safely: {operation.safe_error or 'restore_failed'}")
        self.stdout.write(self.style.SUCCESS(f"Restore validated: {operation.id}"))
