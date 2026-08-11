from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ExportMetricsSnapshot:
    requests: int
    available: int
    partial: int
    failed: int
    downloads: int
    denied_downloads: int
    expired: int
    cleanups: int


class ExportMetrics:
    """Process-local bounded counters; labels never contain filters or fiscal identifiers."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._values = {
            "requests": 0,
            "available": 0,
            "partial": 0,
            "failed": 0,
            "downloads": 0,
            "denied_downloads": 0,
            "expired": 0,
            "cleanups": 0,
        }

    def record(self, action: str, result: str = "") -> None:
        key = {
            "request": "requests",
            "available": "available",
            "partial": "partial",
            "failed": "failed",
            "download": "downloads",
            "denied": "denied_downloads",
            "expired": "expired",
            "cleanup": "cleanups",
        }.get(result if action == "compose" else action)
        if key is None:
            return
        with self._lock:
            self._values[key] += 1

    def snapshot(self) -> ExportMetricsSnapshot:
        with self._lock:
            return ExportMetricsSnapshot(**self._values)


export_metrics = ExportMetrics()
