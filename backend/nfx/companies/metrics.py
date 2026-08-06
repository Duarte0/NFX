from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from threading import Lock

from django.db.models import Count

from nfx.companies.models import Company, CompanyFlow, CompanyStatus, FlowState


@dataclass(frozen=True)
class CompanyMetricsSnapshot:
    enrichment_results: dict[str, int]
    enrichment_total_duration_ms: float
    companies_by_status: dict[str, int]
    paused_flows: int


class CompanyMetrics:
    """Small process metrics port; P3 can replace the sink without changing domain calls."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._enrichment_results: Counter[str] = Counter()
        self._enrichment_duration_ms = 0.0

    def record_enrichment(self, status: str, duration_ms: float) -> None:
        with self._lock:
            self._enrichment_results[status] += 1
            self._enrichment_duration_ms += duration_ms

    def snapshot(self) -> CompanyMetricsSnapshot:
        with self._lock:
            results = dict(self._enrichment_results)
            duration = self._enrichment_duration_ms
        counts = Company.objects.values("status").annotate(total=Count("id"))
        by_status = {status: 0 for status, _ in CompanyStatus.choices}
        by_status.update({row["status"]: row["total"] for row in counts})
        return CompanyMetricsSnapshot(
            enrichment_results=results,
            enrichment_total_duration_ms=duration,
            companies_by_status=by_status,
            paused_flows=CompanyFlow.objects.filter(state=FlowState.PAUSED).count(),
        )


company_metrics = CompanyMetrics()
