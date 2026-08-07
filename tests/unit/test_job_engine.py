from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from django.db import OperationalError
from nfx.jobs.handlers import HandlerOutcome, clear_handlers, register_handler
from nfx.jobs.models import Job, JobOutcomeKind, JobState
from nfx.jobs.policy import AmbiguousPolicy, create_policy, select_policy
from nfx.jobs.services import (
    InvalidJobPayload,
    InvalidTransition,
    JobEngine,
    LeaseLost,
    process_one,
    run_scheduler_loop,
    run_worker_loop,
)


class FrozenClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


@pytest.fixture(autouse=True)
def reset_handlers() -> None:
    clear_handlers()
    yield
    clear_handlers()


@pytest.mark.django_db
def test_enqueue_is_idempotent_only_while_the_key_is_active() -> None:
    engine = JobEngine()
    first = engine.enqueue(
        job_type="synthetic.test",
        logical_target="company:synthetic-001",
        payload={"company_id": "synthetic-001"},
        idempotency_key="synthetic-key-001",
    )
    duplicate = engine.enqueue(
        job_type="synthetic.test",
        logical_target="company:synthetic-001",
        payload={"company_id": "synthetic-001"},
        idempotency_key="synthetic-key-001",
    )

    assert duplicate.id == first.id
    assert Job.objects.count() == 1

    engine.claim("worker-a")
    engine.complete(first.id, "worker-a", {"reference_id": "synthetic-result-001"})
    replacement = engine.enqueue(
        job_type="synthetic.test",
        logical_target="company:synthetic-001",
        payload={"company_id": "synthetic-001"},
        idempotency_key="synthetic-key-001",
    )

    assert replacement.id != first.id
    assert Job.objects.count() == 2


@pytest.mark.django_db
def test_claim_renew_complete_and_stale_owner_rejection_are_atomic() -> None:
    clock = FrozenClock()
    engine = JobEngine(clock=clock, lease_duration=timedelta(seconds=10))
    job = engine.enqueue(
        job_type="synthetic.test",
        logical_target="company:synthetic-002",
        payload={"company_id": "synthetic-002"},
        idempotency_key="synthetic-key-002",
        scheduled_at=clock(),
    )

    claimed = engine.claim("worker-a")
    assert claimed is not None
    assert claimed.attempt_count == 1
    assert claimed.state == JobState.RUNNING
    original_expiry = claimed.lease_expires_at

    clock.advance(5)
    renewed = engine.renew(job.id, "worker-a")
    assert renewed.lease_expires_at is not None
    assert renewed.lease_expires_at > original_expiry  # type: ignore[operator]

    with pytest.raises(LeaseLost):
        engine.complete(job.id, "worker-b", {"reference_id": "synthetic-stale"})
    assert Job.objects.get(id=job.id).state == JobState.RUNNING

    completed = engine.complete(job.id, "worker-a", {"reference_id": "synthetic-result-002"})
    assert completed.state == JobState.COMPLETED
    with pytest.raises(InvalidTransition):
        engine.renew(job.id, "worker-a")


@pytest.mark.django_db
def test_expired_lease_is_reclaimed_and_overdue_job_can_be_claimed_again() -> None:
    clock = FrozenClock()
    engine = JobEngine(clock=clock, lease_duration=timedelta(seconds=5))
    job = engine.enqueue(
        job_type="synthetic.test",
        logical_target="company:synthetic-003",
        payload={"company_id": "synthetic-003"},
        idempotency_key="synthetic-key-003",
        scheduled_at=clock(),
    )
    engine.claim("worker-a")
    clock.advance(6)

    assert engine.reclaim_expired() == 1
    recovered = Job.objects.get(id=job.id)
    assert recovered.state == JobState.QUEUED
    assert recovered.lease_owner is None
    assert engine.claim("worker-b") is not None
    with pytest.raises(LeaseLost):
        engine.complete(job.id, "worker-a", {"reference_id": "synthetic-stale"})


@pytest.mark.django_db
def test_payload_and_result_reject_secret_or_content_material() -> None:
    engine = JobEngine()
    with pytest.raises(InvalidJobPayload):
        engine.enqueue(
            job_type="synthetic.test",
            logical_target="company:synthetic-004",
            payload={"xml": "<invoice>secret</invoice>"},
            idempotency_key="synthetic-key-004",
        )

    job = engine.enqueue(
        job_type="synthetic.test",
        logical_target="company:synthetic-004",
        payload={"company_id": "synthetic-004"},
        idempotency_key="synthetic-key-005",
    )
    engine.claim("worker-a")
    with pytest.raises(InvalidJobPayload):
        engine.complete(job.id, "worker-a", {"token": "synthetic-token"})
    assert Job.objects.get(id=job.id).state == JobState.RUNNING


