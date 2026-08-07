from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from nfx.adapters.simulation import (
    FiscalFamily,
    NFeSimulator,
    ScenarioName,
    build_scenario,
    make_simulator_handler,
)
from nfx.jobs.handlers import clear_handlers, register_handler
from nfx.jobs.models import Job
from nfx.jobs.services import JobEngine, process_one


class FrozenClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value


@pytest.fixture(autouse=True)
def reset_handlers() -> Iterator[None]:
    clear_handlers()
    yield
    clear_handlers()


@pytest.mark.django_db
def test_synthetic_handler_replays_after_interruption_without_duplicate_effect() -> None:
    clock = FrozenClock()
    engine = JobEngine(clock=clock, lease_duration=timedelta(seconds=5))
    job = engine.enqueue(
        job_type="synthetic.fiscal",
        logical_target="company:synthetic-001",
        payload={
            "source": "synthetic",
            "family": "nfe",
            "actor": "actor:synthetic-001",
            "flow": "received",
            "policy_reference": "policy:synthetic-v1",
            "certificate_handle": "certificate:synthetic-001",
            "correlation_id": "correlation:synthetic-001",
        },
        idempotency_key="synthetic-fiscal-restart-001",
        scheduled_at=clock(),
    )
    effects: set[str] = set()
    first_adapter = NFeSimulator(
        build_scenario(ScenarioName.INTERRUPTION_RESTART, FiscalFamily.NFE, seed=43)
    )

    def interrupted_handler(current: Job) -> None:
        make_simulator_handler(first_adapter)(current)
        effects.add(current.logical_target)
        raise RuntimeError("synthetic interruption")

    register_handler("synthetic.fiscal", interrupted_handler)
    assert process_one(engine, owner="worker-a")
    assert Job.objects.get(id=job.id).state == "queued"

    restarted_adapter = NFeSimulator(
        build_scenario(ScenarioName.INTERRUPTION_RESTART, FiscalFamily.NFE, seed=43)
    )
    register_handler("synthetic.fiscal", make_simulator_handler(restarted_adapter))
    assert process_one(engine, owner="worker-b")

    stored = Job.objects.get(id=job.id)
    assert stored.state == "completed"
    assert stored.safe_result == {
        "outcome": "success",
        "unit_count": 1,
        "next_cursor": "cursor-restart",
        "next_nsu": None,
        "coverage": "available",
    }
    assert effects == {"company:synthetic-001"}
    assert [call.cursor for call in restarted_adapter.transport.calls] == [None]
