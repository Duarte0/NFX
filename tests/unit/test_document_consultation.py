from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from nfx.documents.consultation import (
    ConsultationParams,
    InvalidConsultationParams,
    cursor_for,
    parse_consultation_params,
    safe_filename,
)
from nfx.documents.metrics import DocumentMetrics


def test_consultation_params_accept_the_approved_bounded_filters() -> None:
    company = "11111111-1111-1111-1111-111111111111"

    params = parse_consultation_params(
        {
            "company_id": [company, "22222222-2222-2222-2222-222222222222"],
            "competence_from": "2026-01-01",
            "competence_to": "2026-03-31",
            "emitted_from": "2026-01-01",
            "emitted_to": "2026-03-31",
            "family": "nfe",
            "direction": "entrada",
            "search": "  Chave\u00a0Fiscal  ",
            "limit": "25",
        }
    )

    assert params == ConsultationParams(
        company_ids=(UUID(company), UUID("22222222-2222-2222-2222-222222222222")),
        competence_from=date(2026, 1, 1),
        competence_to=date(2026, 3, 31),
        emitted_from=date(2026, 1, 1),
        emitted_to=date(2026, 3, 31),
        family="nfe",
        flow=None,
        direction="entrada",
        nfse_category=None,
        event_type=None,
        search="Chave Fiscal",
        limit=25,
        cursor=None,
    )


@pytest.mark.parametrize(
    "query",
    [
        {"unsupported": "value"},
        {"limit": "101"},
        {"family": "xml"},
        {"direction": "all"},
        {"competence_from": "2026-02-01", "competence_to": "2026-01-01"},
        {"search": "x" * 129},
        {"company_id": ["not-a-uuid"]},
    ],
)
def test_consultation_params_reject_unsupported_or_invalid_input(query: dict[str, object]) -> None:
    with pytest.raises(InvalidConsultationParams):
        parse_consultation_params(query)


def test_cursor_is_opaque_and_round_trips_without_exposing_the_database_id() -> None:
    value = "11111111-1111-1111-1111-111111111111"

    token = cursor_for(value)

    assert token != value
    assert parse_consultation_params({"cursor": token}).cursor == value

    with pytest.raises(InvalidConsultationParams):
        parse_consultation_params({"cursor": "forged-cursor"})


def test_safe_filename_is_bounded_and_does_not_allow_path_traversal() -> None:
    assert safe_filename("../NF-e: 2026/08", "application/xml") == "nf-e-2026-08.xml"
    assert len(safe_filename("x" * 300, "application/octet-stream")) <= 96


def test_document_metrics_keep_only_bounded_outcomes() -> None:
    metrics = DocumentMetrics()

    metrics.record(action="consultation", result="empty", latency_ms=2.5)
    metrics.record(action="download", result="unavailable", latency_ms=3.5)

    assert metrics.snapshot() == metrics.snapshot().__class__(
        consultations=1,
        empty_results=1,
        consultation_errors=0,
        downloads=1,
        denied_downloads=0,
        unavailable_objects=1,
        download_errors=0,
        consultation_latency_ms=2.5,
        download_latency_ms=3.5,
    )
