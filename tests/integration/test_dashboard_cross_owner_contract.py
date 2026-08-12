from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.audit.models import AuditEvent
from nfx.backup.models import BackupSet, RestoreOperation
from nfx.certificates.models import Certificate, CertificateState
from nfx.collection.models import (
    CollectionExecution,
    CollectionExecutionState,
    CollectionOrigin,
    CollectionScope,
    IngestionOutcome,
    IngestionRecovery,
)
from nfx.companies.models import Company, CompanyFlow, CompanyStatus, FlowFamily
from nfx.documents.models import Document, DocumentSituation
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest
from nfx.jobs.models import Job, JobOutcomeKind, JobState

CURRENT_FROM = "2026-08-01"
CURRENT_TO = "2026-09-01"
PREVIOUS_FROM = "2026-07-01"
PREVIOUS_TO = "2026-08-01"
CURRENT_QUERY = {"from": CURRENT_FROM, "to": CURRENT_TO}


def _client(role: str, *, expired: bool = False) -> Client:
    user = User.objects.create(
        email=f"dashboard-gate-{role}-{uuid4().hex}@example.test",
        name="Synthetic dashboard gate user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"dashboard-gate-token-{uuid4().hex}"
    now = timezone.now()
    session = IdentitySession.objects.create(
        token_hash=_digest(token),
        user=user,
        revocation_version=user.revocation_version,
        last_activity_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    if expired:
        expired_at = now - timedelta(seconds=1)
        IdentitySession.objects.filter(id=session.id).update(
            created_at=expired_at - timedelta(minutes=30),
            expires_at=expired_at,
            last_activity_at=expired_at,
        )
    result = Client()
    result.cookies["nfx_session"] = token
    return result


def _company(name: str, status: str) -> Company:
    return Company.objects.create(
        cnpj=f"dashboard-gate-{uuid4().hex}",
        legal_name=name,
        status=status,
        deactivation_reason="synthetic" if status == CompanyStatus.DEACTIVATED else None,
    )


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
        object_key=f"dashboard-gate/{uuid4().hex}/cross-owner-secret-object-key",
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
            origin_execution_ref=f"dashboard-gate-execution-{key}",
        )
    )
    assert result.document_id is not None
    return Document.objects.get(pk=result.document_id)


def _execution(company: Company, *, state: str, created_at: datetime) -> CollectionExecution:
    row = CollectionExecution.objects.create(
        company=company,
        family=FlowFamily.NFE,
        requested_scope=CollectionScope.NFE,
        origin=CollectionOrigin.MANUAL,
        state=state,
        outcome=IngestionOutcome.UNKNOWN,
        recovery=IngestionRecovery.NONE,
        correlation_id=f"dashboard-gate-correlation-{uuid4().hex}",
        safe_summary={"cross_owner_secret": "must-not-leak"},
        safe_error="raw-provider-error-token",
    )
    CollectionExecution.objects.filter(id=row.id).update(created_at=created_at)
    row.refresh_from_db()
    return row


def _job(
    *,
    created_at: datetime,
    state: str = JobState.QUEUED,
    outcome: str = "",
    job_type: str = "synthetic.dashboard.gate",
) -> Job:
    row = Job.objects.create(
        job_type=job_type,
        logical_target="dashboard-gate-secret-target",
        payload={"cross_owner_secret": "must-not-leak"},
        idempotency_key=f"dashboard-gate-job-{uuid4().hex}",
        scheduled_at=created_at,
        state=state,
        last_outcome=outcome,
        safe_error="raw-provider-error-token",
        attempt_count=1 if outcome else 0,
        lease_owner="dashboard-gate-secret-lease" if state == JobState.RUNNING else None,
        lease_issued_at=created_at if state == JobState.RUNNING else None,
        lease_expires_at=created_at + timedelta(minutes=1) if state == JobState.RUNNING else None,
    )
    Job.objects.filter(id=row.id).update(created_at=created_at)
    return Job.objects.get(id=row.id)


