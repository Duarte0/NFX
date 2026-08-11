from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.audit.models import AuditEvent
from nfx.companies.models import Company, CompanyFlow, FlowFamily
from nfx.documents.models import Document, DocumentSituation
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest


def _client(role: str = Role.VIEWER) -> Client:
    user = User.objects.create(
        email=f"dashboard-documents-{uuid4().hex}@example.test",
        name="Synthetic dashboard document reader",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"dashboard-documents-token-{uuid4().hex}"
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


def _document(
    company: Company,
    *,
    key: str,
    emitted_at: datetime,
    family: str,
    role: str,
    category: str,
) -> Document:
    payload = key.encode()
    artifact = Artifact.objects.create(
        logical_class="fiscal_original",
        logical_key=key,
        object_key=f"artifacts/{uuid4().hex}/v1",
        digest_algorithm="sha256",
        digest=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        declared_mime_type="application/xml",
        detected_mime_type="application/xml",
        state=ArtifactState.FINALIZED,
    )
    result = persist_document(
        DocumentInput(
            company_id=company.id,
            family=family,
            role=role,
            category=category,
            source="simulator",
            flow="distribution",
            identity=FiscalIdentity(official_key=key),
            emitted_at=emitted_at,
            authorized_at=emitted_at + timedelta(minutes=1),
            situation=DocumentSituation.AUTHORIZED,
            artifact_id=artifact.id,
            origin_execution_ref=f"execution-{key}",
        )
    )
    assert result.document_id is not None
    return Document.objects.get(pk=result.document_id)


@pytest.mark.django_db(transaction=True)
def test_document_cards_reconcile_with_canonical_archive_filters() -> None:
    company = Company.objects.create(cnpj="11222333000181", legal_name="Empresa Documento")
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFSE)
    start = datetime(2026, 8, 1, 3, tzinfo=UTC)
    end = datetime(2026, 9, 1, 3, tzinfo=UTC)
    _document(
        company,
        key="nfe-entrada",
        emitted_at=start,
        family=FlowFamily.NFE,
        role="entrada",
        category="document",
    )
    _document(
        company,
        key="nfe-saida",
        emitted_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
        family=FlowFamily.NFE,
        role="saida",
        category="document",
    )
    _document(
        company,
        key="nfse-tomada",
        emitted_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
        family=FlowFamily.NFSE,
        role="tomador",
        category="tomada",
    )
    _document(
        company,
        key="nfse-prestada",
        emitted_at=datetime(2026, 8, 13, 12, tzinfo=UTC),
        family=FlowFamily.NFSE,
        role="prestador",
        category="prestada",
    )
    _document(
        company,
        key="at-end-is-excluded",
        emitted_at=end,
        family=FlowFamily.NFE,
        role="entrada",
        category="document",
    )

    client = _client()
    dashboard = client.get(
        "/api/dashboard", {"from": "2026-08-01", "to": "2026-09-01"}
    )
    assert dashboard.status_code == 200
    cards = {card["id"]: card for card in dashboard.json()["cards"]}
    expected = {
        "documents.total": 4,
        "documents.nfe": 2,
        "documents.nfse": 2,
        "documents.entrada": 1,
        "documents.saida": 1,
        "documents.tomados": 1,
        "documents.prestados": 1,
    }
    for card_id, total in expected.items():
        card = cards[card_id]
        filters = card["drilldown"]["filters"]
        assert filters["from"] == "2026-08-01"
        assert filters["to"] == "2026-09-01"
        response = client.get("/api/documents", filters)
        assert response.status_code == 200
        payload = response.json()
        assert payload["filter"] == filters
        assert payload["boundary"] == "[from,to)"
        assert payload["total"] == total == card["current"]["value"]

    assert cards["documents.tomados"]["drilldown"]["filters"]["nfse_category"] == "tomada"
    assert cards["documents.prestados"]["drilldown"]["filters"]["nfse_category"] == "prestada"
    assert "tomado" not in cards["documents.tomados"]["drilldown"]["href"]
    assert "prestado" not in cards["documents.prestados"]["drilldown"]["href"]
    assert start < end


@pytest.mark.django_db(transaction=True)
def test_document_archive_rejects_invalid_period_and_keeps_quarantine_out_of_total() -> None:
    company = Company.objects.create(cnpj="11222333000182", legal_name="Empresa Limites")
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)
    before = (Document.objects.count(), AuditEvent.objects.count())
    client = _client()

    for params in (
        {"from": "2026-08-01"},
        {"from": "2026-09-01", "to": "2026-08-01"},
        {"from": "2026-01-01", "to": "2027-02-01"},
        [("from", "2026-08-01"), ("from", "2026-08-02"), ("to", "2026-09-01")],
    ):
        response = client.get("/api/documents", params)
        assert response.status_code == 400

    assert (Document.objects.count(), AuditEvent.objects.count()) == before


@pytest.mark.django_db(transaction=True)
def test_document_archive_source_failure_is_safe_and_not_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.documents.views.list_document_status",
        lambda params: (_ for _ in ()).throw(RuntimeError("provider details")),
    )

    response = _client().get(
        "/api/documents", {"from": "2026-08-01", "to": "2026-09-01", "family": "nfe"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Não foi possível consultar os documentos."}
    assert "provider details" not in response.content.decode()
