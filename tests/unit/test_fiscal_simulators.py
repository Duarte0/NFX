from __future__ import annotations

import socket
from datetime import UTC, datetime

import pytest
from nfx.adapters.fiscal import FiscalDestinationError, FiscalDestinationGuard
from nfx.adapters.simulation import (
    AdnSimulator,
    FiscalFamily,
    FiscalOutcome,
    FiscalRequest,
    NFeSimulator,
    ScenarioName,
    ScenarioValidationError,
    build_scenario,
    make_simulator_handler,
)
from nfx.infrastructure.configuration import load_settings


def request(
    *,
    family: FiscalFamily,
    cursor: str | None = None,
    flow: str = "received",
) -> FiscalRequest:
    return FiscalRequest(
        source="synthetic",
        family=family,
        actor="actor:synthetic-001",
        flow=flow,
        cursor=cursor,
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id="correlation:synthetic-001",
    )


def test_nfe_and_adn_are_independent_deterministic_adapters() -> None:
    nfe = NFeSimulator(build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.NFE, seed=7))
    adn = AdnSimulator(build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.ADN, seed=7))

    first_nfe = nfe.collect(request(family=FiscalFamily.NFE))
    first_adn = adn.collect(request(family=FiscalFamily.ADN))

    assert first_nfe.outcome == FiscalOutcome.SUCCESS
    assert first_adn.outcome == FiscalOutcome.SUCCESS
    assert first_nfe.next_cursor == "cursor-1"
    assert first_nfe.next_nsu is None
    assert first_adn.next_cursor is None
    assert first_adn.next_nsu == "nsu-1"
    assert first_nfe.units[0].identity != first_adn.units[0].identity
    assert [call.cursor for call in nfe.transport.calls] == [None]
    assert [call.cursor for call in adn.transport.calls] == [None]


@pytest.mark.parametrize("scenario_name", list(ScenarioName))
def test_every_required_scenario_is_generated_and_marked_synthetic(
    scenario_name: ScenarioName,
) -> None:
    scenario = build_scenario(scenario_name, FiscalFamily.NFE, seed=19)
    assert scenario.seed == 19
    assert scenario.steps
    assert all(unit.synthetic for step in scenario.steps for unit in step.response.units)


def test_pagination_and_restart_replay_are_stable() -> None:
    scenario = build_scenario(ScenarioName.INTERRUPTION_RESTART, FiscalFamily.NFE, seed=23)
    first_run = NFeSimulator(scenario)
    restarted_run = NFeSimulator(
        build_scenario(ScenarioName.INTERRUPTION_RESTART, FiscalFamily.NFE, seed=23)
    )

    first_page = first_run.collect(request(family=FiscalFamily.NFE))
    restarted_page = restarted_run.collect(request(family=FiscalFamily.NFE))
    second_page = first_run.collect(request(family=FiscalFamily.NFE, cursor=first_page.next_cursor))

    assert restarted_page == first_page
    assert first_page.next_cursor == "cursor-restart"
    assert second_page.next_cursor is None
    assert [call.cursor for call in first_run.transport.calls] == [None, "cursor-restart"]


@pytest.mark.parametrize(
    ("scenario_name", "expected"),
    [
        (ScenarioName.VALID_EMPTY, FiscalOutcome.EMPTY),
        (ScenarioName.NO_COVERAGE, FiscalOutcome.NO_COVERAGE),
        (ScenarioName.DUPLICATE_EQUAL_HASH, FiscalOutcome.DUPLICATE),
        (ScenarioName.IDENTITY_CONFLICT, FiscalOutcome.CONFLICT),
        (ScenarioName.TIMEOUT, FiscalOutcome.TIMEOUT),
        (ScenarioName.UNAVAILABLE, FiscalOutcome.UNAVAILABLE),
        (ScenarioName.COOLDOWN, FiscalOutcome.COOLDOWN),
        (ScenarioName.PERMANENT_BLOCK, FiscalOutcome.BLOCKED),
        (ScenarioName.MALFORMED_PAYLOAD, FiscalOutcome.MALFORMED),
        (ScenarioName.EVENT_WITHOUT_PARENT, FiscalOutcome.EVENT_WITHOUT_PARENT),
        (ScenarioName.PARTIAL_RESULT, FiscalOutcome.PARTIAL),
    ],
)
def test_required_outcomes_are_distinct(
    scenario_name: ScenarioName, expected: FiscalOutcome
) -> None:
    simulator = NFeSimulator(build_scenario(scenario_name, FiscalFamily.NFE, seed=29))
    response = simulator.collect(request(family=FiscalFamily.NFE))

    assert response.outcome == expected
    if expected == FiscalOutcome.EMPTY:
        assert response.units == ()
        assert response.coverage.value == "available"
    if expected == FiscalOutcome.COOLDOWN:
        assert response.cooldown_until == datetime(2030, 1, 1, tzinfo=UTC)
    if expected == FiscalOutcome.NO_COVERAGE:
        assert response.coverage.value == "none"