def _certificate(
    company: Company, *, evaluated_at: datetime, not_after: datetime
) -> Certificate:
    return Certificate.objects.create(
        id=uuid4(),
        company=company,
        encrypted_data_key=b"encrypted-data-key",
        data_key_nonce=b"data-key-nonce",
        encrypted_password=b"encrypted-password",
        password_nonce=b"password-nonce",
        fingerprint_sha256=f"cross-owner-secret-fingerprint-{uuid4().hex}",
        certificate_cnpj=company.cnpj,
        not_before=evaluated_at - timedelta(days=1),
        not_after=not_after,
        state=CertificateState.CURRENT,
        activated_at=evaluated_at,
    )


def _seed_cross_owner_dataset(evaluated_at: datetime) -> None:
    active = _company("Empresa Gate Ativa", CompanyStatus.ACTIVE)
    registered = _company("Empresa Gate Cadastrada", CompanyStatus.REGISTERED)
    deactivated = _company("Empresa Gate Desativada", CompanyStatus.DEACTIVATED)
    running_company = _company("Empresa Gate Coleta Running", CompanyStatus.ACTIVE)
    partial_company = _company("Empresa Gate Coleta Partial", CompanyStatus.ACTIVE)
    CompanyFlow.objects.create(company=active, family=FlowFamily.NFE)
    CompanyFlow.objects.create(company=active, family=FlowFamily.NFSE)

    _document(
        active,
        key="gate-nfe-entrada-start",
        emitted_at=datetime(2026, 8, 1, 3, tzinfo=UTC),
        family=FlowFamily.NFE,
        role="entrada",
        category="document",
    )
    _document(
        active,
        key="gate-nfe-saida",
        emitted_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
        family=FlowFamily.NFE,
        role="saida",
        category="document",
    )
    _document(
        active,
        key="gate-nfse-tomada",
        emitted_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
        family=FlowFamily.NFSE,
        role="tomador",
        category="tomada",
    )
    _document(
        active,
        key="gate-nfse-prestada",
        emitted_at=datetime(2026, 8, 13, 12, tzinfo=UTC),
        family=FlowFamily.NFSE,
        role="prestador",
        category="prestada",
    )
    _document(
        active,
        key="gate-document-end-excluded",
        emitted_at=datetime(2026, 9, 1, 3, tzinfo=UTC),
        family=FlowFamily.NFE,
        role="entrada",
        category="document",
    )
    _document(
        active,
        key="gate-document-previous",
        emitted_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
        family=FlowFamily.NFE,
        role="entrada",
        category="document",
    )

    _execution(
        running_company,
        state=CollectionExecutionState.RUNNING,
        created_at=datetime(2026, 8, 1, 3, tzinfo=UTC),
    )
    _execution(
        active,
        state=CollectionExecutionState.FAILED,
        created_at=datetime(2026, 8, 10, 12, tzinfo=UTC),
    )
    _execution(
        active,
        state=CollectionExecutionState.BLOCKED,
        created_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
    )
    _execution(
        partial_company,
        state=CollectionExecutionState.PARTIAL,
        created_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
    )
    _execution(
        active,
        state=CollectionExecutionState.CONCLUDED,
        created_at=datetime(2026, 8, 13, 12, tzinfo=UTC),
    )
    _execution(
        active,
        state=CollectionExecutionState.RUNNING,
        created_at=datetime(2026, 9, 1, 3, tzinfo=UTC),
    )
    _execution(
        active,
        state=CollectionExecutionState.CONCLUDED,
        created_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
    )

    _job(created_at=datetime(2026, 8, 1, 3, tzinfo=UTC), job_type="gate-pending-start")
    _job(
        created_at=datetime(2026, 8, 31, 23, 59, 59, tzinfo=UTC),
        state=JobState.RUNNING,
        job_type="gate-pending-end",
    )
    _job(
        created_at=datetime(2026, 8, 10, 12, tzinfo=UTC),
        outcome=JobOutcomeKind.TEMPORARY,
        job_type="gate-failed",
    )
    _job(
        created_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
        state=JobState.BLOCKED,
        outcome=JobOutcomeKind.PERMANENT,
        job_type="gate-blocked",
    )
    _job(created_at=datetime(2026, 9, 1, 3, tzinfo=UTC), job_type="gate-end-excluded")
    _job(
        created_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
        outcome=JobOutcomeKind.PARTIAL,
        job_type="gate-previous",
    )

    _certificate(active, evaluated_at=evaluated_at, not_after=evaluated_at - timedelta(seconds=1))
    _certificate(registered, evaluated_at=evaluated_at, not_after=evaluated_at + timedelta(days=1))
    _certificate(
        deactivated, evaluated_at=evaluated_at, not_after=evaluated_at + timedelta(days=30)
    )
    _certificate(
        _company("Empresa Gate Certificado Atual", CompanyStatus.ACTIVE),
        evaluated_at=evaluated_at,
        not_after=evaluated_at + timedelta(days=31),
    )


