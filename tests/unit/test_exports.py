from datetime import date
from uuid import UUID

import pytest
from nfx.companies.models import Company
from nfx.documents.models import Document
from nfx.exports.models import ExportItem
from nfx.exports.services import ExportError, _idempotency, archive_path


def test_export_idempotency_is_bounded_and_stored_as_a_digest() -> None:
    digest = _idempotency(" request-1 ")
    assert len(digest) == 64
    assert digest.isalnum()
    with pytest.raises(ExportError):
        _idempotency("../unsafe")


def test_export_archive_path_is_deterministic_safe_and_non_colliding() -> None:
    company = Company(id=UUID("11111111-1111-1111-1111-111111111111"), legal_name="../São & Filhos")
    document = Document(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        company=company,
        family="nfe",
        role="entrada",
        normalized_identity="../../NF-e/2026",
        competence=date(2026, 8, 10),
    )
    item = ExportItem(document=document, content_type="application/xml")
    path = archive_path(item)
    assert ".." not in path
    assert path.endswith("-222222222222.xml")
    assert path == archive_path(item)
