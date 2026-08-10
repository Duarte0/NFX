from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from nfx.backup.models import BackupKind, BackupSet, BackupState
from nfx.backup.services import select_retention


def test_retention_is_independent_for_the_three_schedules() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    backups = []
    for kind, count in ((BackupKind.DAILY, 8), (BackupKind.WEEKLY, 5), (BackupKind.MONTHLY, 13)):
        for index in range(count):
            backups.append(
                BackupSet(
                    id=uuid4(),
                    kind=kind,
                    state=BackupState.COMPLETE,
                    started_at=start + timedelta(days=index),
                )
            )

    selection = select_retention(backups)

    assert len(selection.keep) == 7 + 4 + 12
    assert len(selection.expire) == 3
