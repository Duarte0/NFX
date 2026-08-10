from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class DocumentMetricsSnapshot:
    consultations: int
    empty_results: int
    consultation_errors: int
    downloads: int
    denied_downloads: int
    unavailable_objects: int
    download_errors: int
    consultation_latency_ms: float
    download_latency_ms: float


class DocumentMetrics:
    """Bounded in-process counters; no document identifiers become labels."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._values = {
            "consultations": 0,
            "empty_results": 0,
            "consultation_errors": 0,
            "downloads": 0,
            "denied_downloads": 0,
            "unavailable_objects": 0,
            "download_errors": 0,
            "consultation_latency_ms": 0.0,
            "download_latency_ms": 0.0,
        }

    def record(self, *, action: str, result: str, latency_ms: float) -> None:
        with self._lock:
            if action == "consultation":
                self._values["consultations"] += 1
                self._values["consultation_latency_ms"] += latency_ms
                if result == "empty":
                    self._values["empty_results"] += 1
                elif result not in {"success", "not_found"}:
                    self._values["consultation_errors"] += 1
            elif action == "download":
                self._values["downloads"] += 1
                self._values["download_latency_ms"] += latency_ms
                if result == "unavailable":
                    self._values["unavailable_objects"] += 1
                elif result == "denied":
                    self._values["denied_downloads"] += 1
                elif result != "success":
                    self._values["download_errors"] += 1

    def snapshot(self) -> DocumentMetricsSnapshot:
        with self._lock:
            return DocumentMetricsSnapshot(
                consultations=int(self._values["consultations"]),
                empty_results=int(self._values["empty_results"]),
                consultation_errors=int(self._values["consultation_errors"]),
                downloads=int(self._values["downloads"]),
                denied_downloads=int(self._values["denied_downloads"]),
                unavailable_objects=int(self._values["unavailable_objects"]),
                download_errors=int(self._values["download_errors"]),
                consultation_latency_ms=self._values["consultation_latency_ms"],
                download_latency_ms=self._values["download_latency_ms"],
            )


document_metrics = DocumentMetrics()
