from __future__ import annotations

from datetime import date

import pytest
from django.http import QueryDict
from nfx.certificates.services import CERTIFICATE_INVENTORY_FILTERS
from nfx.collection.services import COLLECTION_DASHBOARD_STATE_FILTERS
from nfx.companies.services import COMPANY_LIFECYCLE_STATUS_FILTERS
from nfx.documents.status import DOCUMENT_DASHBOARD_FILTERS
from nfx.jobs.observability import JOB_DASHBOARD_FILTERS
from nfx.operations.dashboard import InvalidDashboardParams, normalize_period


def test_cross_owner_matrix_records_the_exact_allowlisted_card_contract() -> None:
    assert DOCUMENT_DASHBOARD_FILTERS == {
        "total": {},
        "nfe": {"family": "nfe"},
        "nfse": {"family": "nfse"},
        "entrada": {"family": "nfe", "direction": "entrada"},
        "saida": {"family": "nfe", "direction": "saida"},
        "tomados": {"family": "nfse", "nfse_category": "tomada"},
        "prestados": {"family": "nfse", "nfse_category": "prestada"},
    }
    assert COLLECTION_DASHBOARD_STATE_FILTERS == {
        "recent": None,
        "running": "running",
        "failed": "failed",
        "blocked": "blocked",
        "partial": "partial",
    }
    assert set(COMPANY_LIFECYCLE_STATUS_FILTERS) == {"active", "inactive"}
    assert set(CERTIFICATE_INVENTORY_FILTERS) == {"current", "expired", "expiring"}
    assert set(JOB_DASHBOARD_FILTERS) == {"pending", "failed", "blocked"}


def test_period_contract_is_consecutive_half_open_and_bounded() -> None:
    period = normalize_period(QueryDict("from=2026-08-01&to=2026-09-01"))

    assert period.current.start == date(2026, 8, 1)
    assert period.current.end == date(2026, 9, 1)
    assert period.previous.end == period.current.start
    assert period.current.days == period.previous.days


@pytest.mark.parametrize(
    "query",
    [
        "from=2026-08-01",
        "to=2026-09-01",
        "from=2026-09-01&to=2026-08-01",
        "from=2025-01-01&to=2026-09-01",
        "from=2026-08-01&from=2026-08-02&to=2026-09-01",
        "from=2026-08-01&to=2026-09-01&unexpected=value",
    ],
)
def test_dashboard_period_rejects_malformed_or_ambiguous_input(query: str) -> None:
    with pytest.raises(InvalidDashboardParams):
        normalize_period(QueryDict(query))
