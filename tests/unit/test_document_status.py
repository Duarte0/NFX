from __future__ import annotations

import pytest
from nfx.documents.status import (
    DocumentListParams,
    DocumentStatusCode,
    InvalidDocumentListParams,
    collection_status,
)


@pytest.mark.parametrize(
    ("collection_state", "page_coverage", "page_state", "expected"),
    [
        ("empty", "available", "empty", DocumentStatusCode.VALID_EMPTY),
        ("partial", "available", "partial", DocumentStatusCode.PARTIAL),
        ("retrying", "available", "failed", DocumentStatusCode.RETRY),
        ("blocked", "available", "failed", DocumentStatusCode.BLOCKED),
        ("idle", "none", "complete", DocumentStatusCode.NO_COVERAGE),
        ("idle", "unknown", "complete", DocumentStatusCode.UNKNOWN),
        ("idle", "available", "failed", DocumentStatusCode.UNAVAILABLE),
    ],
)
def test_collection_status_preserves_explicit_operational_meaning(
    collection_state: str,
    page_coverage: str,
    page_state: str,
    expected: DocumentStatusCode,
) -> None:
    result = collection_status(
        collection_state=collection_state,
        page_coverage=page_coverage,
        page_state=page_state,
        has_documents=False,
    )

    assert result.code == expected


def test_collection_status_does_not_infer_success_from_documents() -> None:
    result = collection_status(
        collection_state="idle",
        page_coverage=None,
        page_state=None,
        has_documents=True,
    )

    assert result.code == DocumentStatusCode.UNKNOWN


@pytest.mark.parametrize(
    ("page_outcome", "expected"),
    [
        ("no_coverage", DocumentStatusCode.NO_COVERAGE),
        ("unavailable", DocumentStatusCode.UNAVAILABLE),
        ("temporary_failure", DocumentStatusCode.RETRY),
        ("quarantine", DocumentStatusCode.UNKNOWN),
        ("conflict", DocumentStatusCode.UNKNOWN),
    ],
)
def test_status_consumes_the_persisted_page_outcome_without_inference(
    page_outcome: str, expected: DocumentStatusCode
) -> None:
    result = collection_status(
        collection_state="idle",
        page_coverage="available",
        page_state="complete",
        page_outcome=page_outcome,
        has_documents=False,
    )

    assert result.code == expected


def test_document_list_params_are_bounded_and_cursor_is_validated() -> None:
    assert DocumentListParams.from_query({"limit": "25", "family": "nfe"}).limit == 25

    with pytest.raises(InvalidDocumentListParams):
        DocumentListParams.from_query({"limit": "101"})
    with pytest.raises(InvalidDocumentListParams):
        DocumentListParams.from_query({"cursor": "not-a-uuid"})
    with pytest.raises(InvalidDocumentListParams):
        DocumentListParams.from_query({"flow": "raw xml"})
