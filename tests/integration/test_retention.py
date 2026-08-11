from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.artifacts.storage import ArtifactStorageService, ObjectMetadata
from nfx.audit.models import AuditEvent
from nfx.companies.models import Company
from nfx.documents.models import (
    Document,
    DocumentEvidence,
    DocumentRender,
    DocumentRenderState,
    PdfRepresentation,
)
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest
from nfx.retention.deletion import confirmation_for, execute_deletion
from nfx.retention.models import DeletionOperation, DeletionOperationState


def _client(role: str, *, enforce_csrf_checks: bool = False) -> Client:
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
    client = Client(enforce_csrf_checks=enforce_csrf_checks)
    client.cookies["nfx_session"] = token
    return client


def _document(
    *,
    family: str = "nfe",
    emitted_at: datetime | None = None,
    authorized_at: datetime | None = None,
) -> Document:
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
            emitted_at=emitted_at or datetime(2026, 8, 15, 12, tzinfo=UTC),
            authorized_at=authorized_at,
            situation="authorized",
            artifact_id=artifact.id,
            origin_execution_ref="execution-retention-1",
        )
    )
    assert result.document_id
    return Document.objects.get(pk=result.document_id)


class MemoryDeleteStore:
    def __init__(self, values: dict[str, bytes]) -> None:
        self.values = values
        self.deleted: list[str] = []

    def head(self, object_key: str) -> ObjectMetadata | None:
        payload = self.values.get(object_key)
        if payload is None:
            return None
        return ObjectMetadata(len(payload), sha256(payload).hexdigest(), "application/xml")

    def delete(self, object_key: str) -> None:
        self.deleted.append(object_key)
        self.values.pop(object_key, None)


def _deletion_request(
    client: Client,
    document: Document,
    scope_hash: str,
    reason: str = "Prazo fiscal encerrado",
) -> object:
    return client.post(
        f"/api/retention/documents/{document.id}/deletion",
        data={
            "scope_hash": scope_hash,
            "scope_version": "scope-v1",
            "confirmation": confirmation_for(document.id, scope_hash),
            "reason": reason,
        },
        content_type="application/json",
    )


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
    assert _deletion_request(admin, document, scope_hash).status_code == 409


@pytest.mark.django_db(transaction=True)
def test_controlled_deletion_requires_exact_scope_reason_and_admin_is_idempotent() -> None:
    document = _document(
        emitted_at=datetime(2010, 8, 15, 12, tzinfo=UTC),
        authorized_at=datetime(2010, 8, 15, 12, tzinfo=UTC),
    )
    admin = _client(Role.ADMINISTRATOR)
    preview = admin.get(f"/api/retention/documents/{document.id}/preview").json()
    scope_hash = preview["scope"]["hash"]

    missing_reason = _deletion_request(admin, document, scope_hash, reason="")
    assert missing_reason.status_code == 400
    assert not DeletionOperation.objects.exists()

    retained = _document(authorized_at=datetime(2026, 8, 15, 12, tzinfo=UTC))
    retained_preview = admin.get(f"/api/retention/documents/{retained.id}/preview").json()
    retained_request = _deletion_request(admin, retained, retained_preview["scope"]["hash"])
    assert retained_request.status_code == 409
    assert retained_request.json()["reason_code"] == "within_retention_period"

    DocumentEvidence.objects.update(conflicting=True)
    stale = _deletion_request(admin, document, scope_hash)
    assert stale.status_code == 409
    assert stale.json()["reason_code"] == "scope_changed"
    DocumentEvidence.objects.update(conflicting=False)

    csrf_admin = _client(Role.ADMINISTRATOR, enforce_csrf_checks=True)
    csrf_admin.get("/api/auth/csrf")
    assert _deletion_request(csrf_admin, document, scope_hash).status_code == 403

    requested = _deletion_request(admin, document, scope_hash)
    assert requested.status_code == 202
    operation_id = requested.json()["id"]
    assert requested.json()["state"] == DeletionOperationState.PENDING
    assert "object_key" not in requested.content.decode()

    duplicate = _deletion_request(admin, document, scope_hash)
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == operation_id
    assert DeletionOperation.objects.filter(target_document_id=document.id).count() == 1

    assert _deletion_request(_client(Role.OPERATOR), document, scope_hash).status_code == 403
    assert _deletion_request(_client(Role.VIEWER), document, scope_hash).status_code == 403
    assert admin.get(f"/api/retention/deletions/{operation_id}").status_code == 200
    assert _client(Role.OPERATOR).get(f"/api/retention/deletions/{operation_id}").status_code == 403


