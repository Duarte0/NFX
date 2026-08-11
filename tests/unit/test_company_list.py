from __future__ import annotations

import pytest
from django.http import QueryDict
from nfx.companies.models import CompanyStatus
from nfx.companies.services import (
    CompanyListQueryError,
    normalize_company_list_filter,
)


@pytest.mark.parametrize(
    ("lifecycle", "statuses"),
    [
        ("active", (CompanyStatus.ACTIVE,)),
        ("inactive", (CompanyStatus.REGISTERED, CompanyStatus.DEACTIVATED)),
    ],
)
def test_company_lifecycle_filter_maps_to_canonical_statuses(
    lifecycle: str, statuses: tuple[str, ...]
) -> None:
    selected = normalize_company_list_filter(QueryDict(f"lifecycle={lifecycle}"))

    assert selected.lifecycle == lifecycle
    assert selected.statuses == statuses
    assert selected.filter_payload == {"lifecycle": lifecycle}


def test_company_list_preserves_single_legacy_status_filter() -> None:
    selected = normalize_company_list_filter(QueryDict("status=ativa&search=Alpha&limit=2"))

    assert selected.lifecycle is None
    assert selected.status == CompanyStatus.ACTIVE
    assert selected.search == "Alpha"
    assert selected.limit == 2
    assert selected.filter_payload == {"status": CompanyStatus.ACTIVE, "search": "Alpha"}


@pytest.mark.parametrize(
    "query",
    [
        "lifecycle=active&lifecycle=inactive",
        "lifecycle=unsupported",
        "lifecycle=active&status=ativa",
        "status=unsupported",
        "lifecycle=active&unknown=value",
    ],
)
def test_company_list_filter_rejects_repeated_conflicting_and_unsupported_values(
    query: str,
) -> None:
    with pytest.raises(CompanyListQueryError):
        normalize_company_list_filter(QueryDict(query))
