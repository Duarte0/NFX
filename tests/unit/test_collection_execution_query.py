from __future__ import annotations

from datetime import date

import pytest
from django.http import QueryDict
from nfx.collection.services import (
    CollectionExecutionQueryError,
    normalize_collection_execution_filter,
)


def query(raw: str) -> QueryDict:
    return QueryDict(raw, mutable=False)


def test_collection_execution_filter_normalizes_card_state_and_half_open_dates() -> None:
    result = normalize_collection_execution_filter(
        query("from=2026-08-01&to=2026-09-01&state=running")
    )

    assert result.start == date(2026, 8, 1)
    assert result.end == date(2026, 9, 1)
    assert result.state == "running"
    assert result.model_state == "running"
    assert result.boundary == "[from,to)"


def test_recent_filter_is_the_existing_all_execution_card_without_new_model_state() -> None:
    result = normalize_collection_execution_filter(
        query("from=2026-08-01&to=2026-09-01&state=recent")
    )

    assert result.state == "recent"
    assert result.model_state is None


@pytest.mark.parametrize(
    "raw",
    [
        "to=2026-09-01&state=running",
        "from=2026-08-01&state=running",
        "from=2026-08-01&to=2026-09-01",
        "from=2026-08-01&to=2026-09-01&state=unsupported",
        "from=2026-09-01&to=2026-08-01&state=running",
        "from=2025-01-01&to=2026-09-01&state=running",
        "from=2026-08-01&to=2026-09-01&state=running&unexpected=1",
        "from=2026-08-01&from=2026-08-02&to=2026-09-01&state=running",
    ],
)
def test_collection_execution_filter_rejects_invalid_or_ambiguous_requests(raw: str) -> None:
    with pytest.raises(CollectionExecutionQueryError):
        normalize_collection_execution_filter(query(raw))
