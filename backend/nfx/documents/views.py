from __future__ import annotations

import hashlib
import time
from typing import cast
from uuid import UUID

from django.http import FileResponse, HttpRequest, HttpResponseBase, JsonResponse
from django.views.decorators.http import require_GET

from nfx.artifacts.storage import (
    ArtifactStorageService,
    object_store_from_environment,
)
from nfx.audit.services import AuditService, AuditUnavailable
from nfx.documents.consultation import (
    artifact_available,
    document_detail,
    downloadable_artifact,
    safe_filename,
)
from nfx.documents.metrics import document_metrics
from nfx.documents.status import (
    DocumentListParams,
    InvalidDocumentListParams,
    list_document_status,
)
from nfx.identity.policy import Action
from nfx.identity.services import resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME, protected


def _ip(request: HttpRequest) -> str:
    return str(request.META.get("REMOTE_ADDR", ""))


def _audit_read(
    request: HttpRequest,
    *,
    action: str,
    entity_id: str,
    result: str,
    context: dict[str, object],
) -> bool:
    started = time.perf_counter()
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return False
    try:
        AuditService().append(
            action=action,
            entity_type="document",
            entity_id=entity_id,
            result=result,
            actor_id=identity.user_id,
            actor_role=identity.role,
            ip_address=_ip(request),
            correlation_id=hashlib.sha256(f"{action}:{entity_id}".encode()).hexdigest()[:32],
            context=context,
        )
    except AuditUnavailable:
        document_metrics.record(
            action="download" if action == "document.download" else "consultation",
            result=result,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        return False
    document_metrics.record(
        action="download" if action == "document.download" else "consultation",
        result=result,
        latency_ms=(time.perf_counter() - started) * 1000,
    )
    return True


@require_GET
@protected(Action.READ_DOCUMENTS)
def documents(request: HttpRequest) -> JsonResponse:
    try:
        params = DocumentListParams.from_query(request.GET)
    except InvalidDocumentListParams:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    payload = list_document_status(params)
    if not _audit_read(
        request,
        action="document.consultation",
        entity_id="",
        result="success" if payload["documents"] else "empty",
        context={
            "count": len(cast(list[object], payload["documents"])),
            "scope": "bounded",
        },
    ):
        return JsonResponse({"detail": "Consulta temporariamente indisponível."}, status=503)
    return JsonResponse(payload)


@require_GET
@protected(Action.READ_DOCUMENTS)
def detail(request: HttpRequest, document_id: UUID) -> JsonResponse:
    payload = document_detail(document_id)
    result = "success" if payload is not None else "not_found"
    if not _audit_read(
        request,
        action="document.consultation",
        entity_id=str(document_id),
        result=result,
        context={"scope": "detail"},
    ):
        return JsonResponse({"detail": "Consulta temporariamente indisponível."}, status=503)
    if payload is None:
        return JsonResponse({"detail": "Documento não encontrado."}, status=404)
    return JsonResponse(payload)


def _download(
    request: HttpRequest, *, document_id: UUID | None, artifact_id: UUID | None
) -> HttpResponseBase:
    target = str(document_id or artifact_id or "")
    ownership = downloadable_artifact(document_id=document_id, artifact_id=artifact_id)
    if ownership is None:
        audited = _audit_read(
            request,
            action="document.download",
            entity_id=target,
            result="denied",
            context={"target": "document" if document_id else "artifact"},
        )
        return JsonResponse(
            {"detail": "Documento não disponível."}, status=404 if audited else 503
        )
    document, artifact = ownership
    if artifact.size_bytes is None or not artifact_available(
        artifact,
        digest=artifact.digest,
        size_bytes=artifact.size_bytes,
        conflicting=False,
    ):
        audited = _audit_read(
            request,
            action="document.download",
            entity_id=target,
            result="unavailable",
            context={"target": "document" if document_id else "artifact"},
        )
        return JsonResponse(
            {"detail": "Documento não disponível."}, status=404 if audited else 503
        )
    try:
        stream = ArtifactStorageService(
            object_store_from_environment()  # type: ignore[arg-type]
        ).read_verified(artifact.id)
    except Exception:
        audited = _audit_read(
            request,
            action="document.download",
            entity_id=target,
            result="unavailable",
            context={"target": "document" if document_id else "artifact"},
        )
        return JsonResponse(
            {"detail": "Documento não disponível."}, status=404 if audited else 503
        )
    if not _audit_read(
        request,
        action="document.download",
        entity_id=target,
        result="success",
        context={"target": "document" if document_id else "artifact", "size": artifact.size_bytes},
    ):
        stream.close()
        return JsonResponse({"detail": "Download temporariamente indisponível."}, status=503)
    content_type = artifact.detected_mime_type or artifact.declared_mime_type
    if content_type not in {"application/xml", "text/xml"}:
        content_type = "application/octet-stream"
    response = FileResponse(stream, content_type=content_type, as_attachment=True)
    response["Content-Length"] = str(artifact.size_bytes)
    filename = safe_filename(document.normalized_identity, content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response


@require_GET
@protected(Action.DOWNLOAD_DOCUMENTS)
def download_document(request: HttpRequest, document_id: UUID) -> HttpResponseBase:
    return _download(request, document_id=document_id, artifact_id=None)


@require_GET
@protected(Action.DOWNLOAD_DOCUMENTS)
def download_artifact(request: HttpRequest, artifact_id: UUID) -> HttpResponseBase:
    return _download(request, document_id=None, artifact_id=artifact_id)
