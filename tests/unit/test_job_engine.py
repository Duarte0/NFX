from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from django.db import OperationalError

from nfx.jobs.handlers import clear_handlers, register_handler
from nfx.jobs.models import Job, JobState
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
