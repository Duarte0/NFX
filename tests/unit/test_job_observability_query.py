from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from django.http import QueryDict
from nfx.jobs.observability import (
    InvalidJobObservabilityQuery,
    JobObservabilityFilter,
    job_observability_summary,
    normalize_job_observability_query,
)


def test_job_observability_query_requires_one_allowlisted_filter_and_bounded_period() -> None:
    selected = normalize_job_observability_query(
        QueryDict("from=2026-08-01&to=2026-09-01&filter=failed")
    )

    assert selected == JobObservabilityFilter(
        start=selected.start,
        end=selected.end,
        filter_name="failed",
    )
    assert selected.start.isoformat() == "2026-08-01"
    assert selected.end.isoformat() == "2026-09-01"
    assert selected.boundary == "[from,to)"


@pytest.mark.parametrize(
    "query",
    [
        "from=2026-08-01&to=2026-09-01",
        "from=2026-08-01&to=2026-09-01&filter=unknown",
        "from=2026-09-01&to=2026-08-01&filter=pending",
        "from=2025-01-01&to=2026-01-03&filter=pending",
        "from=2026-08-01&from=2026-08-02&to=2026-09-01&filter=pending",
        "from=2026-08-01&to=2026-09-01&filter=pending&extra=value",
    ],
)
def test_job_observability_query_rejects_ambiguous_or_unbounded_input(query: str) -> None:
    with pytest.raises(InvalidJobObservabilityQuery):
        normalize_job_observability_query(QueryDict(query))


def test_job_observability_summary_exposes_only_safe_bounded_fields() -> None:
    created_at = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    row = SimpleNamespace(
        id="job-1",
        job_type="synthetic.handler",
        state="blocked",
        last_outcome="permanent",
        created_at=created_at,
        scheduled_at=created_at,
        last_attempt_at=created_at,
        completed_at=None,
        attempt_count=2,
        safe_error="provider-secret-token",
        payload={"secret": "must-not-leak"},
        logical_target="document:must-not-leak",
        lease_owner="worker-secret",
        effective_policy_id="policy-secret",
    )

    summary = job_observability_summary(row)

    assert summary == {
        "id": "job-1",
        "job_type": "synthetic.handler",
        "state": "blocked",
        "outcome": "permanent",
        "created_at": created_at.isoformat(),
        "scheduled_at": created_at.isoformat(),
        "last_attempt_at": created_at.isoformat(),
        "completed_at": None,
        "attempt_count": 2,
        "safe_error": "",
    }
    assert "must-not-leak" not in str(summary)
    assert "worker-secret" not in str(summary)
