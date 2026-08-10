from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from nfx.artifacts.models import Artifact, ArtifactState
from nfx.audit.services import AuditService
from nfx.documents.models import (
    Document,
    DocumentEvent,
    DocumentEventEvidence,
    DocumentEvidence,
    DocumentFamily,
    DocumentRelationship,
    DocumentSituation,
    DocumentState,
)

_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
_IDENTIFIER = re.compile(r"^[A-Z0-9]{1,255}$")


class InvalidDocumentInput(ValueError):
    """Safe domain validation failure; input values are never included in its text."""


class DocumentPersistenceStatus(StrEnum):
    PERSISTED = "persisted"
    REPLAY = "replay"
    QUARANTINE = "quarantine"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class FiscalIdentity:
    official_key: str | None = None
    external_id: str | None = None
    number: str | None = None
    series: str | None = None
    issuer_tax_id: str | None = None


@dataclass(frozen=True)
class IdentitySelection:
    kind: str
    value: str


@dataclass
class DocumentInput:
    company_id: UUID | str
    family: str
    role: str
    category: str
    source: str
    flow: str
    identity: FiscalIdentity
    emitted_at: datetime
    artifact_id: UUID | str
    origin_execution_ref: str
    authorized_at: datetime | None = None
    situation: str = DocumentSituation.UNKNOWN
    correlation_id: str = ""
    kind: Literal["document", "event", "substitution"] = "document"
    parent_document_id: UUID | str | None = None
    relationship_type: str | None = None

    def validate(self) -> None:
        try:
            UUID(str(self.company_id))
            UUID(str(self.artifact_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise InvalidDocumentInput("Document references are invalid") from exc
        if self.family not in {choice.value for choice in DocumentFamily}:
            raise InvalidDocumentInput("Document family is unsupported")
        if self.kind not in {"document", "event", "substitution"}:
            raise InvalidDocumentInput("Document kind is unsupported")
        for value in (self.role, self.category, self.source, self.flow, self.origin_execution_ref):
            _validate_reference(value)
        if self.correlation_id:
            _validate_reference(self.correlation_id)
        if not isinstance(self.identity, FiscalIdentity):
            raise InvalidDocumentInput("Document identity is invalid")
        derive_competence(self.emitted_at)
        if self.authorized_at is not None:
            _require_aware(self.authorized_at)
            if self.authorized_at < self.emitted_at:
                raise InvalidDocumentInput("Authorization precedes emission")
        if self.situation not in {choice.value for choice in DocumentSituation}:
            raise InvalidDocumentInput("Document situation is unsupported")
        if self.kind in {"event", "substitution"}:
            if self.parent_document_id is None:
                raise InvalidDocumentInput("Event parent is required")
            try:
                UUID(str(self.parent_document_id))
            except (TypeError, ValueError, AttributeError) as exc:
                raise InvalidDocumentInput("Event parent is invalid") from exc
            if self.relationship_type not in {choice.value for choice in DocumentRelationship}:
                raise InvalidDocumentInput("Event relationship is unsupported")
        elif self.parent_document_id is not None or self.relationship_type is not None:
            raise InvalidDocumentInput("Document parent relationship is unsupported")


@dataclass(frozen=True)
class DocumentPersistenceResult:
    status: DocumentPersistenceStatus
    document_id: UUID | None = None
    event_id: UUID | None = None
    evidence_id: UUID | None = None
    reason_code: str | None = None


@dataclass(frozen=True)
class EvidenceAttachmentResult:
    status: DocumentPersistenceStatus
    evidence_id: UUID


def attach_document_evidence(
    document_id: UUID | str, artifact_id: UUID | str
) -> EvidenceAttachmentResult:
    """Attach a finalized artifact without changing document identity or status."""
    artifact = _artifact(artifact_id)
    try:
        document_uuid = UUID(str(document_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidDocumentInput("Document reference is invalid") from exc
    with transaction.atomic():
        document = Document.objects.select_for_update().filter(pk=document_uuid).first()
        if document is None:
            raise InvalidDocumentInput("Document is unavailable")
        existing = DocumentEvidence.objects.filter(
            document=document, artifact=artifact
        ).first()
        if existing is not None:
            return EvidenceAttachmentResult(DocumentPersistenceStatus.REPLAY, existing.id)
        evidence = DocumentEvidence.objects.create(
            document=document,
            artifact=artifact,
            digest=artifact.digest,
            size_bytes=_artifact_size(artifact),
        )
        AuditService().append(
            action="document.evidence_attached",
            entity_type="document",
            entity_id=str(document.id),
            result=DocumentPersistenceStatus.PERSISTED.value,
            reason="followup_evidence",
            correlation_id=document.correlation_id,
            context={
                "family": document.family,
                "source": document.source,
                "flow": document.flow,
                "artifact_digest_prefix": artifact.digest[:16],
            },
        )
        return EvidenceAttachmentResult(DocumentPersistenceStatus.PERSISTED, evidence.id)


def _validate_reference(value: str) -> str:
    if not isinstance(value, str) or not _SAFE_REFERENCE.fullmatch(value):
        raise InvalidDocumentInput("Document reference is invalid")
    return value


def _normalize_identifier(value: str, *, label: str) -> str:
    normalized = "".join(character for character in value.upper() if character.isalnum())
    if not _IDENTIFIER.fullmatch(normalized):
        raise InvalidDocumentInput(f"{label} identity is invalid")
    return normalized


def select_strongest_identity(identity: FiscalIdentity) -> IdentitySelection:
    if identity.official_key:
        return IdentitySelection(
            "official_key", _normalize_identifier(identity.official_key, label="Official")
        )
    if identity.external_id:
        return IdentitySelection(
            "external_id", _normalize_identifier(identity.external_id, label="External")
        )
    if identity.number and identity.series and identity.issuer_tax_id:
        parts = (
            _normalize_identifier(identity.number, label="Number"),
            _normalize_identifier(identity.series, label="Series"),
            _normalize_identifier(identity.issuer_tax_id, label="Issuer"),
        )
        return IdentitySelection("number_series_issuer", "|".join(parts))
    raise InvalidDocumentInput("Fiscal identity is insufficient")


def derive_competence(emitted_at: datetime) -> date:
    _require_aware(emitted_at)
    return timezone.localtime(emitted_at).date()


def _require_aware(value: datetime) -> None:
    if not timezone.is_aware(value):
        raise InvalidDocumentInput("Fiscal timestamps require timezone awareness")


def _artifact(artifact_id: UUID | str) -> Artifact:
    try:
        artifact = Artifact.objects.get(pk=artifact_id)
    except Artifact.DoesNotExist as exc:
        raise InvalidDocumentInput("Original artifact is unavailable") from exc
    if (
        artifact.state != ArtifactState.FINALIZED
        or not artifact.digest
        or not re.fullmatch(r"[0-9a-f]{64}", artifact.digest)
        or artifact.size_bytes is None
        or artifact.size_bytes < 0
    ):
        raise InvalidDocumentInput("Original artifact is unavailable")
    return artifact


def _artifact_size(artifact: Artifact) -> int:
    if artifact.size_bytes is None:
        raise InvalidDocumentInput("Original artifact is unavailable")
    return artifact.size_bytes


def _identity_key(*, company_id: UUID, data: DocumentInput, selection: IdentitySelection) -> str:
    value = "|".join(
        (
            str(company_id),
            data.family,
            data.role,
            data.category,
            data.source,
            data.flow,
            selection.kind,
            selection.value,
        )
    )
    if len(value) > 1024:
        raise InvalidDocumentInput("Fiscal identity context is too long")
    return value


def _audit(
    *,
    action: str,
    result: DocumentPersistenceStatus,
    entity_type: str,
    entity_id: UUID | None,
    correlation_id: str,
    reason_code: str | None,
    data: DocumentInput,
    digest: str | None,
) -> None:
    AuditService().append(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else "",
        result=result.value,
        correlation_id=data.correlation_id or correlation_id,
        reason=reason_code or "",
        context={
            "family": data.family,
            "source": data.source,
            "flow": data.flow,
            "status": result.value,
            "artifact_digest_prefix": digest[:16] if digest else "",
        },
    )


def persist_document(data: DocumentInput) -> DocumentPersistenceResult:
    data.validate()
    company_id = UUID(str(data.company_id))
    artifact = _artifact(data.artifact_id)
    try:
        selection = select_strongest_identity(data.identity)
    except InvalidDocumentInput as exc:
        if str(exc) != "Fiscal identity is insufficient":
            raise
        _audit(
            action="document.quarantine",
            result=DocumentPersistenceStatus.QUARANTINE,
            entity_type="document" if data.kind == "document" else "event",
            entity_id=None,
            correlation_id="",
            reason_code="identity_insufficient",
            data=data,
            digest=artifact.digest,
        )
        return DocumentPersistenceResult(
            DocumentPersistenceStatus.QUARANTINE, reason_code="identity_insufficient"
        )

    if data.kind in {"event", "substitution"}:
        return _persist_event(data, company_id, artifact, selection)
    return _persist_document(data, company_id, artifact, selection)


def _persist_document(
    data: DocumentInput, company_id: UUID, artifact: Artifact, selection: IdentitySelection
) -> DocumentPersistenceResult:
    identity_key = _identity_key(company_id=company_id, data=data, selection=selection)
    size_bytes = _artifact_size(artifact)
    for attempt in range(2):
        try:
            with transaction.atomic():
                existing = (
                    Document.objects.select_for_update().filter(identity_key=identity_key).first()
                )
                if existing:
                    evidence = (
                        DocumentEvidence.objects.filter(document=existing, digest=artifact.digest)
                        .order_by("created_at")
                        .first()
                    )
                    if evidence:
                        _audit(
                            action="document.replay",
                            result=DocumentPersistenceStatus.REPLAY,
                            entity_type="document",
                            entity_id=existing.id,
                            correlation_id=identity_key,
                            reason_code=None,
                            data=data,
                            digest=artifact.digest,
                        )
                        return DocumentPersistenceResult(
                            DocumentPersistenceStatus.REPLAY,
                            document_id=existing.id,
                            evidence_id=evidence.id,
                        )
                    evidence = DocumentEvidence.objects.create(
                        document=existing,
                        artifact=artifact,
                        digest=artifact.digest,
                        size_bytes=size_bytes,
                        conflicting=True,
                    )
                    Document.objects.filter(pk=existing.id).update(
                        state=DocumentState.CONFLICT, updated_at=timezone.now()
                    )
                    _audit(
                        action="document.conflict",
                        result=DocumentPersistenceStatus.CONFLICT,
                        entity_type="document",
                        entity_id=existing.id,
                        correlation_id=identity_key,
                        reason_code="content_hash_mismatch",
                        data=data,
                        digest=artifact.digest,
                    )
                    return DocumentPersistenceResult(
                        DocumentPersistenceStatus.CONFLICT,
                        document_id=existing.id,
                        evidence_id=evidence.id,
                        reason_code="content_hash_mismatch",
                    )

                document = Document.objects.create(
                    company_id=company_id,
                    family=data.family,
                    role=data.role,
                    category=data.category,
                    source=data.source,
                    flow=data.flow,
                    identity_kind=selection.kind,
                    normalized_identity=selection.value,
                    identity_key=identity_key,
                    emitted_at=data.emitted_at,
                    authorized_at=data.authorized_at,
                    competence=derive_competence(data.emitted_at),
                    situation=data.situation,
                    origin_execution_ref=data.origin_execution_ref,
                    correlation_id=data.correlation_id,
                )
                evidence = DocumentEvidence.objects.create(
                    document=document,
                    artifact=artifact,
                    digest=artifact.digest,
                    size_bytes=size_bytes,
                )
                _audit(
                    action="document.persisted",
                    result=DocumentPersistenceStatus.PERSISTED,
                    entity_type="document",
                    entity_id=document.id,
                    correlation_id=identity_key,
                    reason_code=None,
                    data=data,
                    digest=artifact.digest,
                )
                return DocumentPersistenceResult(
                    DocumentPersistenceStatus.PERSISTED,
                    document_id=document.id,
                    evidence_id=evidence.id,
                )
        except IntegrityError:
            if attempt == 1:
                raise InvalidDocumentInput("Document identity could not be persisted safely")
    raise AssertionError("unreachable")


def _persist_event(
    data: DocumentInput, company_id: UUID, artifact: Artifact, selection: IdentitySelection
) -> DocumentPersistenceResult:
    assert data.parent_document_id is not None
    assert data.relationship_type is not None
    parent_id = UUID(str(data.parent_document_id))
    size_bytes = _artifact_size(artifact)
    identity_key = "|".join(
        (
            "event",
            str(parent_id),
            data.family,
            data.role,
            data.category,
            data.source,
            data.flow,
            selection.kind,
            selection.value,
        )
    )
    if len(identity_key) > 1024:
        raise InvalidDocumentInput("Fiscal event identity context is too long")
    for attempt in range(2):
        try:
            with transaction.atomic():
                try:
                    parent = Document.objects.select_for_update().get(pk=parent_id)
                except Document.DoesNotExist:
                    _audit(
                        action="document.quarantine",
                        result=DocumentPersistenceStatus.QUARANTINE,
                        entity_type="event",
                        entity_id=None,
                        correlation_id="",
                        reason_code="parent_missing",
                        data=data,
                        digest=artifact.digest,
                    )
                    return DocumentPersistenceResult(
                        DocumentPersistenceStatus.QUARANTINE, reason_code="parent_missing"
                    )
                if parent.company_id != company_id or parent.family != data.family:
                    _audit(
                        action="document.quarantine",
                        result=DocumentPersistenceStatus.QUARANTINE,
                        entity_type="event",
                        entity_id=None,
                        correlation_id="",
                        reason_code="parent_incompatible",
                        data=data,
                        digest=artifact.digest,
                    )
                    return DocumentPersistenceResult(
                        DocumentPersistenceStatus.QUARANTINE, reason_code="parent_incompatible"
                    )
                existing = (
                    DocumentEvent.objects.select_for_update()
                    .filter(identity_key=identity_key)
                    .first()
                )
                if existing:
                    evidence = (
                        DocumentEventEvidence.objects.filter(event=existing, digest=artifact.digest)
                        .order_by("created_at")
                        .first()
                    )
                    if evidence:
                        _audit(
                            action="document.event.replay",
                            result=DocumentPersistenceStatus.REPLAY,
                            entity_type="document_event",
                            entity_id=existing.id,
                            correlation_id=identity_key,
                            reason_code=None,
                            data=data,
                            digest=artifact.digest,
                        )
                        return DocumentPersistenceResult(
                            DocumentPersistenceStatus.REPLAY,
                            document_id=parent.id,
                            event_id=existing.id,
                            evidence_id=evidence.id,
                        )
                    evidence = DocumentEventEvidence.objects.create(
                        event=existing,
                        artifact=artifact,
                        digest=artifact.digest,
                        size_bytes=size_bytes,
                        conflicting=True,
                    )
                    DocumentEvent.objects.filter(pk=existing.id).update(
                        state=DocumentState.CONFLICT
                    )
                    _audit(
                        action="document.event.conflict",
                        result=DocumentPersistenceStatus.CONFLICT,
                        entity_type="document_event",
                        entity_id=existing.id,
                        correlation_id=identity_key,
                        reason_code="content_hash_mismatch",
                        data=data,
                        digest=artifact.digest,
                    )
                    return DocumentPersistenceResult(
                        DocumentPersistenceStatus.CONFLICT,
                        document_id=parent.id,
                        event_id=existing.id,
                        evidence_id=evidence.id,
                        reason_code="content_hash_mismatch",
                    )

                event = DocumentEvent.objects.create(
                    parent_document=parent,
                    family=data.family,
                    category=data.category,
                    source=data.source,
                    flow=data.flow,
                    identity_kind=selection.kind,
                    normalized_identity=selection.value,
                    identity_key=identity_key,
                    occurred_at=data.emitted_at,
                    situation=data.situation,
                    relationship_type=data.relationship_type,
                    origin_execution_ref=data.origin_execution_ref,
                    correlation_id=data.correlation_id,
                )
                evidence = DocumentEventEvidence.objects.create(
                    event=event,
                    artifact=artifact,
                    digest=artifact.digest,
                    size_bytes=size_bytes,
                )
                _audit(
                    action="document.event.persisted",
                    result=DocumentPersistenceStatus.PERSISTED,
                    entity_type="document_event",
                    entity_id=event.id,
                    correlation_id=identity_key,
                    reason_code=None,
                    data=data,
                    digest=artifact.digest,
                )
                return DocumentPersistenceResult(
                    DocumentPersistenceStatus.PERSISTED,
                    document_id=parent.id,
                    event_id=event.id,
                    evidence_id=evidence.id,
                )
        except IntegrityError:
            if attempt == 1:
                raise InvalidDocumentInput("Document event could not be persisted safely")
    raise AssertionError("unreachable")
