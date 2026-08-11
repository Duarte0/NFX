from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from nfx.infrastructure.dependencies import DependencyCheck
from nfx.infrastructure.http import JsonFormatter, safe_log
from nfx.jobs.observability import (
    ComponentHealth,
    HeartbeatService,
    JobMetricsSnapshot,
    OperationalHealth,
)
from nfx.jobs.services import JobEngine, run_scheduler_loop, run_worker_loop

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)


def _metrics(*, oldest_due_age_seconds: float | None = None) -> JobMetricsSnapshot:
    return JobMetricsSnapshot(
        queue_counts={"queued": 2, "running": 1, "completed": 3, "blocked": 1},
        oldest_due_age_seconds=oldest_due_age_seconds,
        claim_candidates=2,
        retrying=1,
        expired_lease_recoveries=1,
        cooldowns=1,
        blocked=1,
        outcomes={"success": 3, "temporary": 1, "cooldown": 1, "permanent": 1},
    )


def _components(*, worker: str = "ready", scheduler: str = "ready") -> dict[str, ComponentHealth]:
    return {
        "worker": ComponentHealth(worker, "worker-1", NOW, 0),
        "scheduler": ComponentHealth(scheduler, "scheduler-1", NOW, 0),
    }


def test_operational_health_reports_safe_ready_and_degraded_states() -> None:
    service = OperationalHealth(
        worker_timeout=timedelta(seconds=30),
        scheduler_timeout=timedelta(seconds=30),
        backlog_delay=timedelta(seconds=60),
    )
    ready = service.evaluate(
        DependencyCheck(True, ()), _metrics(), _components(), now=NOW
    )

    assert ready["status"] == "ready"
    assert ready["jobs"] == {
        "queue_counts": {"queued": 2, "running": 1, "completed": 3, "blocked": 1},
        "oldest_due_age_seconds": None,
        "claim_candidates": 2,
        "retrying": 1,
        "expired_lease_recoveries": 1,
        "cooldowns": 1,
        "blocked": 1,
        "outcomes": {"success": 3, "temporary": 1, "cooldown": 1, "permanent": 1},
        "status": "ready",
    }
    assert ready["capabilities"] == {
        "fiscal_sources": "unavailable",
        "disk": "unavailable",
        "backup": "unavailable",
        "documents": "unavailable",
        "quarantine": "unavailable",
        "rendering": "available",
    }

    degraded = service.evaluate(
        DependencyCheck(False, ("minio",)),
        _metrics(oldest_due_age_seconds=61),
        _components(worker="stale"),
        now=NOW,
    )
    assert degraded["status"] == "degraded"
    assert degraded["dependencies"] == {
        "postgres": "ready",
        "schema": "ready",
        "minio": "unavailable",
    }
    assert degraded["backlog"] == {"status": "delayed", "oldest_due_age_seconds": 61}


def test_operational_health_never_claims_ready_when_durable_state_is_unavailable() -> None:
    service = OperationalHealth()
    result = service.evaluate(
        DependencyCheck(False, ("postgres",)), None, None, now=NOW
    )

    assert result["status"] == "unavailable"
    assert result["jobs"]["status"] == "unavailable"
    assert result["processes"]["worker"]["status"] == "unavailable"
    assert result["dependencies"]["postgres"] == "unavailable"


def test_json_lifecycle_log_is_structured_safe_and_logging_cannot_raise() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("nfx-observability-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    safe_log(
        logger,
        "info",
        "job_finalized",
        job_id="synthetic-job",
        job_type="synthetic.handler",
        attempt=2,
        duration_ms=17,
        outcome="success",
        error_class="RuntimeError",
        secret="must-not-appear",
    )

    entry = json.loads(stream.getvalue())
    assert entry["message"] == "job_finalized"
    assert entry["job_ref"] == "synthetic-job"
    assert entry["job_type"] == "synthetic.handler"
    assert entry["attempt"] == 2
    assert entry["duration_ms"] == 17
    assert entry["outcome"] == "success"
    assert "secret" not in entry
    assert "must-not-appear" not in stream.getvalue()


def test_loop_heartbeat_is_written_after_reaching_the_service_boundary() -> None:
    class FakeHeartbeat:
        def __init__(self) -> None:
            self.calls = 0

        def beat(self) -> None:
            self.calls += 1

    class FakeEngine(JobEngine):
        def claim(self, owner: str):  # type: ignore[no-untyped-def]
            return None

        def recover(self):  # type: ignore[no-untyped-def]
            return (0, 0)

    worker_heartbeat = FakeHeartbeat()
    worker_checks = iter([True, False, False])
    run_worker_loop(
        FakeEngine(),
        owner="worker-test",
        heartbeat=worker_heartbeat,
        should_continue=lambda: next(worker_checks),
        sleep=lambda _: None,
    )
    assert worker_heartbeat.calls == 1

    scheduler_heartbeat = FakeHeartbeat()
    scheduler_checks = iter([True, False, False])
    run_scheduler_loop(
        FakeEngine(),
        heartbeat=scheduler_heartbeat,
        should_continue=lambda: next(scheduler_checks),
        sleep=lambda _: None,
    )
    assert scheduler_heartbeat.calls == 1


@pytest.mark.django_db
def test_heartbeats_are_independent_by_component_and_process() -> None:
    first = HeartbeatService(component="worker", process_id="worker-a", clock=lambda: NOW)
    second = HeartbeatService(
        component="worker", process_id="worker-b", clock=lambda: NOW - timedelta(seconds=1)
    )

    first.beat()
    second.beat()
    first.beat()

    snapshot = HeartbeatService.inspect(now=NOW, timeout=timedelta(seconds=30))

    assert snapshot["worker"].process_id == "worker-a"
    assert snapshot["worker"].status == "ready"
