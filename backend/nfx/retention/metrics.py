from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class RetentionMetricsSnapshot:
    decisions: int
    eligible: int
    non_executable: int
    previews: int
    stale_previews: int
    preview_errors: int
    deletion_requested: int
    deletion_blocked: int
    deletion_failures: int
    deletion_recoveries: int
    deletion_completed: int
    deletion_orphans: int


class RetentionMetrics:
    """Bounded counters; document identifiers never become metric labels."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._values = {
            "decisions": 0,
            "eligible": 0,
            "non_executable": 0,
            "previews": 0,
            "stale_previews": 0,
            "preview_errors": 0,
            "deletion_requested": 0,
            "deletion_blocked": 0,
            "deletion_failures": 0,
            "deletion_recoveries": 0,
            "deletion_completed": 0,
            "deletion_orphans": 0,
        }

    def record_decision(self, state: str) -> None:
        with self._lock:
            self._values["decisions"] += 1
            if state == "eligible":
                self._values["eligible"] += 1
            elif state == "non_executable":
                self._values["non_executable"] += 1

    def record_preview(self, result: str) -> None:
        with self._lock:
            self._values["previews"] += 1
            if result == "stale":
                self._values["stale_previews"] += 1
            elif result != "success":
                self._values["preview_errors"] += 1

    def snapshot(self) -> RetentionMetricsSnapshot:
        with self._lock:
            return RetentionMetricsSnapshot(**self._values)

    def record_deletion(self, result: str) -> None:
        counter = {
            "requested": "deletion_requested",
            "blocked": "deletion_blocked",
            "failed": "deletion_failures",
            "recovery_required": "deletion_recoveries",
            "completed": "deletion_completed",
            "orphan": "deletion_orphans",
        }.get(result)
        if counter is None:
            return
        with self._lock:
            self._values[counter] += 1


retention_metrics = RetentionMetrics()
