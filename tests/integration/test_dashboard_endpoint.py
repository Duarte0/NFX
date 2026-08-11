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
from nfx.backup.models import BackupSet, RestoreOperation
from nfx.companies.models import Company, CompanyFlow, CompanyStatus, FlowFamily
from nfx.documents.models import DocumentSituation
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest
from nfx.jobs.models import Job


def _client(role: str) -> Client:
    user = User.objects.create(
        email=f"dashboard-{role}-{uuid4().hex}@example.test",
        name="Synthetic dashboard user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"dashboard-token-{uuid4().hex}"
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


def _document(company: Company, *, key: str, role: str, family: str = FlowFamily.NFE) -> None:
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
            category="document",
            source="simulator",
            flow="distribution",
            identity=FiscalIdentity(official_key=key),
            emitted_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
            authorized_at=datetime(2026, 8, 10, 12, 1, tzinfo=UTC),
            situation=DocumentSituation.AUTHORIZED,
            artifact_id=artifact.id,
            origin_execution_ref=f"execution-{key}",
        )
    )
    assert result.document_id is not None


@pytest.mark.django_db(transaction=True)
def test_dashboard_returns_period_cards_real_zero_and_explicit_capabilities() -> None:
    company = Company.objects.create(
        cnpj="11222333000181", legal_name="Empresa Dashboard", status=CompanyStatus.ACTIVE
    )
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)
    _document(company, key="dashboard-nfe", role="entrada")

    response = _client(Role.VIEWER).get(
        "/api/dashboard", {"from": "2026-08-01", "to": "2026-09-01"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert payload["period"] == {
        "current": {"from": "2026-08-01", "to": "2026-09-01"},
        "previous": {"from": "2026-07-01", "to": "2026-08-01"},
        "boundary": "[from,to)",
    }
    cards = {card["id"]: card for card in payload["cards"]}
    assert cards["documents.total"]["current"]["value"] == 1
    assert cards["documents.nfe"]["current"]["value"] == 1
    assert cards["documents.nfse"]["current"]["value"] == 0
    assert cards["documents.nfse"]["current"]["status"] == "zero"
    assert cards["documents.total"]["previous"]["value"] == 0
    assert cards["documents.nfe"]["drilldown"] == {
        "href": "?family=nfe#documentos",
        "filters": {"family": "nfe"},
    }
    assert payload["capabilities"]["fiscal_sources"]["status"] == "unavailable"
    assert payload["capabilities"]["rendering"] == {
        "status": "available",
        "reason": "brazilfiscalreport:1.0.1",
    }
    assert payload["capabilities"]["backup"] == {
        "status": "admin_only",
        "reason": "restricted",
    }
    assert "operational_health" not in payload
    assert all("dependencies" not in card for card in payload["cards"])


@pytest.mark.django_db(transaction=True)
def test_dashboard_rejects_anonymous_and_invalid_period() -> None:
    assert Client().get("/api/dashboard").status_code == 403
    assert _client(Role.VIEWER).get(
        "/api/dashboard", {"from": "2026-08-01", "to": "2026-08-01"}
    ).status_code == 400


@pytest.mark.django_db(transaction=True)
def test_dashboard_admin_health_is_separate_from_fiscal_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.operations.dashboard._health_payload",
        lambda now: {
            "status": "degraded",
            "read_only": True,
            "dependencies": {"minio": "unavailable"},
        },
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard.backup_status",
        lambda *, now: {
            "status": "success",
            "latest_backup": {
                "id": "synthetic-backup-id",
                "state": "complete",
                "safe_error": "",
            },
            "latest_success_age_seconds": 60,
            "retention": {"daily": 2, "weekly": 1, "monthly": 1},
            "latest_restore": {
                "id": "synthetic-restore-id",
                "state": "success",
                "safe_error": "",
            },
        },
    )

    payload = _client(Role.ADMINISTRATOR).get("/api/dashboard").json()

    assert payload["operational_health"] == {
        "status": "degraded",
        "read_only": True,
        "dependencies": {"minio": "unavailable"},
        "backup": {
            "status": "success",
            "latest_backup": {"state": "complete", "safe_error": ""},
            "latest_success_age_seconds": 60,
            "retention": {"daily": 2, "weekly": 1, "monthly": 1},
            "latest_restore": {"state": "success", "safe_error": ""},
        },
    }
    assert payload["capabilities"]["operational_health"]["status"] == "available"


@pytest.mark.django_db(transaction=True)
def test_dashboard_backup_is_admin_only_without_source_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def source_must_not_be_read(*, now: object) -> dict[str, object]:
        raise AssertionError("backup source must not be read for non-administrators")

    monkeypatch.setattr("nfx.operations.dashboard.backup_status", source_must_not_be_read)

    for role in (Role.OPERATOR, Role.VIEWER):
        payload = _client(role).get("/api/dashboard").json()

        assert "operational_health" not in payload
        assert payload["capabilities"]["backup"] == {
            "status": "admin_only",
            "reason": "restricted",
        }
        assert "latest_success_age_seconds" not in str(payload)
        assert "latest_restore" not in str(payload)


@pytest.mark.django_db(transaction=True)
def test_repeated_admin_dashboard_reads_do_not_create_operational_records() -> None:
    before = {
        "backups": BackupSet.objects.count(),
        "restores": RestoreOperation.objects.count(),
        "jobs": Job.objects.count(),
        "audit": AuditEvent.objects.count(),
    }

    client = _client(Role.ADMINISTRATOR)
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/dashboard").status_code == 200

    assert {
        "backups": BackupSet.objects.count(),
        "restores": RestoreOperation.objects.count(),
        "jobs": Job.objects.count(),
        "audit": AuditEvent.objects.count(),
    } == before
