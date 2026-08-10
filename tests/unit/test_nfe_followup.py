from __future__ import annotations

from uuid import uuid4

import pytest
from nfx.adapters.nfe import (
    NFeCompleteXmlRequest,
    NFeFlow,
    NFeFollowUpAdapter,
    NFeFollowUpError,
    NFeFollowUpScenarioName,
    NFeFollowUpSimulator,
    NFeScienceRequest,
    build_nfe_followup_scenario,
)


def science_request(
    *, flow: NFeFlow = NFeFlow.RECEIVED, correlation: str = "correlation:science-1"
) -> NFeScienceRequest:
    return NFeScienceRequest(
        company_id=uuid4(),
        document_id=uuid4(),
        flow=flow,
        source="synthetic",
        actor="actor:synthetic-001",
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id=correlation,
    )


def xml_request(request: NFeScienceRequest) -> NFeCompleteXmlRequest:
    return NFeCompleteXmlRequest(
        company_id=request.company_id,
        document_id=request.document_id,
        flow=request.flow,
        source=request.source,
        actor=request.actor,
        policy_reference=request.policy_reference,
        certificate_handle=request.certificate_handle,
        correlation_id="correlation:xml-1",
        science_correlation_id=request.correlation_id,
    )


def test_science_gates_complete_xml_and_replays_without_a_second_call() -> None:
    simulator = NFeFollowUpSimulator(
        build_nfe_followup_scenario(NFeFollowUpScenarioName.PERMITTED, seed=601)
    )
    adapter = NFeFollowUpAdapter(simulator)
    request = science_request()

    result = adapter.science(request)
    assert result.retrieval_permitted is True
    first_xml = adapter.complete_xml(xml_request(request))
    second_xml = adapter.complete_xml(xml_request(request))

    assert first_xml == second_xml
    assert [call.operation for call in simulator.calls()] == ["science", "complete_xml"]


@pytest.mark.parametrize(
    "scenario_name",
    [
        NFeFollowUpScenarioName.DENIED,
        NFeFollowUpScenarioName.UNAVAILABLE,
        NFeFollowUpScenarioName.TIMEOUT,
        NFeFollowUpScenarioName.COOLDOWN,
        NFeFollowUpScenarioName.BLOCKED,
        NFeFollowUpScenarioName.MALFORMED,
        NFeFollowUpScenarioName.UNKNOWN,
    ],
)
def test_non_permitted_science_never_requests_complete_xml(
    scenario_name: NFeFollowUpScenarioName,
) -> None:
    simulator = NFeFollowUpSimulator(build_nfe_followup_scenario(scenario_name, seed=607))
    adapter = NFeFollowUpAdapter(simulator)
    request = science_request()

    result = adapter.science(request)
    assert result.retrieval_permitted is False
    with pytest.raises(NFeFollowUpError):
        adapter.complete_xml(xml_request(request))
    assert [call.operation for call in simulator.calls()] == ["science"]


def test_followup_contract_rejects_sensitive_context_and_unsafe_xml() -> None:
    with pytest.raises(NFeFollowUpError):
        science_request(correlation="https://production.invalid")

    with pytest.raises(NFeFollowUpError):
        NFeFollowUpSimulator(
            build_nfe_followup_scenario(NFeFollowUpScenarioName.PERMITTED, seed=613)
        ).complete_xml(
            NFeCompleteXmlRequest(
                company_id=uuid4(),
                document_id=uuid4(),
                flow=NFeFlow.RECEIVED,
                source="synthetic",
                actor="actor:synthetic-001",
                policy_reference="policy:synthetic-v1",
                certificate_handle="certificate:synthetic-001",
                correlation_id="correlation:xml-1",
                science_correlation_id="correlation:missing",
            )
        )