@pytest.mark.django_db(transaction=True)
def test_controlled_deletion_removes_complete_set_and_preserves_safe_audit() -> None:
    document = _document(
        emitted_at=datetime(2010, 8, 15, 12, tzinfo=UTC),
        authorized_at=datetime(2010, 8, 15, 12, tzinfo=UTC),
    )
    artifact = DocumentEvidence.objects.get(document=document).artifact
    pdf_payload = b"%PDF-synthetic"
    derived = Artifact.objects.create(
        logical_class="document_derived_pdf",
        logical_key=f"retention-pdf-{uuid4().hex}",
        object_key=f"artifacts/{uuid4().hex}/v1",
        digest=sha256(pdf_payload).hexdigest(),
        size_bytes=len(pdf_payload),
        declared_mime_type="application/pdf",
        detected_mime_type="application/pdf",
        state=ArtifactState.FINALIZED,
    )
    render = DocumentRender.objects.create(
        document=document,
        source_artifact=artifact,
        artifact=derived,
        pdf_type=PdfRepresentation.DANFE,
        representation=PdfRepresentation.DANFE,
        renderer_id="synthetic",
        renderer_version="1",
        source_digest=artifact.digest,
        digest=derived.digest,
        size_bytes=derived.size_bytes,
        state=DocumentRenderState.FINALIZED,
        finalized_at=timezone.now(),
    )
    store = MemoryDeleteStore(
        {artifact.object_key: b"<synthetic/>", derived.object_key: pdf_payload}
    )
    admin = _client(Role.ADMINISTRATOR)
    preview = admin.get(f"/api/retention/documents/{document.id}/preview").json()
    response = _deletion_request(admin, document, preview["scope"]["hash"])
    assert response.status_code == 202

    operation = execute_deletion(
        response.json()["id"], storage=ArtifactStorageService(store)
    )

    assert operation.state == DeletionOperationState.COMPLETED, operation.safe_error
    assert not Document.objects.filter(pk=document.id).exists()
    assert not DocumentRender.objects.filter(pk=render.id).exists()
    assert not Artifact.objects.filter(pk__in=(artifact.id, derived.id)).exists()
    assert set(store.deleted) == {artifact.object_key, derived.object_key}
    assert "<synthetic/>" not in str(operation.checkpoint)
    audit = AuditEvent.objects.filter(entity_id=str(document.id), action="document.delete")
    assert {event.result for event in audit} >= {"requested", "completed"}
    assert all("<synthetic/>" not in str(event.context) for event in audit)
    assert all("object_key" not in str(event.context) for event in audit)


@pytest.mark.django_db(transaction=True)
def test_controlled_deletion_missing_object_is_recovery_required_and_resumable() -> None:
    document = _document(
        emitted_at=datetime(2010, 8, 15, 12, tzinfo=UTC),
        authorized_at=datetime(2010, 8, 15, 12, tzinfo=UTC),
    )
    artifact = DocumentEvidence.objects.get(document=document).artifact
    store = MemoryDeleteStore({})
    admin = _client(Role.ADMINISTRATOR)
    preview = admin.get(f"/api/retention/documents/{document.id}/preview").json()
    response = _deletion_request(admin, document, preview["scope"]["hash"])

    failed = execute_deletion(response.json()["id"], storage=ArtifactStorageService(store))
    assert failed.state == DeletionOperationState.RECOVERY_REQUIRED
    assert Document.objects.filter(pk=document.id).exists()
    assert admin.get(f"/api/retention/deletions/{failed.id}").json()["state"] == "recovery_required"

    resumed_request = admin.post(f"/api/retention/deletions/{failed.id}/resume")
    assert resumed_request.status_code == 202
    assert resumed_request.json()["state"] == DeletionOperationState.PENDING
    store.values[artifact.object_key] = b"<synthetic/>"
    resumed = execute_deletion(failed.id, storage=ArtifactStorageService(store))
    assert resumed.state == DeletionOperationState.COMPLETED, resumed.safe_error
    assert not Document.objects.filter(pk=document.id).exists()
