from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from nfx.documents.services import (
    DocumentInput,
    FiscalIdentity,
    InvalidDocumentInput,
    derive_competence,
    select_strongest_identity,
)


def test_strongest_official_identity_is_selected_and_normalized() -> None:
    identity = select_strongest_identity(
        FiscalIdentity(
            official_key="  ab-123 ",
            external_id="source-42",
            number="0007",
            series="01",
            issuer_tax_id="11.222.333/0001-81",
        )
    )

    assert identity.kind == "official_key"
    assert identity.value == "AB123"


def test_compound_identity_is_used_when_no_single_official_id_exists() -> None:
    identity = select_strongest_identity(
        FiscalIdentity(number="0007", series="01", issuer_tax_id="11.222.333/0001-81")
    )

    assert identity.kind == "number_series_issuer"
    assert identity.value == "0007|01|11222333000181"


def test_identity_without_official_components_is_rejected() -> None:
    with pytest.raises(InvalidDocumentInput, match="identity"):
        select_strongest_identity(FiscalIdentity())


def test_competence_is_derived_from_emission_and_requires_aware_time() -> None:
    emitted_at = datetime(2026, 8, 9, 2, 30, tzinfo=UTC)

    assert derive_competence(emitted_at).isoformat() == "2026-08-08"
    with pytest.raises(InvalidDocumentInput, match="timezone"):
        derive_competence(datetime(2026, 8, 9, 2, 30))


def test_document_input_rejects_unbounded_or_payload_like_references() -> None:
    with pytest.raises(InvalidDocumentInput):
        DocumentInput(
            company_id=uuid4(),
            family="nfe",
            role="entrada",
            category="document",
            source="source\nxml",
            flow="distribution",
            identity=FiscalIdentity(official_key="synthetic-1"),
            emitted_at=datetime(2026, 8, 9, tzinfo=UTC),
            artifact_id=uuid4(),
            origin_execution_ref="execution-1",
        ).validate()
