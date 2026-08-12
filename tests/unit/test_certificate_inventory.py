from __future__ import annotations

from datetime import UTC, datetime

import pytest
from nfx.certificates.models import CertificateState
from nfx.certificates.services import (
    CertificateInventoryQueryError,
    certificate_inventory_queryset,
    normalize_certificate_inventory_query,
)


def test_certificate_inventory_filter_is_allowlisted_and_bounded() -> None:
    selected = normalize_certificate_inventory_query({"filter": "expiring", "limit": "7"})

    assert selected.filter_name == "expiring"
    assert selected.limit == 7
    assert selected.cursor is None
    assert selected.filter_payload == {"filter": "expiring"}


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"filter": "unsupported"},
        {"filter": ["current", "expired"]},
        {"filter": "current", "unexpected": "1"},
        {"filter": "current", "limit": "0"},
        {"filter": "current", "limit": "101"},
        {"filter": "current", "cursor": "not-a-cursor"},
    ],
)
def test_certificate_inventory_filter_rejects_ambiguous_or_unbounded_queries(
    query: dict[str, object],
) -> None:
    with pytest.raises(CertificateInventoryQueryError):
        normalize_certificate_inventory_query(query)


def test_certificate_inventory_predicates_use_explicit_utc_boundaries() -> None:
    evaluated_at = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)

    assert certificate_inventory_queryset("current", evaluated_at).query.where.children
    assert certificate_inventory_queryset("expired", evaluated_at).query.where.children
    assert certificate_inventory_queryset("expiring", evaluated_at).query.where.children
    assert CertificateState.CURRENT == "current"


def test_certificate_inventory_cursor_is_bounded_and_composite() -> None:
    selected = normalize_certificate_inventory_query(
        {
            "filter": "current",
            "cursor": "00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002",
        }
    )

    assert selected.cursor is not None
    assert selected.cursor.company_id.int == 1
    assert selected.cursor.certificate_id.int == 2
    assert len(selected.cursor_payload) < 100