def test_repeated_cursor_is_explicit_and_request_order_is_recorded() -> None:
    simulator = NFeSimulator(
        build_scenario(ScenarioName.REPEATED_CURSOR, FiscalFamily.NFE, seed=31)
    )

    first = simulator.collect(request(family=FiscalFamily.NFE))
    second = simulator.collect(request(family=FiscalFamily.NFE, cursor=first.next_cursor))

    assert first.next_cursor == second.next_cursor == "cursor-repeat"
    assert second.outcome == FiscalOutcome.REPEATED_CURSOR
    assert [call.cursor for call in simulator.transport.calls] == [None, "cursor-repeat"]


def test_invalid_fixture_fails_explicitly_instead_of_becoming_empty() -> None:
    with pytest.raises(ScenarioValidationError):
        build_scenario("not-a-scenario", FiscalFamily.NFE, seed=1)


def test_request_rejects_sensitive_or_raw_context() -> None:
    with pytest.raises(ValueError):
        FiscalRequest(
            source="https://production.invalid",
            family=FiscalFamily.NFE,
            actor="actor:synthetic-001",
            flow="received",
            cursor=None,
            policy_reference="policy:synthetic-v1",
            certificate_handle="certificate:synthetic-001",
            correlation_id="correlation:synthetic-001",
        )

    with pytest.raises(ValueError):
        FiscalRequest(
            source="synthetic",
            family=FiscalFamily.NFE,
            actor="actor:synthetic-001",
            flow="received",
            cursor=None,
            policy_reference="policy:synthetic-v1",
            certificate_handle="certificate:synthetic-secret-canary",
            correlation_id="correlation:synthetic-001",
        )


def test_simulator_never_opens_a_network_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*_: object, **__: object) -> None:
        raise AssertionError("synthetic simulator attempted network I/O")

    monkeypatch.setattr(socket, "socket", fail_socket)
    simulator = NFeSimulator(build_scenario(ScenarioName.VALID_EMPTY, FiscalFamily.NFE, seed=41))

    assert simulator.collect(request(family=FiscalFamily.NFE)).outcome == FiscalOutcome.EMPTY
    assert simulator.transport.calls[0].source == "synthetic"


def test_simulator_handler_returns_only_safe_referential_outcome() -> None:
    simulator = NFeSimulator(
        build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.NFE, seed=37)
    )
    handler = make_simulator_handler(simulator)

    class Job:
        payload = {
            "source": "synthetic",
            "family": "nfe",
            "actor": "actor:synthetic-001",
            "flow": "received",
            "policy_reference": "policy:synthetic-v1",
            "certificate_handle": "certificate:synthetic-001",
            "correlation_id": "correlation:synthetic-001",
        }

    outcome = handler(Job())

    assert outcome.kind == "success"
    assert outcome.result == {
        "outcome": "success",
        "unit_count": 1,
        "next_cursor": "cursor-1",
        "next_nsu": None,
        "coverage": "available",
    }


def test_destination_guard_rejects_before_fake_transport_is_called() -> None:
    calls: list[str] = []
    settings = load_settings(
        {
            "NFX_PROFILE": "test",
            "NFX_SECRET_KEY": "synthetic-test-secret",
            "NFX_CERTIFICATE_MASTER_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "NFX_FISCAL_TRANSPORT": "simulator",
            "NFX_FISCAL_DESTINATION": "simulator://empty",
            "DATABASE_URL": "postgresql://user:password@database.test:5432/nfx_test",
            "MINIO_ROOT_PASSWORD": "synthetic-minio-secret",
        }
    )
    guard = FiscalDestinationGuard(settings.public)

    with pytest.raises(FiscalDestinationError):
        guard.send("https://sefaz.production.invalid", calls.append)

    assert calls == []
