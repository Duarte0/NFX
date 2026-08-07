from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from nfx.jobs.models import Job, JobOutcomeKind, JobState
from nfx.jobs.observability import JobObservability


@pytest.mark.django_db
def test_job_metrics_aggregate_safe_durable_states_without_mutating_jobs() -> None:
    now = timezone.now()
    Job.objects.create(
        job_type="synthetic.handler",
        logical_target="target-queued",
        payload={"reference": "queued"},
        idempotency_key="metrics-queued",
        scheduled_at=now - timedelta(seconds=90),
        attempt_count=2,
        safe_error="lease_expired",
    )
    Job.objects.create(
        job_type="synthetic.handler",
        logical_target="target-running",
        payload={"reference": "running"},
        idempotency_key="metrics-running",
        scheduled_at=now,
        state=JobState.RUNNING,
        lease_owner="worker-synthetic",
        lease_issued_at=now - timedelta(seconds=10),
        lease_expires_at=now - timedelta(seconds=1),
        attempt_count=1,
    )
    Job.objects.create(
        job_type="synthetic.handler",
        logical_target="target-cooldown",
        payload={"reference": "cooldown"},
        idempotency_key="metrics-cooldown",
        scheduled_at=now + timedelta(seconds=30),
        cooldown_until=now + timedelta(seconds=30),
        attempt_count=1,
        last_outcome=JobOutcomeKind.COOLDOWN,
    )
    Job.objects.create(
        job_type="synthetic.handler",
        logical_target="target-completed",
        payload={"reference": "completed"},
        idempotency_key="metrics-completed",
        scheduled_at=now,
        state=JobState.COMPLETED,
        last_outcome=JobOutcomeKind.SUCCESS,
    )
    Job.objects.create(
        job_type="synthetic.handler",
        logical_target="target-blocked",
        payload={"reference": "blocked"},
        idempotency_key="metrics-blocked",
        scheduled_at=now,
        state=JobState.BLOCKED,
        last_outcome=JobOutcomeKind.PERMANENT,
        blocked_at=now,
        blocked_reason="synthetic_block",
    )

    before = list(Job.objects.values_list("id", "state", "attempt_count"))
    snapshot = JobObservability(clock=lambda: now).snapshot()
    after = list(Job.objects.values_list("id", "state", "attempt_count"))

    assert snapshot.queue_counts == {"queued": 2, "running": 1, "completed": 1, "blocked": 1}
    assert snapshot.oldest_due_age_seconds == pytest.approx(90, abs=1)
    assert snapshot.claim_candidates == 2
    assert snapshot.retrying == 2
    assert snapshot.expired_lease_recoveries == 2
    assert snapshot.cooldowns == 1
    assert snapshot.blocked == 1
    assert snapshot.outcomes[JobOutcomeKind.SUCCESS] == 1
    assert snapshot.outcomes[JobOutcomeKind.COOLDOWN] == 1
    assert snapshot.outcomes[JobOutcomeKind.PERMANENT] == 1
    assert before == after
