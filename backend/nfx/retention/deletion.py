"""Administrator-controlled, checkpointed fiscal document deletion."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from nfx.artifacts.models import Artifact
from nfx.artifacts.storage import (
    ArtifactDeletionDivergent,
    ArtifactDeletionFailed,
    ArtifactDeletionMissing,
    ArtifactStorageService,
    ObjectStore,
    object_store_from_environment,
)
from nfx.audit.services import AuditService, AuditUnavailable
from nfx.collection.models import ReceivedUnit
from nfx.documents.models import (
    Document,
    DocumentEvent,
    DocumentEventEvidence,
    DocumentEvidence,
    DocumentRender,
    NFeManifestation,
)
from nfx.exports.models import ExportItem, ExportItemState
from nfx.identity.models import Role
from nfx.identity.services import SessionIdentity
from nfx.jobs.handlers import HandlerOutcome, register_handler
from nfx.jobs.models import Job, JobPolicy, JobState
from nfx.jobs.services import JobEngine
from nfx.retention.metrics import retention_metrics
from nfx.retention.models import (
    DeletionItem,
    DeletionItemKind,
    DeletionItemState,
    DeletionOperation,
    DeletionOperationState,
)
from nfx.retention.services import decision_for_document, scope_hash

SCOPE_VERSION = "scope-v1"
DELETION_JOB_TYPE = "retention.delete"
_HASH = re.compile(r"^[a-f0-9]{64}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_ACTIVE_OPERATION_STATES = (
    DeletionOperationState.PENDING,
    DeletionOperationState.EXECUTING,
    DeletionOperationState.RECOVERY_REQUIRED,
)


class DeletionError(ValueError):
    code = "deletion_error"


class DeletionAccessDenied(DeletionError):
    code = "access_denied"


class DeletionNotFound(DeletionError):
    code = "not_found"


class DeletionInvalid(DeletionError):
    code = "invalid_request"


class DeletionStaleScope(DeletionError):
    code = "scope_changed"


class DeletionConflict(DeletionError):
    code = "operation_active"


class DeletionNotEligible(DeletionError):
    def __init__(self, code: str) -> None:
        self.code = code if _SAFE_CODE.fullmatch(code) else "not_eligible"
        super().__init__(self.code)


class DeletionAuditFailure(DeletionError):
    code = "audit_unavailable"


@dataclass(frozen=True)
class DeletionRequestResult:
    operation: DeletionOperation
    duplicate: bool = False


def confirmation_for(document_id: UUID | str, scope_hash_value: str) -> str:
    """Return the exact phrase bound to one document and one immutable preview."""
    return f"EXCLUIR:{document_id}:{scope_hash_value}"


def _now(value: datetime | None = None) -> datetime:
    current = value or timezone.now()
    if timezone.is_naive(current):
        raise ValueError("now must be timezone-aware")
    return current


def _scope_hash(value: object) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise DeletionInvalid("scope_hash is invalid")
    return value


def _reason(value: object) -> str:
    if not isinstance(value, str):
        raise DeletionInvalid("reason is invalid")
    normalized = value.strip()
    if not 1 <= len(normalized) <= 1000:
        raise DeletionInvalid("reason is invalid")
    return normalized


def _actor_uuid(actor: SessionIdentity) -> UUID:
    try:
        return UUID(actor.user_id)
    except ValueError as exc:
        raise DeletionAccessDenied("session is invalid") from exc


def _load_document(document_id: UUID | str) -> Document:
    try:
        document_uuid = UUID(str(document_id))
    except ValueError as exc:
        raise DeletionNotFound("document is unavailable") from exc
    document = (
        Document.objects.select_related("company")
        .prefetch_related(
            "evidence__artifact",
            "events__evidence__artifact",
            "renders__artifact",
            "renders__source_artifact",
        )
        .filter(pk=document_uuid)
        .first()
    )
    if document is None:
        raise DeletionNotFound("document is unavailable")
    return document


def _audit(
    *,
    operation: DeletionOperation,
    result: str,
    action: str = "document.delete",
    code: str = "",
) -> None:
    try:
        AuditService().append(
            action=action,
            entity_type="document",
            entity_id=str(operation.target_document_id),
            result=result,
            actor_id=operation.actor_id,
            actor_role=operation.actor.role if operation.actor_id and operation.actor else "",
            reason=operation.reason,
            correlation_id=operation.correlation_id,
            context={
                "operation_id": str(operation.id),
                "scope_version": operation.scope_version,
                "scope_hash_prefix": operation.scope_hash[:16],
                "step": operation.current_step,
                "code": code,
            },
        )
    except AuditUnavailable as exc:
        raise DeletionAuditFailure("audit is unavailable") from exc


def _operation_payload(
    operation: DeletionOperation, *, include_items: bool = True
) -> dict[str, object]:
    items = list(operation.items.order_by("created_at", "id")) if include_items else []
    payload: dict[str, object] = {
        "id": str(operation.id),
        "target_document_id": str(operation.target_document_id),
        "state": operation.state,
        "scope": {"hash": operation.scope_hash, "version": operation.scope_version},
        "reason": operation.reason,
        "actor_id": str(operation.actor_id) if operation.actor_id else None,
        "current_step": operation.current_step or None,
        "safe_error": operation.safe_error or None,
        "result_code": operation.result_code or None,
        "requested_at": operation.requested_at.isoformat(),
        "started_at": operation.started_at.isoformat() if operation.started_at else None,
        "completed_at": operation.completed_at.isoformat() if operation.completed_at else None,
        "checkpoint": operation.checkpoint,
    }
    if include_items:
        payload["items"] = [
            {
                "id": str(item.id),
                "kind": item.kind,
                "target_id": str(item.target_id),
                "artifact_id": str(item.artifact_id) if item.artifact_id else None,
                "digest_prefix": item.digest_prefix or None,
                "size_bytes": item.expected_size_bytes,
                "version": item.expected_version,
                "state": item.state,
                "attempts": item.attempts,
                "safe_error": item.safe_error or None,
            }
            for item in items
        ]
    return payload


def operation_payload(operation: DeletionOperation) -> dict[str, object]:
    return _operation_payload(operation)


def _append_item(
    operation: DeletionOperation,
    *,
    kind: str,
    target_id: UUID,
    artifact: Artifact | None = None,
) -> DeletionItem:
    return DeletionItem.objects.create(
        operation=operation,
        kind=kind,
        target_id=target_id,
        artifact_id=artifact.id if artifact else None,
        digest_prefix=artifact.digest[:16] if artifact and artifact.digest else "",
        expected_size_bytes=artifact.size_bytes if artifact else None,
        expected_version=artifact.version if artifact else None,
    )


def _enumerate_items(operation: DeletionOperation, document: Document) -> int:
    artifact_by_id: dict[UUID, Artifact] = {}
    count = 0
    _append_item(operation, kind=DeletionItemKind.DOCUMENT, target_id=document.id)
    count += 1
    for evidence in document.evidence.all():
        _append_item(
            operation,
            kind=DeletionItemKind.EVIDENCE,
            target_id=evidence.id,
            artifact=evidence.artifact,
        )
        artifact_by_id[evidence.artifact_id] = evidence.artifact
        count += 1
    for event in document.events.all():
        _append_item(operation, kind=DeletionItemKind.EVENT, target_id=event.id)
        count += 1
        for event_evidence in event.evidence.all():
            _append_item(
                operation,
                kind=DeletionItemKind.EVENT_EVIDENCE,
                target_id=event_evidence.id,
                artifact=event_evidence.artifact,
            )
            artifact_by_id[event_evidence.artifact_id] = event_evidence.artifact
            count += 1
    for render in document.renders.all():
        _append_item(operation, kind=DeletionItemKind.RENDER, target_id=render.id)
        count += 1
        artifact_by_id[render.source_artifact_id] = render.source_artifact
        if render.artifact_id and render.artifact is not None:
            artifact_by_id[render.artifact_id] = render.artifact
    for artifact_id in sorted(artifact_by_id, key=str):
        _append_item(
            operation,
            kind=DeletionItemKind.ARTIFACT,
            target_id=artifact_id,
            artifact=artifact_by_id[artifact_id],
        )
        count += 1
    return count


def _deletion_policy(at: datetime) -> JobPolicy:
    policy, _ = JobPolicy.objects.get_or_create(
        source_scope="retention",
        flow_scope="deletion",
        version=1,
        defaults={
            "valid_from": datetime(2020, 1, 1, tzinfo=UTC),
            "retry_limit": 3,
            "backoff_initial_seconds": 1,
            "backoff_cap_seconds": 60,
            "jitter_seconds": 0,
        },
    )
    if not policy.valid_from <= at:
        raise DeletionError("deletion policy is unavailable")
    return policy


def _enqueue(operation: DeletionOperation, *, resume: bool = False) -> Job:
    current = timezone.now()
    active_job = (
        Job.objects.filter(
            id=operation.job_id,
            state__in=(JobState.QUEUED, JobState.RUNNING),
        ).first()
        if operation.job_id
        else None
    )
    if active_job is not None:
        return active_job
    key = f"deletion:{operation.id}"
    if resume:
        key = f"{key}:resume:{uuid4().hex}"
    job = JobEngine().enqueue(
        job_type=DELETION_JOB_TYPE,
        logical_target=f"document:{operation.target_document_id}",
        payload={"operation_id": str(operation.id)},
        idempotency_key=key,
        policy=_deletion_policy(current),
    )
    operation.job = job
    operation.save(update_fields=["job", "updated_at"])
    return job


def request_deletion(
    *,
    actor: SessionIdentity,
    document_id: UUID | str,
    scope_hash_value: object,
    scope_version: object,
    confirmation: object,
    reason: object,
) -> DeletionRequestResult:
    if actor.role != Role.ADMINISTRATOR:
        raise DeletionAccessDenied("administrator access required")
    document_uuid = UUID(str(document_id))
    requested_hash = _scope_hash(scope_hash_value)
    if scope_version != SCOPE_VERSION:
        raise DeletionInvalid("scope_version is invalid")
    normalized_reason = _reason(reason)
    if not isinstance(confirmation, str):
        raise DeletionInvalid("confirmation is invalid")
    actor_uuid = _actor_uuid(actor)
    correlation_id = hashlib.sha256(
        f"deletion:{document_uuid}:{requested_hash}".encode()
    ).hexdigest()[:32]

    for attempt in range(2):
        try:
            with transaction.atomic():
                locked_document = (
                    Document.objects.select_for_update().filter(pk=document_uuid).first()
                )
                if locked_document is None:
                    raise DeletionNotFound("document is unavailable")
                current_document = _load_document(document_uuid)
                current_hash = scope_hash(current_document)
                if current_hash != requested_hash:
                    raise DeletionStaleScope("preview scope changed")
                if confirmation != confirmation_for(document_uuid, current_hash):
                    raise DeletionInvalid("confirmation is invalid")
                existing = (
                    DeletionOperation.objects.select_for_update()
                    .filter(
                        target_document_id=document_uuid,
                        state__in=_ACTIVE_OPERATION_STATES,
                    )
                    .first()
                )
                if existing is not None:
                    if existing.scope_hash != requested_hash:
                        raise DeletionConflict("another deletion is active")
                    return DeletionRequestResult(existing, duplicate=True)
                decision = decision_for_document(current_document)
                if decision.state.value != "eligible":
                    raise DeletionNotEligible(decision.reason_code)
                operation = DeletionOperation.objects.create(
                    target_document_id=document_uuid,
                    actor_id=actor_uuid,
                    scope_hash=current_hash,
                    scope_version=SCOPE_VERSION,
                    reason=normalized_reason,
                    correlation_id=correlation_id,
                    state=DeletionOperationState.PENDING,
                    current_step="requested",
                    checkpoint={"scope_version": SCOPE_VERSION},
                )
                count = _enumerate_items(operation, current_document)
                operation.checkpoint = {
                    "total_items": count,
                    "artifact_items": operation.items.filter(
                        kind=DeletionItemKind.ARTIFACT
                    ).count(),
                }
                operation.save(update_fields=["checkpoint", "updated_at"])
                _audit(operation=operation, result="requested")
                _enqueue(operation)
                retention_metrics.record_deletion("requested")
                return DeletionRequestResult(operation)
        except IntegrityError:
            if attempt == 0:
                continue
            raise DeletionConflict("another deletion is active")
    raise DeletionConflict("another deletion is active")


def resume_deletion(*, actor: SessionIdentity, operation_id: UUID | str) -> DeletionOperation:
    if actor.role != Role.ADMINISTRATOR:
        raise DeletionAccessDenied("administrator access required")
    try:
        operation_uuid = UUID(str(operation_id))
    except ValueError as exc:
        raise DeletionNotFound("operation is unavailable") from exc
    with transaction.atomic():
        operation = DeletionOperation.objects.select_for_update().filter(pk=operation_uuid).first()
        if operation is None:
            raise DeletionNotFound("operation is unavailable")
        if operation.state == DeletionOperationState.COMPLETED:
            return operation
        operation.state = DeletionOperationState.PENDING
        operation.safe_error = ""
        operation.current_step = "resume_requested"
        operation.save(update_fields=["state", "safe_error", "current_step", "updated_at"])
        _audit(operation=operation, result="recovery_requested")
        _enqueue(operation, resume=True)
    return DeletionOperation.objects.get(pk=operation_uuid)


def _mark_outcome(
    operation_id: UUID,
    *,
    state: str,
    code: str,
    item_id: UUID | None = None,
) -> DeletionOperation:
    current = timezone.now()
    with transaction.atomic():
        if item_id is not None:
            DeletionItem.objects.filter(pk=item_id).update(
                state=(
                    DeletionItemState.RECOVERY_REQUIRED
                    if state == DeletionOperationState.RECOVERY_REQUIRED
                    else DeletionItemState.FAILED
                ),
                safe_error=code,
                updated_at=current,
            )
        operation = DeletionOperation.objects.select_for_update().get(pk=operation_id)
        operation.state = state
        operation.current_step = (
            "recovery" if state == DeletionOperationState.RECOVERY_REQUIRED else "failed"
        )
        operation.safe_error = code
        operation.result_code = (
            "recovery_required"
            if state == DeletionOperationState.RECOVERY_REQUIRED
            else "failed"
        )
        operation.save(
            update_fields=["state", "current_step", "safe_error", "result_code", "updated_at"]
        )
    try:
        _audit(
            operation=operation,
            result=state,
            code=code,
        )
    except DeletionAuditFailure:
        pass
    retention_metrics.record_deletion(
        "recovery_required" if state == DeletionOperationState.RECOVERY_REQUIRED else "failed"
    )
    return operation


def _claim_item(item_id: UUID) -> DeletionItem | None:
    with transaction.atomic():
        item = DeletionItem.objects.select_for_update().filter(pk=item_id).first()
        if item is None or item.state == DeletionItemState.COMPLETED:
            return None
        item.state = DeletionItemState.RUNNING
        item.attempts = F("attempts") + 1
        item.save(update_fields=["state", "attempts", "updated_at"])
    return DeletionItem.objects.get(pk=item_id)


def _process_artifact(
    operation: DeletionOperation,
    item: DeletionItem,
    storage: ArtifactStorageService,
) -> DeletionOperation | None:
    claimed = _claim_item(item.id)
    if claimed is None:
        return None
    if (
        claimed.artifact_id is None
        or claimed.expected_size_bytes is None
        or claimed.expected_version is None
    ):
        return _mark_outcome(
            operation.id,
            state=DeletionOperationState.RECOVERY_REQUIRED,
            code="artifact_metadata_missing",
            item_id=claimed.id,
        )
    try:
        storage.delete_for_deletion(
            claimed.artifact_id,
            expected_digest_prefix=claimed.digest_prefix,
            expected_size_bytes=claimed.expected_size_bytes,
            expected_version=claimed.expected_version,
        )
    except ArtifactDeletionMissing:
        return _mark_outcome(
            operation.id,
            state=DeletionOperationState.RECOVERY_REQUIRED,
            code="artifact_missing",
            item_id=claimed.id,
        )
    except ArtifactDeletionDivergent:
        return _mark_outcome(
            operation.id,
            state=DeletionOperationState.RECOVERY_REQUIRED,
            code="artifact_divergent",
            item_id=claimed.id,
        )
    except ArtifactDeletionFailed:
        return _mark_outcome(
            operation.id,
            state=DeletionOperationState.RECOVERY_REQUIRED,
            code="storage_delete_failed",
            item_id=claimed.id,
        )
    with transaction.atomic():
        DeletionItem.objects.filter(pk=claimed.id).update(
            state=DeletionItemState.COMPLETED,
            safe_error="",
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )
    return None


def _finalize_relational(operation_id: UUID) -> DeletionOperation:
    with transaction.atomic():
        operation = (
            DeletionOperation.objects.select_for_update()
            .get(pk=operation_id)
        )
        items = list(operation.items.all())
        if any(
            item.kind == DeletionItemKind.ARTIFACT
            and item.state != DeletionItemState.COMPLETED
            for item in items
        ):
            raise DeletionError("deletion checkpoints are incomplete")
        event_ids = [
            item.target_id for item in items if item.kind == DeletionItemKind.EVENT
        ]
        artifact_ids = {
            item.artifact_id
            for item in items
            if item.kind == DeletionItemKind.ARTIFACT and item.artifact_id
        }
        ReceivedUnit.objects.filter(document_id=operation.target_document_id).update(document=None)
        if event_ids:
            ReceivedUnit.objects.filter(event_id__in=event_ids).update(event=None)
        if artifact_ids:
            ReceivedUnit.objects.filter(artifact_id__in=artifact_ids).update(artifact=None)
        NFeManifestation.objects.filter(document_id=operation.target_document_id).update(document=None)
        ExportItem.objects.filter(document_id=operation.target_document_id).update(
            document=None,
            artifact=None,
            state=ExportItemState.EXCLUDED,
            safe_error="document_deleted",
            updated_at=timezone.now(),
        )
        DocumentEventEvidence.objects.filter(event__parent_document_id=operation.target_document_id).delete()
        DocumentEvidence.objects.filter(document_id=operation.target_document_id).delete()
        DocumentRender.objects.filter(document_id=operation.target_document_id).delete()
        DocumentEvent.objects.filter(parent_document_id=operation.target_document_id).delete()
        deleted, _ = Document.objects.filter(pk=operation.target_document_id).delete()
        if deleted == 0:
            raise DeletionError("document is unavailable")
        for artifact_id in artifact_ids:
            Artifact.objects.filter(pk=artifact_id).delete()
        now = timezone.now()
        DeletionItem.objects.filter(operation_id=operation_id).update(
            state=DeletionItemState.COMPLETED,
            safe_error="",
            completed_at=now,
            updated_at=now,
        )
        operation.state = DeletionOperationState.COMPLETED
        operation.current_step = "completed"
        operation.safe_error = ""
        operation.result_code = "completed"
        operation.completed_at = now
        operation.checkpoint = {
            "total_items": len(items),
            "completed_items": len(items),
            "artifact_items": len(artifact_ids),
        }
        operation.save(
            update_fields=[
                "state",
                "current_step",
                "safe_error",
                "result_code",
                "completed_at",
                "checkpoint",
                "updated_at",
            ]
        )
        _audit(operation=operation, result="completed", code="completed")
        retention_metrics.record_deletion("completed")
        return operation


def execute_deletion(
    operation_id: UUID | str,
    *,
    storage: ArtifactStorageService | None = None,
) -> DeletionOperation:
    try:
        operation_uuid = UUID(str(operation_id))
    except ValueError as exc:
        raise DeletionNotFound("operation is unavailable") from exc
    with transaction.atomic():
        operation = DeletionOperation.objects.select_for_update().filter(pk=operation_uuid).first()
        if operation is None:
            raise DeletionNotFound("operation is unavailable")
        if operation.state == DeletionOperationState.COMPLETED:
            return operation
        operation.state = DeletionOperationState.EXECUTING
        operation.started_at = operation.started_at or timezone.now()
        operation.current_step = "revalidate"
        operation.save(update_fields=["state", "started_at", "current_step", "updated_at"])
    try:
        document = _load_document(operation.target_document_id)
        if scope_hash(document) != operation.scope_hash:
            return _mark_outcome(
                operation_uuid, state=DeletionOperationState.FAILED, code="scope_changed"
            )
        decision = decision_for_document(document)
        if decision.state.value != "eligible":
            return _mark_outcome(
                operation_uuid,
                state=DeletionOperationState.FAILED,
                code=decision.reason_code,
            )
        object_storage = storage or ArtifactStorageService(
            cast(ObjectStore, object_store_from_environment())
        )
        items = list(
            DeletionItem.objects.filter(operation_id=operation_uuid).order_by("created_at", "id")
        )
        for item in items:
            if item.kind != DeletionItemKind.ARTIFACT:
                continue
            with transaction.atomic():
                DeletionOperation.objects.filter(pk=operation_uuid).update(
                    current_step="artifact", updated_at=timezone.now()
                )
            outcome = _process_artifact(
                DeletionOperation.objects.get(pk=operation_uuid), item, object_storage
            )
            if outcome is not None:
                return outcome
        return _finalize_relational(operation_uuid)
    except DeletionAuditFailure:
        return _mark_outcome(
            operation_uuid,
            state=DeletionOperationState.RECOVERY_REQUIRED,
            code="audit_unavailable",
        )
    except ProtectedError:
        retention_metrics.record_deletion("orphan")
        return _mark_outcome(
            operation_uuid,
            state=DeletionOperationState.RECOVERY_REQUIRED,
            code="relational_cleanup_blocked",
        )
    except DeletionError:
        return _mark_outcome(
            operation_uuid,
            state=DeletionOperationState.RECOVERY_REQUIRED,
            code="relational_cleanup_blocked",
        )
    except Exception:
        return _mark_outcome(
            operation_uuid,
            state=DeletionOperationState.FAILED,
            code="deletion_failed",
        )


def deletion_handler(job: Job) -> HandlerOutcome:
    operation_id = job.payload.get("operation_id")
    if not isinstance(operation_id, str):
        return HandlerOutcome.permanent(error_code="invalid_operation")
    try:
        operation = execute_deletion(operation_id)
    except DeletionNotFound:
        return HandlerOutcome.permanent(error_code="operation_missing")
    if operation.state == DeletionOperationState.COMPLETED:
        return HandlerOutcome.success(
            {
                "operation_id": str(operation.id),
                "state": operation.state,
                "result_code": operation.result_code,
            }
        )
    if operation.state == DeletionOperationState.RECOVERY_REQUIRED:
        return HandlerOutcome.partial(
            error_code=operation.safe_error or "recovery_required",
            result={"operation_id": str(operation.id), "state": operation.state},
        )
    return HandlerOutcome.permanent(
        error_code=operation.safe_error or "deletion_failed",
        result={"operation_id": str(operation.id), "state": operation.state},
    )


def ensure_deletion_handler() -> None:
    register_handler(DELETION_JOB_TYPE, deletion_handler)
