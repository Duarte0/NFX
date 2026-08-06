from __future__ import annotations

import threading
from datetime import UTC, datetime

import pytest
from django.db import connections

from nfx.jobs.services import JobEngine


@pytest.mark.django_db(transaction=True)
def test_job_migration_installs_claim_lease_target_and_idempotency_indexes() -> None:
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'nfx_job' ORDER BY indexname")
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
    } <= constraints


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
