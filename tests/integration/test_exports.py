from __future__ import annotations

import hashlib
import io
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zipfile import ZipFile

import pytest
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.artifacts.storage import ArtifactStorageService, ObjectMetadata
from nfx.companies.models import Company
from nfx.documents.models import Document, DocumentEvidence
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.exports.models import Export, ExportItemState, ExportState
from nfx.exports.services import compose_export, request_export
from nfx.identity.models import Role, User
from nfx.identity.services import SessionIdentity


class MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata:
        payload = b"".join(chunks)
        if len(payload) > maximum_size:
            raise ValueError("too large")
        self.objects[object_key] = (payload, content_type)
        return ObjectMetadata(len(payload), hashlib.sha256(payload).hexdigest(), content_type)

    def head(self, object_key: str) -> ObjectMetadata | None:
        payload = self.objects.get(object_key)
        return None if payload is None else ObjectMetadata(
            len(payload[0]), hashlib.sha256(payload[0]).hexdigest(), payload[1]
        )

    def read(self, object_key: str) -> io.BytesIO | None:
        payload = self.objects.get(object_key)
        return None if payload is None else io.BytesIO(payload[0])

    def list_keys(self, prefix: str) -> Iterator[str]:
        yield from (key for key in self.objects if key.startswith(prefix))

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


def _actor(role: str = Role.VIEWER) -> SessionIdentity:
    user = User.objects.create(
        email=f"export-{uuid4().hex}@example.test",
        name="Synthetic export user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    return SessionIdentity(str(user.id), user.email, user.name, user.role)


def _document(store: MemoryObjectStore, company: Company, key: str) -> Document:
    payload = f"<synthetic id='{key}'/>".encode()
    artifact = Artifact.objects.create(
        logical_class="fiscal_original",
        logical_key=f"source-{key}",
        object_key=f"artifacts/{uuid4().hex}/v1",
        digest=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        declared_mime_type="application/xml",
        detected_mime_type="application/xml",
        state=ArtifactState.FINALIZED,
    )
    store.objects[artifact.object_key] = (payload, "application/xml")
    result = persist_document(
        DocumentInput(
            company_id=company.id,
            family="nfe",
            role="entrada",
            category="document",
            source="simulator",
            flow="distribution",
            identity=FiscalIdentity(official_key=key),
            emitted_at=datetime(2026, 8, 10, 12, tzinfo=UTC),
            authorized_at=datetime(2026, 8, 10, 12, 1, tzinfo=UTC),
            situation="authorized",
            artifact_id=artifact.id,
            origin_execution_ref=f"execution-{key}",
        )
    )
    assert result.document_id
    return Document.objects.get(pk=result.document_id)


@pytest.mark.django_db(transaction=True)
def test_export_freezes_selection_composes_verified_zip_and_is_idempotent() -> None:
    store = MemoryObjectStore()
    company = Company.objects.create(cnpj="11222333000181", legal_name="Empresa Exportação")
    first = _document(store, company, "export-first")
    actor = _actor()
    identity = request_export(actor=actor, filters={"family": "nfe"}, idempotency_key="same-key")
    duplicate = request_export(actor=actor, filters={"family": "nfe"}, idempotency_key="same-key")

    assert duplicate.duplicate is True
    assert duplicate.export.id == identity.export.id
    assert Export.objects.get(pk=identity.export.id).expected_count == 1
    assert list(identity.export.items.values_list("document_id", flat=True)) == [first.id]

    outcome = compose_export(
        identity.export.id,
        storage=ArtifactStorageService(store, maximum_size=100 * 1024 * 1024),
    )
    export = Export.objects.get(pk=identity.export.id)
    assert outcome.kind == "success"
    assert export.state == ExportState.AVAILABLE
    assert export.zip_artifact_id is not None
    zip_bytes = store.objects[export.zip_artifact.object_key][0]
    with ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert len(archive.namelist()) == 1
        assert archive.read(archive.namelist()[0]).startswith(b"<synthetic")


@pytest.mark.django_db(transaction=True)
def test_export_missing_source_is_explicit_partial_and_never_complete() -> None:
    store = MemoryObjectStore()
    company = Company.objects.create(cnpj="11222333000182", legal_name="Empresa Parcial")
    document = _document(store, company, "export-missing")
    artifact_id = DocumentEvidence.objects.get(document=document).artifact_id
    artifact = Artifact.objects.get(pk=artifact_id)
    del store.objects[artifact.object_key]
    actor = _actor()
    result = request_export(actor=actor, filters={}, idempotency_key="missing-key")
    compose_export(
        result.export.id,
        storage=ArtifactStorageService(store, maximum_size=100 * 1024 * 1024),
    )

    export = Export.objects.get(pk=result.export.id)
    assert export.state == ExportState.FAILED
    assert export.zip_artifact_id is None
    assert export.items.get().state == ExportItemState.MISSING
    assert Artifact.objects.filter(pk=artifact_id).exists()


@pytest.mark.django_db(transaction=True)
def test_export_expiry_is_24_hours_from_request() -> None:
    actor = _actor()
    requested = datetime(2026, 8, 10, 12, tzinfo=UTC)
    result = request_export(actor=actor, filters={}, idempotency_key="expiry-key", now=requested)
    assert result.export.expires_at == requested + timedelta(hours=24)
    assert timezone.is_aware(result.export.expires_at)
