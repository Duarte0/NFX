from __future__ import annotations

import threading
from datetime import UTC, datetime

import pytest
from django.db import connections
from nfx.jobs.models import JobPolicy
from nfx.jobs.policy import create_policy
from nfx.jobs.services import JobEngine


@pytest.mark.django_db(transaction=True)
def test_job_migration_installs_claim_lease_target_and_idempotency_indexes() -> None:
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'nfx_job' ORDER BY indexname"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'nfx_job'::regclass ORDER BY conname"
        )
        constraints = {row[0] for row in cursor.fetchall()}

    assert {
        "nfx_job_claim_ix",
        "nfx_job_expired_lease_ix",
        "nfx_job_target_ix",
        "nfx_job_active_idempotency_uq",
    } <= indexes
    assert {
        "nfx_job_running_lease_ck",
        "nfx_job_attempt_nonnegative_ck",
        "nfx_job_blocked_without_lease_ck",
    } <= constraints

    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'nfx_job_policy'")
        policy_indexes = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'nfx_job_policy'::regclass"
        )
        policy_constraints = {row[0] for row in cursor.fetchall()}
    assert "nfx_policy_scope_valid_ix" in policy_indexes
    assert {
        "nfx_policy_scope_version_uq",
        "nfx_policy_validity_order_ck",
        "nfx_policy_backoff_cap_ck",
        "nfx_policy_timing_values_ck",
    } <= policy_constraints


@pytest.mark.django_db(transaction=True)
def test_two_postgres_workers_cannot_claim_one_job() -> None:
    engine = JobEngine(clock=lambda: datetime(2026, 8, 6, 12, 0, tzinfo=UTC))
    engine.enqueue(
        job_type="synthetic.contention",
        logical_target="company:synthetic-contention",
        payload={"company_id": "synthetic-contention"},
        idempotency_key="synthetic-contention-key",
    )
    barrier = threading.Barrier(2)
    claims: list[str | None] = []
    failures: list[BaseException] = []

    def claim(owner: str) -> None:
        try:
            connections.close_all()
            barrier.wait()
            claimed = JobEngine().claim(owner)
            claims.append(str(claimed.id) if claimed else None)
        except BaseException as exc:  # pragma: no cover - asserted by caller
            failures.append(exc)
        finally:
            connections.close_all()

    first = threading.Thread(target=claim, args=("worker-a",))
    second = threading.Thread(target=claim, args=("worker-b",))
    first.start()
    second.start()
    first.join()
    second.join()

    assert not failures
    assert sum(value is not None for value in claims) == 1


@pytest.mark.django_db(transaction=True)
def test_policy_is_persisted_and_referenced_by_job() -> None:
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="integration",
        version=1,
        valid_from=datetime(2026, 8, 6, 12, 0, tzinfo=UTC),
        retry_limit=1,
    )
    job = JobEngine(clock=lambda: datetime(2026, 8, 6, 12, 0, tzinfo=UTC)).enqueue(
        job_type="synthetic.integration",
        logical_target="company:synthetic-integration",
        payload={"company_id": "synthetic-integration"},
        idempotency_key="synthetic-policy-integration",
        policy=policy,
    )
    stored = JobPolicy.objects.get(id=policy.id)
    assert job.effective_policy_id == stored.id
