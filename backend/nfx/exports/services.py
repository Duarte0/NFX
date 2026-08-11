"""Frozen selection, resumable composition, access control, and cleanup for ZIP exports."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from nfx.artifacts.models import ArtifactState
from nfx.artifacts.storage import ArtifactNotReadable, ArtifactStorageService, ObjectStore
from nfx.audit.services import AuditService
from nfx.documents.consultation import (
    InvalidConsultationParams,
    parse_consultation_params,
    safe_filename,
)
from nfx.documents.models import Document, DocumentEvidence
from nfx.documents.status import DocumentListParams, scoped_documents
from nfx.exports.metrics import export_metrics
from nfx.exports.models import Export, ExportItem, ExportItemState, ExportState
from nfx.identity.policy import Action, authorize
from nfx.identity.services import SessionIdentity
from nfx.jobs.handlers import HandlerOutcome, register_handler
from nfx.jobs.models import Job
from nfx.jobs.services import JobEngine

EXPORT_JOB_TYPE = "export.zip"
EXPORT_TTL = timedelta(hours=24)
MAX_EXPORT_ITEMS = 100
MAX_ENTRY_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class ExportError(ValueError):
    code = "export_error"


class ExportAccessDenied(ExportError):
    code = "access_denied"


class ExportTemporaryFailure(RuntimeError):
    code = "temporary_failure"


@dataclass(frozen=True)
class ExportRequestResult:
    export: Export
    duplicate: bool = False


def _now(value: datetime | None) -> datetime:
    current = value or timezone.now()
    if timezone.is_naive(current):
        raise ValueError("now must be timezone-aware")
    return current


def _idempotency(value: object) -> str:
    if not isinstance(value, str):
        raise ExportError("idempotency_key is invalid")
    normalized = value.strip()
    if not 1 <= len(normalized) <= 128 or not _SAFE_KEY.fullmatch(normalized):
        raise ExportError("idempotency_key is invalid")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _params(filters: Mapping[str, object]) -> DocumentListParams:
    try:
        parsed = parse_consultation_params(filters)
    except InvalidConsultationParams as exc:
        raise ExportError("filters are invalid") from exc
    if parsed.limit > MAX_EXPORT_ITEMS:
        raise ExportError("export exceeds its configured item limit")
    return DocumentListParams(
        company_id=parsed.company_ids[0] if len(parsed.company_ids) == 1 else None,
        company_ids=parsed.company_ids,
        family=parsed.family,
        flow=parsed.flow,
        competence_from=parsed.competence_from,
        competence_to=parsed.competence_to,
        emitted_from=parsed.emitted_from,
        emitted_to=parsed.emitted_to,
        direction=parsed.direction,
        nfse_category=parsed.nfse_category,
        event_type=parsed.event_type,
        search=parsed.search,
        limit=parsed.limit,
        cursor=UUID(parsed.cursor) if parsed.cursor else None,
    )


def _filter_snapshot(params: DocumentListParams) -> dict[str, object]:
    return {
        "company_ids": sorted(str(value) for value in params.company_ids),
        "competence_from": params.competence_from.isoformat() if params.competence_from else None,
        "competence_to": params.competence_to.isoformat() if params.competence_to else None,
        "emitted_from": params.emitted_from.isoformat() if params.emitted_from else None,
        "emitted_to": params.emitted_to.isoformat() if params.emitted_to else None,
        "family": params.family,
        "flow": params.flow,
        "direction": params.direction,
        "nfse_category": params.nfse_category,
        "event_type": params.event_type,
        "search": params.search,
        "limit": params.limit,
        "cursor": str(params.cursor) if params.cursor else None,
    }


def _selection(params: DocumentListParams) -> list[tuple[Document, DocumentEvidence | None]]:
    rows = list(scoped_documents(params)[: params.limit])
    selected: list[tuple[Document, DocumentEvidence | None]] = []
    for document in rows:
        evidence = next(iter(document.evidence.all()), None)
        selected.append((document, evidence))
    return selected


def _audit(
    actor: SessionIdentity,
    *,
    action: str,
    export: Export,
    result: str,
    count: int = 0,
) -> None:
    AuditService().append(
        action=action,
        entity_type="export",
        entity_id=str(export.id),
        result=result,
        actor_id=actor.user_id,
        actor_role=actor.role,
        context={"count": min(max(count, 0), MAX_EXPORT_ITEMS), "state": export.state},
    )


def request_export(
    *,
    actor: SessionIdentity,
    filters: Mapping[str, object],
    idempotency_key: object,
    now: datetime | None = None,
) -> ExportRequestResult:
    if not authorize(actor.role, Action.CREATE_ZIP, actor_id=actor.user_id):
        raise ExportAccessDenied("export creation access required")
    current = _now(now)
    key = _idempotency(idempotency_key)
    params = _params(filters)
    selected = _selection(params)
    expected_bytes = sum(
        int(evidence.size_bytes) for _, evidence in selected if evidence is not None
    )
    if expected_bytes > MAX_ARCHIVE_BYTES:
        raise ExportError("export exceeds its configured size limit")
    for _ in range(2):
        try:
            with transaction.atomic():
                existing = (
                    Export.objects.select_for_update()
                    .filter(requester_id=UUID(actor.user_id), idempotency_key=key)
                    .first()
                )
                if existing is not None:
                    export_metrics.record("request")
                    return ExportRequestResult(existing, duplicate=True)
                export = Export.objects.create(
                    requester_id=UUID(actor.user_id),
                    filter_snapshot=_filter_snapshot(params),
                    selection_snapshot={
                        "document_ids": [str(document.id) for document, _ in selected]
                    },
                    expected_count=len(selected),
                    expected_bytes=expected_bytes,
                    idempotency_key=key,
                    expires_at=current + EXPORT_TTL,
                )
                for sequence, (document, evidence) in enumerate(selected):
                    ExportItem.objects.create(
                        export=export,
                        document=document,
                        artifact=evidence.artifact if evidence else None,
                        digest=evidence.digest if evidence else "",
                        size_bytes=evidence.size_bytes if evidence else 0,
                        content_type=(
                            evidence.artifact.detected_mime_type
                            or evidence.artifact.declared_mime_type
                            if evidence
                            else ""
                        ),
                        sequence=sequence,
                    )
                job = JobEngine().enqueue(
                    job_type=EXPORT_JOB_TYPE,
                    logical_target=f"export:{export.id}",
                    payload={"export_id": str(export.id)},
                    idempotency_key=f"export:{actor.user_id}:{key}",
                )
                export.job = job
                export.save(update_fields=["job", "updated_at"])
        except IntegrityError:
            continue
        _audit(
            actor,
            action="export.request",
            export=export,
            result="success",
            count=len(selected),
        )
        export_metrics.record("request")
        return ExportRequestResult(export)
    raise ExportError("could not resolve export idempotency")


def _safe_segment(value: str, fallback: str) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9_-]+", "-", value.encode("ascii", "ignore").decode()
    ).strip(".-")
    return (normalized[:48] or fallback).lower()


def archive_path(item: ExportItem) -> str:
    document = item.document
    if document is None:
        raise ExportError("document is unavailable")
    content_type = item.content_type or "application/octet-stream"
    filename = safe_filename(document.normalized_identity, content_type)
    company = _safe_segment(document.company.legal_name, f"company-{document.company_id.hex[:8]}")
    competence = document.competence.isoformat()
    role = _safe_segment(document.role, "documents")
    stem, extension = filename.rsplit(".", 1)
    return (
        f"{company}/{competence}/{document.family}/{role}/"
        f"{stem}-{document.id.hex[:12]}.{extension}"
    )


def _item_failure(item: ExportItem, state: str, reason: str) -> None:
    item.state = state
    item.safe_error = reason
    item.archive_path = ""
    item.save(update_fields=["state", "safe_error", "archive_path", "updated_at"])


def compose_export(
    export_id: UUID,
    *,
    storage: ArtifactStorageService | None = None,
    now: datetime | None = None,
) -> HandlerOutcome:
    current = _now(now)
    export = Export.objects.select_related("requester").get(pk=export_id)
    if export.state in {ExportState.AVAILABLE, ExportState.EXPIRED, ExportState.EXCLUDED}:
        return HandlerOutcome.success(
            {"state": export.state, "produced_count": export.produced_count}
        )
    if export.expires_at <= current:
        Export.objects.filter(pk=export.id).update(
            state=ExportState.EXPIRED, safe_error="expired", updated_at=current
        )
        return HandlerOutcome.success({"state": ExportState.EXPIRED})
    Export.objects.filter(pk=export.id).update(
        state=ExportState.PROCESSING, safe_error="", updated_at=current
    )
    items = list(
        ExportItem.objects.select_related("document__company", "artifact")
        .filter(export=export)
        .order_by("sequence", "id")
    )
    output = io.BytesIO()
    seen: set[str] = set()
    produced_count = 0
    produced_bytes = 0
    failures = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for item in items:
            if item.artifact_id is None:
                _item_failure(item, ExportItemState.MISSING, "source_missing")
                failures += 1
                continue
            artifact = item.artifact
            if artifact is None or artifact.state != ArtifactState.FINALIZED:
                state = (
                    ExportItemState.DIVERGENT
                    if artifact and artifact.state == ArtifactState.DIVERGENT
                    else ExportItemState.MISSING
                )
                _item_failure(item, state, "source_unavailable")
                failures += 1
                continue
            if artifact.digest != item.digest or artifact.size_bytes != item.size_bytes:
                _item_failure(item, ExportItemState.DIVERGENT, "source_divergent")
                failures += 1
                continue
            try:
                stream = (storage or ArtifactStorageService(_default_store())).read_verified(
                    artifact.id
                )
                payload = stream.read()
                stream.close()
            except (ArtifactNotReadable, OSError, ValueError):
                _item_failure(item, ExportItemState.MISSING, "source_unavailable")
                failures += 1
                continue
            if len(payload) != item.size_bytes or len(payload) > MAX_ENTRY_BYTES:
                _item_failure(item, ExportItemState.DIVERGENT, "source_size_invalid")
                failures += 1
                continue
            path = archive_path(item)
            if path in seen:
                _item_failure(item, ExportItemState.FAILED, "path_collision")
                failures += 1
                continue
            seen.add(path)
            archive.writestr(path, payload)
            item.state = ExportItemState.INCLUDED
            item.archive_path = path
            item.safe_error = ""
            item.save(update_fields=["state", "archive_path", "safe_error", "updated_at"])
            produced_count += 1
            produced_bytes += len(payload)
            if output.tell() > MAX_ARCHIVE_BYTES:
                raise ExportTemporaryFailure("archive_size_limit")
    if failures:
        Export.objects.filter(pk=export.id).update(
            state=ExportState.PARTIAL if produced_count else ExportState.FAILED,
            produced_count=produced_count,
            produced_bytes=produced_bytes,
            safe_result={"failed_count": failures, "produced_count": produced_count},
            safe_error="partial_result" if produced_count else "all_items_failed",
            completed_at=current,
            updated_at=current,
        )
        export_metrics.record("compose", "partial" if produced_count else "failed")
        try:
            AuditService().append(
                action="export.job",
                entity_type="export",
                entity_id=str(export.id),
                result="partial" if produced_count else "failed",
                context={"failed_count": failures, "produced_count": produced_count},
            )
        except Exception:
            pass
        return HandlerOutcome.success(
            {
                "state": ExportState.PARTIAL if produced_count else ExportState.FAILED,
                "failed_count": failures,
            }
        )
    output.seek(0)
    try:
        store = storage or ArtifactStorageService(
            _default_store(), maximum_size=MAX_ARCHIVE_BYTES
        )
        artifact = store.begin(
            "export_zip_temp",
            f"export:{export.id}:{export.updated_at.timestamp()}",
            "application/zip",
        )
        artifact = store.transmit(artifact.id, [output.read()])
    except Exception as exc:
        raise ExportTemporaryFailure("temporary_output_unavailable") from exc
    Export.objects.filter(pk=export.id).update(
        state=ExportState.AVAILABLE,
        produced_count=produced_count,
        produced_bytes=produced_bytes,
        zip_artifact_id=artifact.id,
        safe_result={"failed_count": 0, "produced_count": produced_count},
        safe_error="",
        completed_at=current,
        updated_at=current,
    )
    export_metrics.record("compose", "available")
    try:
        AuditService().append(
            action="export.job",
            entity_type="export",
            entity_id=str(export.id),
            result="available",
            context={"produced_count": produced_count, "produced_bytes": produced_bytes},
        )
    except Exception:
        pass
    return HandlerOutcome.success(
        {"state": ExportState.AVAILABLE, "produced_count": produced_count}
    )


def _default_store() -> ObjectStore:
    from nfx.artifacts.storage import object_store_from_environment

    return object_store_from_environment()  # type: ignore[return-value]


def export_handler(job: Job) -> HandlerOutcome:
    export_id = job.payload.get("export_id")
    try:
        parsed = UUID(str(export_id))
    except (TypeError, ValueError):
        return HandlerOutcome.permanent(error_code="invalid_export_reference")
    try:
        return compose_export(parsed)
    except ExportTemporaryFailure as exc:
        return HandlerOutcome.temporary(error_code=exc.code)


def ensure_export_handler() -> None:
    register_handler(EXPORT_JOB_TYPE, export_handler)


def list_exports(*, actor: SessionIdentity) -> list[Export]:
    queryset = Export.objects.select_related("requester", "job", "zip_artifact")
    if not authorize(actor.role, Action.DOWNLOAD_ANY_ZIP, actor_id=actor.user_id):
        queryset = queryset.filter(requester_id=UUID(actor.user_id))
    return list(queryset.order_by("-created_at")[:100])


def get_export(*, actor: SessionIdentity, export_id: UUID) -> Export | None:
    export = (
        Export.objects.select_related("requester", "job", "zip_artifact")
        .filter(pk=export_id)
        .first()
    )
    if export is None:
        return None
    allowed = authorize(actor.role, Action.DOWNLOAD_ANY_ZIP, actor_id=actor.user_id) or (
        authorize(
            actor.role,
            Action.DOWNLOAD_OWN_ZIP,
            owner_id=str(export.requester_id),
            actor_id=actor.user_id,
        )
    )
    return export if allowed else None


def cleanup_expired(
    *, now: datetime | None = None, storage: ArtifactStorageService | None = None
) -> int:
    current = _now(now)
    expired = list(
        Export.objects.filter(expires_at__lte=current)
        .exclude(state=ExportState.EXCLUDED)
        .filter(~Q(state=ExportState.EXPIRED) | Q(zip_artifact__isnull=False))
        .select_related("zip_artifact")
    )
    cleaned = 0
    for export in expired:
        Export.objects.filter(pk=export.id).update(
            state=ExportState.EXPIRED, safe_error="expired", updated_at=current
        )
        export_metrics.record("compose", "expired")
        if export.zip_artifact_id and export.zip_artifact is not None:
            try:
                Export.objects.filter(pk=export.id).update(zip_artifact=None, updated_at=current)
                (storage or ArtifactStorageService(_default_store())).delete_temporary(
                    export.zip_artifact.id, logical_class="export_zip_temp"
                )
            except Exception:
                Export.objects.filter(pk=export.id).update(
                    zip_artifact_id=export.zip_artifact_id, updated_at=current
                )
                continue
        cleaned += 1
        export_metrics.record("cleanup")
    return cleaned
