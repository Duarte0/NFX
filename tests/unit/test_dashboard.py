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
    assert cards["documents.total"]["drilldown"]["href"] == (
        "?from=2026-08-01&to=2026-09-01#documentos"
    )


def test_collection_source_failure_is_unavailable_without_erasing_other_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.operations.dashboard._collection_counts",
        lambda period: (_ for _ in ()).throw(RuntimeError("synthetic collection failure")),
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._company_counts", lambda: {"active": 2, "inactive": 0}
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._document_counts", _empty_document_counts, raising=False
    )
    monkeypatch.setattr("nfx.operations.dashboard._job_counts", _empty_job_counts)

    payload = build_dashboard(
        period=normalize_period({"from": "2026-08-01", "to": "2026-09-01"}),
        role=Role.VIEWER,
    )
    cards = {card["id"]: card for card in payload["cards"]}

    assert cards["collections.recent"]["status"] == "unavailable"
    assert cards["collections.recent"]["current"]["value"] is None
    assert cards["documents.total"]["status"] == "zero"
    assert cards["companies.active"]["current"]["value"] == 2


def _empty_document_counts(period: object) -> dict[str, int]:
    del period
    return {"total": 0, "nfe": 0, "nfse": 0, "entrada": 0, "saida": 0, "tomados": 0, "prestados": 0}


def _empty_collection_counts(period: object) -> dict[str, int]:
    del period
    return {"recent": 0, "completed": 0, "running": 0, "failed": 0, "blocked": 0, "partial": 0}


def _empty_job_counts(period: object) -> dict[str, int]:
    del period
    return {"recent": 0, "pending": 0, "completed": 0, "blocked": 0, "failed": 0}


def _empty_certificate_counts(now: object) -> dict[str, int]:
    del now
    return {"current": 0, "expired": 0, "expiring": 0}


def _admin_backup_summary(
    monkeypatch: pytest.MonkeyPatch, source_status: object
) -> dict[str, object]:
    monkeypatch.setattr(
        "nfx.operations.dashboard._health_payload",
        lambda now: {"status": "ready", "read_only": True},
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard.backup_status",
        lambda *, now: source_status,
        raising=False,
    )
    for name, value in (
        ("_company_counts", {"active": 1, "inactive": 0}),
        ("_document_counts", _empty_document_counts),
        ("_collection_counts", _empty_collection_counts),
        ("_job_counts", _empty_job_counts),
        ("_certificate_counts", _empty_certificate_counts),
    ):
        monkeypatch.setattr(f"nfx.operations.dashboard.{name}", value)

    payload = build_dashboard(
        period=normalize_period({"from": "2026-08-01", "to": "2026-09-01"}),
        role=Role.ADMINISTRATOR,
    )
    return payload["operational_health"]["backup"]


def test_admin_backup_summary_maps_safe_bounded_fields_and_redacts_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = _admin_backup_summary(
        monkeypatch,
        {
            "status": "success",
            "latest_backup": {
                "id": "raw-backup-id",
                "state": "failed",
                "kind": "daily",
                "backup_path": "/sensitive/path",
                "manifest": {"objects": [{"object_key": "secret-key"}]},
                "manifest_hash": "secret-hash",
                "size_bytes": 999,
                "safe_error": "archive_corrupt",
            },
            "latest_success_age_seconds": 123.9,
            "retention": {"daily": 99, "weekly": 8, "monthly": 20},
            "latest_restore": {
                "id": "raw-restore-id",
                "state": "failed",
                "target_reference": "/live/target",
                "safe_error": "archive_corrupt",
            },
        },
    )

    assert summary == {
        "status": "success",
        "latest_backup": {"state": "failed", "safe_error": "archive_corrupt"},
        "latest_success_age_seconds": 123,
        "retention": {"daily": 7, "weekly": 4, "monthly": 12},
        "latest_restore": {"state": "failed", "safe_error": "archive_corrupt"},
    }
    assert "raw-backup-id" not in str(summary)
    assert "secret-key" not in str(summary)
    assert "/live/target" not in str(summary)


@pytest.mark.parametrize("status", ["failure", "unavailable"])
def test_admin_backup_summary_does_not_turn_missing_success_into_zero(
    monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    summary = _admin_backup_summary(
        monkeypatch,
        {
            "status": status,
            "latest_backup": {"id": "raw-id", "state": "failed", "safe_error": "capture_failed"},
            "latest_success_age_seconds": None,
            "retention": {"daily": 0, "weekly": 0, "monthly": 0},
            "latest_restore": {"id": None, "state": None, "safe_error": ""},
        },
    )

    assert summary["status"] == status
    assert summary["latest_success_age_seconds"] is None
    assert summary["retention"] == {"daily": None, "weekly": None, "monthly": None}


def test_backup_source_failure_degrades_only_admin_backup_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.operations.dashboard._health_payload",
        lambda now: {"status": "ready", "read_only": True},
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard.backup_status",
        lambda *, now: (_ for _ in ()).throw(RuntimeError("provider exception")),
        raising=False,
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._company_counts", lambda: {"active": 2, "inactive": 0}
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._document_counts",
        _empty_document_counts,
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._collection_counts",
        _empty_collection_counts,
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._job_counts",
        _empty_job_counts,
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard._certificate_counts",
        _empty_certificate_counts,
    )

    payload = build_dashboard(
        period=normalize_period({"from": "2026-08-01", "to": "2026-09-01"}),
        role=Role.ADMINISTRATOR,
    )
    cards = {card["id"]: card for card in payload["cards"]}

    assert payload["operational_health"]["status"] == "ready"
    assert payload["operational_health"]["backup"]["status"] == "unavailable"
    assert cards["companies.active"]["current"]["value"] == 2
    assert cards["documents.total"]["status"] == "zero"
