from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.collection.models import (
    CollectionExecutionState,
    IngestionPage,
    IngestionPageState,
    ReceivedUnit,
    ReceivedUnitState,
)
from nfx.companies.models import Company, CompanyFlow, FlowFamily
from nfx.documents.models import Document, DocumentSituation, DocumentState
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest


def _client(role: str = Role.VIEWER) -> Client:
    user = User.objects.create(
        email=f"{role}-{uuid4().hex}@example.test",
        name="Synthetic reader",
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


def _artifact(key: str, payload: bytes = b"synthetic-document") -> Artifact:
    return Artifact.objects.create(
        logical_class="fiscal_original",
        logical_key=key,
        object_key=f"artifacts/{uuid4().hex}/v1",
        digest_algorithm="sha256",
        digest=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        declared_mime_type="application/octet-stream",
        detected_mime_type="application/octet-stream",
        state=ArtifactState.FINALIZED,
    )


def _document(company: Company, key: str = "synthetic-document") -> Document:
    artifact = _artifact(key)
    result = persist_document(
        DocumentInput(
            company_id=company.id,
            family=FlowFamily.NFE,
            role="entrada",
            category="document",
            source="simulator",
            flow="distribution",
            identity=FiscalIdentity(official_key=f"synthetic-{key}"),
            emitted_at=datetime(2026, 8, 9, 14, 0, tzinfo=UTC),
            authorized_at=datetime(2026, 8, 9, 14, 1, tzinfo=UTC),
            situation=DocumentSituation.AUTHORIZED,
            artifact_id=artifact.id,
            origin_execution_ref="execution-synthetic-1",
        )
    )
    assert result.document_id
    return Document.objects.get(pk=result.document_id)


@pytest.mark.django_db(transaction=True)
def test_document_list_is_authenticated_and_valid_empty_is_not_unavailable() -> None:
    company = Company.objects.create(cnpj="11222333000181", legal_name="Synthetic Company")
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)

    anonymous = Client().get("/api/documents")
    response = _client().get("/api/documents", {"company_id": str(company.id), "family": "nfe"})

    assert anonymous.status_code == 403
    assert response.status_code == 200
    assert response.json()["status"] == "unknown"
    assert response.json()["documents"] == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("role", [Role.ADMINISTRATOR, Role.OPERATOR, Role.VIEWER])
def test_all_authenticated_roles_can_read_the_global_document_scope(role: str) -> None:
    company = Company.objects.create(
        cnpj=f"1122233300018{len(role)}", legal_name="Synthetic Company"
    )
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)

    response = _client(role).get("/api/documents", {"company_id": str(company.id)})

    assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_document_list_rejects_invalid_bounds_without_querying_documents() -> None:
    client = _client()

    response = client.get("/api/documents", {"limit": "101"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Parâmetros inválidos."}


@pytest.mark.django_db(transaction=True)
def test_document_list_redacts_storage_and_external_error_fields_and_does_not_write() -> None:
    company = Company.objects.create(cnpj="11222333000182", legal_name="Synthetic Company")
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)
    document = _document(company)
    document.state = DocumentState.CONFLICT
    document.save(update_fields=["state", "updated_at"])
    page = IngestionPage.objects.create(
        company=company,
        family=FlowFamily.NFE,
        flow="distribution",
        page_key="page-synthetic",
        adapter_outcome="success",
        coverage="available",
        state=IngestionPageState.COMPLETE,
        unit_count=1,
    )
    ReceivedUnit.objects.create(
        page=page,
        company=company,
        family=FlowFamily.NFE,
        flow="distribution",
        identity="synthetic-quarantine",
        kind="document",
        content_hash="a" * 64,
        state=ReceivedUnitState.QUARANTINE,
        safe_reason="identity_insufficient",
    )
    before = (
        Document.objects.count(),
        ReceivedUnit.objects.count(),
        IngestionPage.objects.count(),
    )

    payload = _client().get(
        "/api/documents", {"company_id": str(company.id), "family": "nfe"}
    ).json()
    serialized = str(payload)

    assert {item["outcome"] for item in payload["documents"]} == {"conflict", "quarantine"}
    assert "object_key" not in serialized
    assert "safe_error" not in serialized
    assert "secret" not in serialized
    assert (
        Document.objects.count(),
        ReceivedUnit.objects.count(),
        IngestionPage.objects.count(),
    ) == before


@pytest.mark.django_db(transaction=True)
def test_document_list_paginates_deterministically_and_maps_blocked_collection() -> None:
    company = Company.objects.create(cnpj="11222333000183", legal_name="Synthetic Company")
    flow = CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)
    first = _document(company, "first")
    second = _document(company, "second")
    flow.collection_state = CollectionExecutionState.BLOCKED
    flow.blocked_reason = "certificate_required"
    flow.save(update_fields=["collection_state", "blocked_reason", "updated_at"])

    client = _client(Role.ADMINISTRATOR)
    page = client.get("/api/documents", {"company_id": str(company.id), "limit": "1"}).json()
    next_page = client.get(
        "/api/documents",
        {"company_id": str(company.id), "limit": "1", "cursor": page["next_cursor"]},
    ).json()

    assert page["status"] == "blocked"
    assert page["documents"][0]["id"] == str(min(first.id, second.id))
    assert next_page["documents"][0]["id"] == str(max(first.id, second.id))
