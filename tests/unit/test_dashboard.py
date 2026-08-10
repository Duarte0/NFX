from __future__ import annotations

from datetime import date

import pytest
from nfx.identity.models import Role
from nfx.operations.dashboard import (
    InvalidDashboardParams,
    build_dashboard,
    normalize_period,
)


def test_periods_are_half_open_equal_duration_and_non_overlapping() -> None:
    period = normalize_period({"from": "2026-08-10", "to": "2026-08-20"})

    assert period.current.start == date(2026, 8, 10)
    assert period.current.end == date(2026, 8, 20)
    assert period.previous.start == date(2026, 7, 31)
    assert period.previous.end == period.current.start
    assert period.current.end - period.current.start == period.current.start - period.previous.start


@pytest.mark.parametrize(
    "query",
    [
        {"from": "2026-08-20", "to": "2026-08-10"},
        {"from": "2025-01-01", "to": "2026-01-03"},
        {"from": "not-a-date", "to": "2026-08-20"},
        {"from": "2026-08-10", "to": "2026-08-20", "unsupported": "1"},
    ],
)
def test_period_validation_is_bounded_and_fail_closed(query: dict[str, str]) -> None:
    with pytest.raises(InvalidDashboardParams):
        normalize_period(query)


def test_default_period_is_the_current_civil_month() -> None:
    period = normalize_period({}, today=date(2026, 8, 10))

    assert period.current.start == date(2026, 8, 1)
    assert period.current.end == date(2026, 9, 1)
    assert period.previous.start == date(2026, 7, 1)
    assert period.previous.end == date(2026, 8, 1)


def test_document_source_failure_does_not_erase_unrelated_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.operations.dashboard._document_counts",
        lambda period: (_ for _ in ()).throw(RuntimeError("synthetic source failure")),
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._company_counts",
        lambda: {"active": 2, "inactive": 1},
    )
    payload = build_dashboard(
        period=normalize_period({"from": "2026-08-01", "to": "2026-09-01"}),
        role=Role.VIEWER,
    )
    cards = {card["id"]: card for card in payload["cards"]}

    assert cards["companies.active"]["status"] in {"zero", "ready"}
    assert cards["documents.total"]["status"] == "unavailable"
    assert cards["documents.total"]["current"]["freshness"]["status"] == "unknown"
    assert cards["documents.total"]["drilldown"]["href"] == "#documentos"
