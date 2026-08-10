from __future__ import annotations

import socket
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from nfx.adapters.adn import (
    AdnDistributionAdapter,
    AdnDistributionError,
    AdnDistributionPolicy,
    AdnDistributionRequest,
    AdnDistributionSimulator,
    AdnFlow,
    AdnPosition,
)
from nfx.adapters.simulation import (
    FiscalFamily,
    FiscalOutcome,
    FiscalResponse,
    FiscalUnit,
    ScenarioName,
    build_scenario,
)


def request(
    *,
    actor: str = "actor:synthetic-001",
    flow: AdnFlow | str = AdnFlow.TAKEN,
    position: AdnPosition | None = None,
    page_limit: int = 50,
) -> AdnDistributionRequest:
    return AdnDistributionRequest(
        company_id=uuid4(),
        actor=actor,
        flow=flow,
        source="synthetic",
        position=position,
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id="correlation:synthetic-001",
        page_limit=page_limit,
    )


def test_actor_and_flow_keep_independent_nsu_histories() -> None:
    simulator = AdnDistributionSimulator(
        build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.ADN, seed=401)
    )

    taken = simulator.distribute(request(flow=AdnFlow.TAKEN))
    provided = simulator.distribute(request(flow=AdnFlow.PROVIDED))
    other_actor = simulator.distribute(request(actor="actor:synthetic-002"))

    assert taken.continuation == AdnPosition(request().actor, AdnFlow.TAKEN, "nsu-1")
    assert provided.continuation == AdnPosition(request().actor, AdnFlow.PROVIDED, "nsu-1")
    assert other_actor.continuation == AdnPosition("actor:synthetic-002", AdnFlow.TAKEN, "nsu-1")
    assert [call.flow for call in simulator.calls(request().actor, AdnFlow.TAKEN)] == ["taken"]
    assert [call.flow for call in simulator.calls(request().actor, AdnFlow.PROVIDED)] == [
        "provided"
    ]

    next_taken = simulator.distribute(
        request(position=AdnPosition(request().actor, AdnFlow.TAKEN, "nsu-1"))
    )
    assert next_taken.units[0].identity != provided.units[0].identity
    assert [call.cursor for call in simulator.calls(request().actor, AdnFlow.PROVIDED)] == [None]


@pytest.mark.parametrize(
    ("scenario", "outcome", "coverage"),
    [
        (ScenarioName.VALID_EMPTY, FiscalOutcome.EMPTY, "available"),
        (ScenarioName.NO_COVERAGE, FiscalOutcome.NO_COVERAGE, "none"),
        (ScenarioName.UNAVAILABLE, FiscalOutcome.UNAVAILABLE, "unknown"),
        (ScenarioName.PARTIAL_RESULT, FiscalOutcome.PARTIAL, "available"),
        (ScenarioName.UNKNOWN_OUTCOME, FiscalOutcome.UNKNOWN, "unknown"),
    ],
)
def test_coverage_and_safe_outcomes_do_not_collapse(
    scenario: ScenarioName, outcome: FiscalOutcome, coverage: str
) -> None:
    simulator = AdnDistributionSimulator(build_scenario(scenario, FiscalFamily.ADN, seed=403))

    result = simulator.distribute(request())

    assert result.outcome == outcome
    assert result.coverage.value == coverage
    assert result.consumed == len(result.units)
    assert result.as_fiscal_response().safe_metadata["actor"] == "actor:synthetic-001"


def test_event_and_substitution_units_preserve_parent_evidence() -> None:
    event = AdnDistributionSimulator(
        build_scenario(ScenarioName.EVENT_WITH_PARENT, FiscalFamily.ADN, seed=407)
    ).distribute(request())
    substitution = AdnDistributionSimulator(
        build_scenario(ScenarioName.SUBSTITUTION, FiscalFamily.ADN, seed=409)
    ).distribute(request())

    assert [unit.kind for unit in event.units] == ["document", "event"]
    assert event.units[1].parent_identity == event.units[0].identity
    assert [unit.kind for unit in substitution.units] == ["document", "substitution"]
    assert substitution.units[1].parent_identity == substitution.units[0].identity


def test_invalid_scope_limits_sensitive_context_and_unknown_kinds_are_rejected() -> None:
    simulator = AdnDistributionSimulator(
        build_scenario(ScenarioName.VALID_EMPTY, FiscalFamily.ADN, seed=419)
    )
    with pytest.raises(AdnDistributionError):
        simulator.distribute(
            request(position=AdnPosition("actor:synthetic-002", AdnFlow.TAKEN, "nsu-1"))
        )
    with pytest.raises(AdnDistributionError):
        simulator.distribute(request(page_limit=0))
    with pytest.raises((AdnDistributionError, ValueError)):
        AdnDistributionRequest(
            company_id=uuid4(),
            actor="actor:synthetic-001",
            flow=AdnFlow.TAKEN,
            source="https://production.invalid",
            policy_reference="policy:synthetic-v1",
            certificate_handle="certificate:synthetic-001",
            correlation_id="correlation:synthetic-001",
        )

    class UnknownKindAdapter:
        family = FiscalFamily.ADN

        def collect(self, _request: object) -> FiscalResponse:
            unit = FiscalUnit(
                identity="synthetic:unknown-kind",
                content_hash="0" * 64,
                kind="unknown",
            )
            return FiscalResponse(FiscalOutcome.SUCCESS, units=(unit,))

    with pytest.raises(AdnDistributionError):
        AdnDistributionAdapter(UnknownKindAdapter()).distribute(request())


def test_safe_audit_metrics_replay_and_no_network() -> None:
    audit: list[Mapping[str, object]] = []
    simulator = AdnDistributionSimulator(
        build_scenario(ScenarioName.UNAVAILABLE, FiscalFamily.ADN, seed=421), audit=audit.append
    )

    def fail_socket(*_: object, **__: object) -> None:
        raise AssertionError("synthetic ADN simulator attempted network I/O")

    original_socket = socket.socket
    socket.socket = fail_socket  # type: ignore[assignment]
    try:
        current = request()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(simulator.distribute, (current, current)))
    finally:
        socket.socket = original_socket

    assert results[0] == results[1]
    assert [entry["event"] for entry in audit] == ["started", "completed"]
    assert all("payload" not in entry and "certificate" not in entry for entry in audit)
    assert simulator.metrics_snapshot().outcomes[FiscalOutcome.UNAVAILABLE.value] == 1
    assert simulator.metrics_snapshot().pages == 1


def test_response_rejects_oversized_page() -> None:
    class OversizedAdapter:
        family = FiscalFamily.ADN

        def collect(self, _request: object) -> FiscalResponse:
            units = tuple(
                FiscalUnit(
                    identity=f"synthetic:oversized:{index}",
                    content_hash="0" * 64,
                )
                for index in range(2)
            )
            return FiscalResponse(FiscalOutcome.SUCCESS, units=units)

    adapter = AdnDistributionAdapter(
        OversizedAdapter(), policy=AdnDistributionPolicy(max_page_units=1, default_page_units=1)
    )
    with pytest.raises(AdnDistributionError):
        adapter.distribute(request(page_limit=1))