@pytest.mark.django_db
def test_idempotent_handler_effect_survives_worker_death_before_completion() -> None:
    clock = FrozenClock()
    engine = JobEngine(clock=clock, lease_duration=timedelta(seconds=5))
    job = engine.enqueue(
        job_type="synthetic.idempotent",
        logical_target="company:synthetic-005",
        payload={"company_id": "synthetic-005"},
        idempotency_key="synthetic-key-006",
        scheduled_at=clock(),
    )
    effects: set[str] = set()

    def handler(current: Job) -> dict[str, str]:
        effects.add(current.logical_target)
        if current.attempt_count == 1:
            raise RuntimeError("synthetic handler interruption")
        return {"reference_id": "synthetic-effect-005"}

    register_handler("synthetic.idempotent", handler)
    assert process_one(engine, owner="worker-a")
    assert Job.objects.get(id=job.id).state == JobState.QUEUED
    clock.advance(6)
    assert process_one(engine, owner="worker-b")

    assert effects == {"company:synthetic-005"}
    assert Job.objects.get(id=job.id).state == JobState.COMPLETED


def test_worker_loop_stops_gracefully_without_a_registered_handler() -> None:
    calls: list[str] = []
    iterations = iter((True, True, False))

    class FakeEngine:
        def claim(self, owner: str) -> None:
            calls.append("claim")

    run_worker_loop(
        FakeEngine(),  # type: ignore[arg-type]
        owner="synthetic-worker",
        poll_interval=0,
        should_continue=lambda: next(iterations),
        sleep=lambda _: calls.append("sleep"),
    )
    assert calls == ["claim", "sleep"]


def test_scheduler_loop_stops_without_touching_a_fiscal_handler() -> None:
    calls: list[str] = []
    iterations = iter((True, True, False))

    class FakeEngine:
        def recover(self) -> tuple[int, int]:
            calls.append("reclaim")
            return (0, 0)

    run_scheduler_loop(
        FakeEngine(),  # type: ignore[arg-type]
        poll_interval=0,
        should_continue=lambda: next(iterations),
        sleep=lambda _: calls.append("sleep"),
    )
    assert calls == ["reclaim", "sleep"]


def test_database_error_does_not_report_unsafe_progress() -> None:
    class BrokenEngine:
        def claim(self, owner: str) -> Job | None:
            raise OperationalError("synthetic database unavailable")

    assert process_one(BrokenEngine(), owner="worker-a") is False  # type: ignore[arg-type]


@pytest.mark.django_db
def test_policy_selection_prefers_exact_scope_and_rejects_ambiguous_validity() -> None:
    clock = FrozenClock()
    create_policy(
        source_scope="*",
        flow_scope="received",
        version=1,
        valid_from=clock(),
    )
    exact = create_policy(
        source_scope="synthetic",
        flow_scope="received",
        version=1,
        valid_from=clock(),
    )
    assert select_policy(source="synthetic", flow="received", at=clock()).id == exact.id

    create_policy(
        source_scope="synthetic",
        flow_scope="issued",
        version=1,
        valid_from=clock(),
    )
    create_policy(
        source_scope="synthetic",
        flow_scope="issued",
        version=2,
        valid_from=clock(),
    )
    with pytest.raises(AmbiguousPolicy):
        select_policy(source="synthetic", flow="issued", at=clock())


@pytest.mark.django_db
def test_temporary_and_partial_outcomes_use_capped_deterministic_backoff() -> None:
    clock = FrozenClock()
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="retry",
        version=1,
        valid_from=clock(),
        retry_limit=2,
        backoff_initial_seconds=10,
        backoff_cap_seconds=15,
        jitter_seconds=3,
    )
    engine = JobEngine(clock=clock, jitter_source=lambda _: 2)
    job = engine.enqueue(
        job_type="synthetic.policy",
        logical_target="company:synthetic-policy",
        payload={"company_id": "synthetic-policy"},
        idempotency_key="synthetic-policy-key",
        policy=policy,
    )

    assert engine.claim("worker-a") is not None
    retried = engine.finalize(job.id, "worker-a", HandlerOutcome.temporary())
    assert retried.state == JobState.QUEUED
    assert retried.last_outcome == JobOutcomeKind.TEMPORARY
    assert retried.scheduled_at == clock() + timedelta(seconds=12)

    clock.advance(12)
    assert engine.claim("worker-a") is not None
    retried_again = engine.finalize(job.id, "worker-a", HandlerOutcome.partial())
    assert retried_again.scheduled_at == clock() + timedelta(seconds=15)

    clock.advance(15)
    assert engine.claim("worker-a") is not None
    exhausted = engine.finalize(job.id, "worker-a", HandlerOutcome.temporary())
    assert exhausted.state == JobState.BLOCKED
    assert exhausted.blocked_reason == "retry_exhausted"


