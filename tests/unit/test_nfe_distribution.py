from __future__ import annotations

import hashlib
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from nfx.adapters.nfe import (
    NFeDistributionAdapter,
    NFeDistributionError,
    NFeDistributionPolicy,
    NFeDistributionRequest,
    NFeDistributionSimulator,
    NFeFlow,
    NFePosition,
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
    flow: NFeFlow | str = NFeFlow.RECEIVED,
    position: NFePosition | None = None,
    page_limit: int = 50,
) -> NFeDistributionRequest:
    return NFeDistributionRequest(
        company_id=uuid4(),
        flow=flow,
        source="synthetic",
        actor="actor:synthetic-001",
        position=position,
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id="correlation:synthetic-001",
        page_limit=page_limit,
    )


def test_received_and_issued_keep_independent_histories_and_positions() -> None:
    simulator = NFeDistributionSimulator(
        build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.NFE, seed=101)
    )

    received = simulator.distribute(request(flow=NFeFlow.RECEIVED))
    issued = simulator.distribute(request(flow=NFeFlow.ISSUED))

    assert received.units[0].identity == issued.units[0].identity
    assert received.continuation == NFePosition(NFeFlow.RECEIVED, "cursor-1")
    assert issued.continuation == NFePosition(NFeFlow.ISSUED, "cursor-1")
    assert simulator.calls(NFeFlow.RECEIVED)[0].flow == "received"
    assert simulator.calls(NFeFlow.ISSUED)[0].flow == "issued"

    received_next = simulator.distribute(
        request(
            flow=NFeFlow.RECEIVED,
            position=NFePosition(NFeFlow.RECEIVED, "cursor-1"),
        )
    )
    assert received_next.units[0].identity != issued.units[0].identity
    assert [call.cursor for call in simulator.calls(NFeFlow.ISSUED)] == [None]


@pytest.mark.parametrize(
    "scenario_name",
    [
        ScenarioName.PAGINATED_SUCCESS,
        ScenarioName.VALID_EMPTY,
        ScenarioName.UNAVAILABLE,
        ScenarioName.TIMEOUT,
        ScenarioName.PERMANENT_BLOCK,
        ScenarioName.MALFORMED_PAYLOAD,
        ScenarioName.UNKNOWN_OUTCOME,
    ],
)
def test_simulator_exposes_explicit_safe_outcomes(scenario_name: ScenarioName) -> None:
    simulator = NFeDistributionSimulator(
        build_scenario(scenario_name, FiscalFamily.NFE, seed=103)
    )

    result = simulator.distribute(request())

    assert result.outcome in {
        FiscalOutcome.SUCCESS,
        FiscalOutcome.EMPTY,
        FiscalOutcome.UNAVAILABLE,
        FiscalOutcome.TIMEOUT,
        FiscalOutcome.BLOCKED,
        FiscalOutcome.MALFORMED,
        FiscalOutcome.UNKNOWN,
    }
    assert result.consumed == len(result.units)
    assert result.safe_reason.islower()


def test_wrong_family_flow_position_and_limits_are_rejected() -> None:
    simulator = NFeDistributionSimulator(
        build_scenario(ScenarioName.VALID_EMPTY, FiscalFamily.NFE, seed=107)
    )

    with pytest.raises(NFeDistributionError):
        simulator.distribute(
            request(
                position=NFePosition(
                    NFeFlow.RECEIVED, "nsu-1", family=FiscalFamily.ADN
                )
            )
        )
    with pytest.raises(NFeDistributionError):
        simulator.distribute(
            request(
                flow=NFeFlow.ISSUED,
                position=NFePosition(NFeFlow.RECEIVED, "cursor-1"),
            )
        )
    with pytest.raises(NFeDistributionError):
        simulator.distribute(request(page_limit=0))


def test_sensitive_request_context_is_rejected() -> None:
    with pytest.raises((NFeDistributionError, ValueError)):
        NFeDistributionRequest(
            company_id=uuid4(),
            flow=NFeFlow.RECEIVED,
            source="https://production.invalid",
            actor="actor:synthetic-001",
            policy_reference="policy:synthetic-v1",
            certificate_handle="certificate:synthetic-001",
            correlation_id="correlation:synthetic-001",
        )


def test_over_bounded_response_fails_without_becoming_empty() -> None:
    class OversizedAdapter:
        family = FiscalFamily.NFE

        def collect(self, _request: object) -> FiscalResponse:
            units = tuple(
                FiscalUnit(
                    identity=f"synthetic:oversized:{index}",
                    content_hash=hashlib.sha256(str(index).encode()).hexdigest(),
                )
                for index in range(2)
            )
            return FiscalResponse(FiscalOutcome.SUCCESS, units=units)

    adapter = NFeDistributionAdapter(
        OversizedAdapter(), policy=NFeDistributionPolicy(max_page_units=1, default_page_units=1)
    )

    with pytest.raises(NFeDistributionError):
        adapter.distribute(request(page_limit=1))


def test_unknown_response_envelope_fails_explicitly() -> None:
    class UnknownEnvelopeAdapter:
        family = FiscalFamily.NFE

        def collect(self, _request: object) -> Mapping[str, str]:
            return {"outcome": "unknown"}

    adapter = NFeDistributionAdapter(UnknownEnvelopeAdapter())

    with pytest.raises(NFeDistributionError):
        adapter.distribute(request())


def test_safe_audit_and_metrics_mapping_contains_no_raw_payload() -> None:
    audit: list[Mapping[str, object]] = []
    simulator = NFeDistributionSimulator(
        build_scenario(ScenarioName.UNAVAILABLE, FiscalFamily.NFE, seed=109),
        audit=audit.append,
    )

    simulator.distribute(request())

    assert [entry["event"] for entry in audit] == ["started", "completed"]
    assert all("payload" not in entry and "certificate" not in entry for entry in audit)
    assert audit[-1]["flow"] == "received"
    assert audit[-1]["outcome"] == FiscalOutcome.UNAVAILABLE.value
    snapshot = simulator.metrics_snapshot()
    assert snapshot.outcomes[FiscalOutcome.UNAVAILABLE.value] == 1
    assert snapshot.pages == 1


def test_concurrent_duplicate_request_is_replayed_once() -> None:
    simulator = NFeDistributionSimulator(
        build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.NFE, seed=113)
    )
    current = request()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(simulator.distribute, (current, current)))

    assert results[0] == results[1]
    assert [call.cursor for call in simulator.calls(NFeFlow.RECEIVED)] == [None]
    assert simulator.metrics_snapshot().pages == 1
