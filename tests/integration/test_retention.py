from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.companies.models import Company
from nfx.documents.models import Document, DocumentEvidence
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest


def _client(role: str) -> Client:
    user = User.objects.create(
        email=f"{role}-{uuid4().hex}@example.test",
        name="Synthetic retention user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"synthetic-token-{uuid4().hex}"
    IdentitySession.objects.create(
        token_hash=_digest(token),
        user=user,
        revocation_version=user.revocation_version,
        last_activity_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    client = Client()
    client.cookies["nfx_session"] = token
    return client


def _document(*, family: str = "nfe", authorized_at: datetime | None = None) -> Document:
    company = Company.objects.create(
        cnpj=f"11222333000{len(Company.objects.all()) + 181}",
        legal_name="Retention Synthetic",
    )
    payload = b"<synthetic/>"
    artifact = Artifact.objects.create(
        logical_class="fiscal_original",
        logical_key=f"retention-{uuid4().hex}",
        object_key=f"artifacts/{uuid4().hex}/v1",
        digest=sha256(payload).hexdigest(),
        size_bytes=len(payload),
        declared_mime_type="application/xml",
        detected_mime_type="application/xml",
        state=ArtifactState.FINALIZED,
    )
    result = persist_document(
        DocumentInput(
            company_id=company.id,
            family=family,
            role="entrada",
            category="document",
            source="simulator",
            flow="distribution",
            identity=FiscalIdentity(official_key="retention-document"),
            emitted_at=datetime(2026, 8, 15, 12, tzinfo=UTC),
            authorized_at=authorized_at,
            situation="authorized",
            artifact_id=artifact.id,
            origin_execution_ref="execution-retention-1",
        )
    )
    assert result.document_id
    return Document.objects.get(pk=result.document_id)


@pytest.mark.django_db(transaction=True)
def test_retention_preview_is_admin_only_metadata_only_and_stable() -> None:
    document = _document(authorized_at=datetime(2026, 8, 15, 12, tzinfo=UTC))
    before = (Document.objects.count(), DocumentEvidence.objects.count(), Artifact.objects.count())

    admin = _client(Role.ADMINISTRATOR)
    listed = admin.get("/api/retention/documents", {"as_of": "2037-08-15"})
    assert listed.status_code == 200
    item = next(row for row in listed.json()["documents"] if row["id"] == str(document.id))
    assert item["state"] == "eligible"
    assert item["eligibility_date"] == "2037-08-15"
    assert item["rule_version"] == "retention-v1"

    first = admin.get(f"/api/retention/documents/{document.id}/preview")
    second = admin.get(f"/api/retention/documents/{document.id}/preview")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    serialized = str(first.json())
    assert "object_key" not in serialized
    assert "<synthetic/>" not in serialized
    assert first.json()["scope"]["hash"]
    assert first.json()["evidence"][0]["availability"] == "available"

    assert (
        Document.objects.count(),
        DocumentEvidence.objects.count(),
        Artifact.objects.count(),
    ) == before
    assert _client(Role.OPERATOR).get("/api/retention/documents").status_code == 403
    assert (
        _client(Role.VIEWER).get(f"/api/retention/documents/{document.id}/preview").status_code
        == 403
    )
    assert Client().get("/api/retention/documents").status_code == 403


@pytest.mark.django_db(transaction=True)
def test_retention_missing_authorization_is_non_executable_and_scope_changes_make_preview_stale(
) -> None:
    document = _document(authorized_at=None)
    admin = _client(Role.ADMINISTRATOR)
    response = admin.get(f"/api/retention/documents/{document.id}")
    assert response.status_code == 200
    assert response.json()["decision"]["state"] == "non_executable"
    assert response.json()["decision"]["reason_code"] == "authorization_date_missing"

    preview = admin.get(f"/api/retention/documents/{document.id}/preview")
    scope_hash = preview.json()["scope"]["hash"]
    DocumentEvidence.objects.update(conflicting=True)
    stale = admin.get(
        f"/api/retention/documents/{document.id}/preview", {"scope_hash": scope_hash}
    )
    assert stale.status_code == 409
    assert stale.json()["reason_code"] == "scope_changed"