@pytest.mark.django_db
def test_cooldown_precedes_local_backoff_and_permanent_outcome_blocks() -> None:
    clock = FrozenClock()
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="cooldown",
        version=1,
        valid_from=clock(),
        retry_limit=3,
        backoff_initial_seconds=1,
        cooldown_seconds=5,
    )
    engine = JobEngine(clock=clock)
    job = engine.enqueue(
        job_type="synthetic.policy",
        logical_target="company:synthetic-cooldown",
        payload={"company_id": "synthetic-cooldown"},
        idempotency_key="synthetic-cooldown-key",
        policy=policy,
    )
    engine.claim("worker-a")
    official_deadline = clock() + timedelta(seconds=30)
    cooldown = engine.finalize(
        job.id,
        "worker-a",
        HandlerOutcome.cooldown(cooldown_until=official_deadline),
    )
    assert cooldown.state == JobState.QUEUED
    assert cooldown.scheduled_at == official_deadline
    assert cooldown.cooldown_until == official_deadline

    clock.advance(30)
    engine.claim("worker-a")
    blocked = engine.finalize(
        job.id,
        "worker-a",
        HandlerOutcome.permanent(error_code="certificate_invalid"),
    )
    assert blocked.state == JobState.BLOCKED
    assert blocked.lease_owner is None
    assert blocked.safe_error == "certificate_invalid"


@pytest.mark.django_db
def test_policy_configured_cooldown_is_used_when_handler_has_no_deadline() -> None:
    clock = FrozenClock()
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="configured-cooldown",
        version=1,
        valid_from=clock(),
        cooldown_seconds=45,
    )
    engine = JobEngine(clock=clock)
    job = engine.enqueue(
        job_type="synthetic.policy",
        logical_target="company:synthetic-configured-cooldown",
        payload={"company_id": "synthetic-configured-cooldown"},
        idempotency_key="synthetic-configured-cooldown-key",
        policy=policy,
    )

    engine.claim("worker-a")
    retried = engine.finalize(job.id, "worker-a", HandlerOutcome.cooldown())

    assert retried.state == JobState.QUEUED
    assert retried.scheduled_at == clock() + timedelta(seconds=45)
    assert retried.cooldown_until == retried.scheduled_at


@pytest.mark.django_db
def test_effective_policy_cannot_change_after_job_is_scheduled() -> None:
    clock = FrozenClock()
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="immutable",
        version=1,
        valid_from=clock(),
        retry_limit=1,
    )
    engine = JobEngine(clock=clock)
    job = engine.enqueue(
        job_type="synthetic.policy",
        logical_target="company:synthetic-immutable",
        payload={"company_id": "synthetic-immutable"},
        idempotency_key="synthetic-immutable-key",
        policy=policy,
    )

    policy.retry_limit = 99
    with pytest.raises(ValueError, match="immutable"):
        policy.save()

    replacement = create_policy(
        source_scope="synthetic",
        flow_scope="immutable-replacement",
        version=1,
        valid_from=clock(),
    )
    job.effective_policy = replacement
    with pytest.raises(ValueError, match="effective job policies are immutable"):
        job.save()

    job.refresh_from_db()
    assert job.effective_policy_id == policy.id
    assert Job.objects.get(id=job.id).effective_policy.retry_limit == 1


@pytest.mark.django_db
def test_policy_job_handler_outcome_is_applied_by_worker() -> None:
    clock = FrozenClock()
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="handler",
        version=1,
        valid_from=clock(),
        retry_limit=1,
        backoff_initial_seconds=1,
    )
    engine = JobEngine(clock=clock)
    job = engine.enqueue(
        job_type="synthetic.classified",
        logical_target="company:synthetic-handler",
        payload={"company_id": "synthetic-handler"},
        idempotency_key="synthetic-handler-key",
        policy=policy,
    )
    register_handler(
        "synthetic.classified",
        lambda _: HandlerOutcome.permanent(error_code="authorization_required"),
    )

    assert process_one(engine, owner="worker-a")
    stored = Job.objects.get(id=job.id)
    assert stored.state == JobState.BLOCKED
    assert stored.last_outcome == JobOutcomeKind.PERMANENT