def _dashboard_cards(client: Client) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    response = client.get("/api/dashboard", CURRENT_QUERY)
    assert response.status_code == 200
    payload = response.json()
    return payload, {str(card["id"]): card for card in payload["cards"]}


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("role", [Role.ADMINISTRATOR, Role.OPERATOR])
def test_cross_owner_matrix_reconciles_every_implemented_card(
    role: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluated_at = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("django.utils.timezone.now", lambda: evaluated_at)
    monkeypatch.setattr(
        "nfx.operations.dashboard._health_payload",
        lambda now: {"status": "ready", "read_only": True},
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard.backup_status",
        lambda *, now: {"status": "unavailable"},
    )
    _seed_cross_owner_dataset(evaluated_at)
    client = _client(role)
    payload, cards = _dashboard_cards(client)

    expected_ids = {
        *(
            f"documents.{key}"
            for key in ("total", "nfe", "nfse", "entrada", "saida", "tomados", "prestados")
        ),
        *(f"collections.{key}" for key in ("recent", "running", "failed", "blocked", "partial")),
        *(f"jobs.{key}" for key in ("pending", "failed", "blocked")),
        *(f"certificates.{key}" for key in ("current", "expired", "expiring")),
        "companies.active",
        "companies.inactive",
    }
    assert set(cards) == expected_ids
    assert payload["period"] == {
        "current": {"from": CURRENT_FROM, "to": CURRENT_TO},
        "previous": {"from": PREVIOUS_FROM, "to": PREVIOUS_TO},
        "boundary": "[from,to)",
    }

    owner_endpoints = (
        ("documents.", "/api/documents"),
        ("collections.", "/api/collections/executions"),
        ("jobs.", "/api/jobs/observability"),
        ("companies.", "/api/companies"),
        ("certificates.", "/api/certificates/inventory"),
    )
    for prefix, endpoint in owner_endpoints:
        for card_id, card in cards.items():
            if not card_id.startswith(prefix):
                continue
            filters = dict(card["drilldown"]["filters"])
            first = client.get(endpoint, filters)
            second = client.get(endpoint, filters)
            assert first.status_code == second.status_code == 200
            assert first.content == second.content
            owner_payload = first.json()
            assert owner_payload["total"] == card["current"]["value"]
            rows_key = {
                "documents.": "documents",
                "collections.": "executions",
                "jobs.": "jobs",
                "companies.": "companies",
                "certificates.": "certificates",
            }[prefix]
            assert len(owner_payload[rows_key]) <= owner_payload["limit"]
            if prefix in {"documents.", "collections.", "jobs."}:
                assert owner_payload["boundary"] == "[from,to)"
                assert owner_payload["filter"] == filters
            elif prefix == "companies.":
                assert owner_payload["filter"] == filters
            else:
                assert owner_payload["filter"] == filters
                assert owner_payload["evaluated_at"] == payload["evaluated_at"]
                assert owner_payload["freshness"] == {
                    "status": "fresh",
                    "evaluated_at": payload["evaluated_at"],
                    "age_seconds": 0,
                }
            serialized = first.content.decode()
            assert "cross-owner-secret" not in serialized
            assert "raw-provider-error-token" not in serialized

    period_owner_endpoints = (
        ("documents.", "/api/documents"),
        ("collections.", "/api/collections/executions"),
        ("jobs.", "/api/jobs/observability"),
    )
    for prefix, endpoint in period_owner_endpoints:
        for card_id, card in cards.items():
            if not card_id.startswith(prefix):
                continue
            filters = dict(card["drilldown"]["filters"])
            filters.update({"from": PREVIOUS_FROM, "to": PREVIOUS_TO})
            response = client.get(endpoint, filters)
            assert response.status_code == 200
            assert response.json()["total"] == card["previous"]["value"]


@pytest.mark.django_db(transaction=True)
def test_cross_owner_role_session_and_capability_matrix_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluated_at = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("django.utils.timezone.now", lambda: evaluated_at)
    monkeypatch.setattr(
        "nfx.operations.dashboard._health_payload",
        lambda now: {"status": "ready", "read_only": True},
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard.backup_status",
        lambda *, now: {"status": "unavailable"},
    )
    _seed_cross_owner_dataset(evaluated_at)
    queries = {
        "/api/dashboard": CURRENT_QUERY,
        "/api/documents": CURRENT_QUERY,
        "/api/collections/executions": {**CURRENT_QUERY, "state": "recent"},
        "/api/companies": {"lifecycle": "active"},
        "/api/certificates/inventory": {"filter": "current"},
        "/api/jobs/observability": {**CURRENT_QUERY, "filter": "pending"},
    }

    for role in (Role.ADMINISTRATOR, Role.OPERATOR):
        client = _client(role)
        assert all(client.get(path, query).status_code == 200 for path, query in queries.items())

    viewer = _client(Role.VIEWER)
    assert viewer.get("/api/dashboard", CURRENT_QUERY).status_code == 200
    viewer_payload = viewer.get("/api/dashboard", CURRENT_QUERY).json()
    viewer_cards = {str(card["id"]): card for card in viewer_payload["cards"]}
    assert not any(card_id.startswith("certificates.") for card_id in viewer_cards)
    assert viewer_cards["companies.active"]["drilldown"] is None
    assert viewer_payload["capabilities"]["certificates"] == {"status": "admin_only"}
    assert viewer_payload["capabilities"]["backup"] == {
        "status": "admin_only",
        "reason": "restricted",
    }
    assert "operational_health" not in viewer_payload
    assert viewer.get("/api/documents", CURRENT_QUERY).status_code == 200
    assert viewer.get(
        "/api/collections/executions", {**CURRENT_QUERY, "state": "recent"}
    ).status_code == 200
    assert viewer.get(
        "/api/jobs/observability", {**CURRENT_QUERY, "filter": "pending"}
    ).status_code == 200
    assert viewer.get("/api/companies", {"lifecycle": "active"}).status_code == 403
    assert viewer.get("/api/certificates/inventory", {"filter": "current"}).status_code == 403

    for client in (Client(), _client(Role.VIEWER, expired=True), _client("unauthorized")):
        for path, query in queries.items():
            response = client.get(path, query)
            assert response.status_code == 403
            assert "Empresa Gate" not in response.content.decode()
            assert "cross-owner-secret" not in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_dashboard_and_drilldown_reads_have_no_dashboard_owned_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluated_at = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("django.utils.timezone.now", lambda: evaluated_at)
    monkeypatch.setattr(
        "nfx.operations.dashboard._health_payload",
        lambda now: {"status": "ready", "read_only": True},
    )
    monkeypatch.setattr(
        "nfx.operations.dashboard.backup_status",
        lambda *, now: {"status": "unavailable"},
    )
    _seed_cross_owner_dataset(evaluated_at)
    client = _client(Role.OPERATOR)
    token = client.cookies["nfx_session"].value
    owner_reads = (
        ("/api/dashboard", CURRENT_QUERY),
        ("/api/collections/executions", {**CURRENT_QUERY, "state": "recent"}),
        ("/api/companies", {"lifecycle": "active"}),
        ("/api/certificates/inventory", {"filter": "current"}),
        ("/api/jobs/observability", {**CURRENT_QUERY, "filter": "pending"}),
    )
    before = {
        "backups": BackupSet.objects.count(),
        "restores": RestoreOperation.objects.count(),
        "jobs": Job.objects.count(),
        "collections": CollectionExecution.objects.count(),
        "companies": Company.objects.count(),
        "certificates": Certificate.objects.count(),
        "documents": Document.objects.count(),
        "audit": AuditEvent.objects.count(),
    }

    for path, query in owner_reads:
        assert client.get(path, query).status_code == 200
        assert client.get(path, query).status_code == 200

    def read_dashboard(_: int) -> bytes:
        thread_client = Client()
        thread_client.cookies["nfx_session"] = token
        response = thread_client.get("/api/dashboard", CURRENT_QUERY)
        assert response.status_code == 200
        return response.content

    with ThreadPoolExecutor(max_workers=4) as executor:
        concurrent_payloads = list(executor.map(read_dashboard, range(8)))
    assert len(set(concurrent_payloads)) == 1

    after = {
        "backups": BackupSet.objects.count(),
        "restores": RestoreOperation.objects.count(),
        "jobs": Job.objects.count(),
        "collections": CollectionExecution.objects.count(),
        "companies": Company.objects.count(),
        "certificates": Certificate.objects.count(),
        "documents": Document.objects.count(),
        "audit": AuditEvent.objects.count(),
    }
    assert {key: after[key] for key in before if key != "audit"} == {
        key: before[key] for key in before if key != "audit"
    }
    assert after["audit"] == before["audit"]

    # P7's document-consultation owner intentionally audits reads. The gate
    # excludes that owner-prescribed evidence while keeping dashboard-owned
    # persistence and every other read path side-effect free.
    first_document = client.get("/api/documents", CURRENT_QUERY)
    second_document = client.get("/api/documents", CURRENT_QUERY)
    assert first_document.status_code == second_document.status_code == 200
    assert first_document.content == second_document.content
    assert AuditEvent.objects.count() == before["audit"] + 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("source", "prefix"),
    [
        ("_company_counts", "companies."),
        ("_document_counts", "documents."),
        ("_collection_counts", "collections."),
        ("_job_counts", "jobs."),
        ("_certificate_counts", "certificates."),
    ],
)
def test_owner_failure_has_unknown_freshness_and_isolated_dashboard_degradation(
    source: str, prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluated_at = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("django.utils.timezone.now", lambda: evaluated_at)
    monkeypatch.setattr(
        "nfx.operations.dashboard._health_payload",
        lambda now: {"status": "ready", "read_only": True},
    )
    _seed_cross_owner_dataset(evaluated_at)
    monkeypatch.setattr(
        f"nfx.operations.dashboard.{source}",
        lambda *args: (_ for _ in ()).throw(RuntimeError("raw provider failure")),
    )

    response = _client(Role.OPERATOR).get("/api/dashboard", CURRENT_QUERY)
    assert response.status_code == 200
    cards = {str(card["id"]): card for card in response.json()["cards"]}
    affected = [card for card_id, card in cards.items() if card_id.startswith(prefix)]
    unrelated = [card for card_id, card in cards.items() if not card_id.startswith(prefix)]
    assert affected
    assert all(card["status"] == "unavailable" for card in affected)
    assert all(card["current"]["value"] is None for card in affected)
    assert all(card["current"]["freshness"]["status"] == "unknown" for card in affected)
    assert all(card["status"] != "unavailable" for card in unrelated)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("path", "query"),
    [
        ("/api/dashboard", {"from": CURRENT_FROM}),
        ("/api/documents", {"from": CURRENT_FROM}),
        ("/api/collections/executions", {**CURRENT_QUERY, "state": "recent"}),
        ("/api/jobs/observability", {**CURRENT_QUERY, "filter": "pending"}),
    ],
)
def test_period_owner_contracts_reject_incomplete_or_ambiguous_bounds(
    path: str, query: dict[str, str]
) -> None:
    client = _client(Role.OPERATOR)
    incomplete = dict(query)
    incomplete.pop("to", None)
    assert client.get(path, incomplete).status_code == 400
    assert client.get(
        path,
        {**query, "from": "2026-09-01", "to": "2026-08-01"},
    ).status_code == 400
    repeated = [("from", CURRENT_FROM), ("from", "2026-08-02"), ("to", CURRENT_TO)]
    if path == "/api/collections/executions":
        repeated.append(("state", "recent"))
    if path == "/api/jobs/observability":
        repeated.append(("filter", "pending"))
    assert client.get(path, repeated).status_code == 400
