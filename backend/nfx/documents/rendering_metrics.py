from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, cast


@dataclass(frozen=True)
class RenderingMetricsSnapshot:
    requests: int
    denied: int
    reused: int
    queued: int
    started: int
    succeeded: int
    failed: int
    regenerated: int
    downloads: int
    failures: int
    duration_ms: float


class RenderingMetrics:
    """Bounded process-local counters without document or object identifiers."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._values = {
            "requests": 0,
            "denied": 0,
            "reused": 0,
            "queued": 0,
            "started": 0,
            "succeeded": 0,
            "failed": 0,
            "regenerated": 0,
            "downloads": 0,
            "failures": 0,
            "duration_ms": 0.0,
        }

    def record(self, event: str, *, duration_ms: float = 0.0) -> None:
        key = {
            "request": "requests",
            "denied": "denied",
            "reuse": "reused",
            "queued": "queued",
            "start": "started",
            "success": "succeeded",
            "failure": "failed",
            "regeneration": "regenerated",
            "download": "downloads",
        }.get(event)
        if key is None:
            return
        with self._lock:
            self._values[key] += 1
            if event in {"success", "failure"}:
                self._values["duration_ms"] += max(0.0, min(duration_ms, 86_400_000.0))
            if event == "failure":
                self._values["failures"] += 1

    def snapshot(self) -> RenderingMetricsSnapshot:
        with self._lock:
            return RenderingMetricsSnapshot(**cast(dict[str, Any], self._values))


rendering_metrics = RenderingMetrics()
