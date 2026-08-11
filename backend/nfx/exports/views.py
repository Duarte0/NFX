from __future__ import annotations

import json
from uuid import UUID

from django.http import FileResponse, HttpRequest, HttpResponseBase, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from nfx.artifacts.storage import ArtifactStorageService, object_store_from_environment
from nfx.audit.services import AuditService
from nfx.exports.metrics import export_metrics
from nfx.exports.models import Export
from nfx.exports.services import (
    ExportAccessDenied,
    ExportError,
    cleanup_expired,
    get_export,
    list_exports,
    request_export,
)
from nfx.identity.policy import Action, authorize
from nfx.identity.services import SessionIdentity, resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME


def _identity(request: HttpRequest) -> SessionIdentity | None:
    return resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME))


def _payload(export: Export, *, detail: bool = False) -> dict[str, object]:
    result: dict[str, object] = {
        "id": str(export.id),
        "state": export.state,
        "expected_count": export.expected_count,
        "produced_count": export.produced_count,
        "expected_bytes": export.expected_bytes,
        "produced_bytes": export.produced_bytes,
        "created_at": export.created_at.isoformat(),
        "expires_at": export.expires_at.isoformat(),
        "safe_error": export.safe_error or None,
        "download_url": (
            f"/api/exports/{export.id}/download" if export.state == "available" else None
        ),
    }
    if detail:
        result["requester_id"] = str(export.requester_id)
        result["filter_snapshot"] = export.filter_snapshot
        result["selection_snapshot"] = export.selection_snapshot
        result["items"] = [
            {
                "document_id": str(item.document_id),
                "state": item.state,
                "archive_path": item.archive_path or None,
                "safe_error": item.safe_error or None,
                "size_bytes": item.size_bytes,
            }
            for item in export.items.order_by("sequence", "id")
        ]
    return result


def _body(request: HttpRequest) -> dict[str, object] | None:
    try:
        value = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


@require_http_methods(["GET", "POST"])
def exports(request: HttpRequest) -> HttpResponseBase:
    actor = _identity(request)
    if actor is None:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    if request.method == "GET":
        if not authorize(actor.role, Action.CREATE_ZIP, actor_id=actor.user_id):
            return JsonResponse({"detail": "Acesso negado."}, status=403)
        return JsonResponse({"exports": [_payload(export) for export in list_exports(actor=actor)]})
    body = _body(request)
    if body is None or "idempotency_key" not in body:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    filters = {key: value for key, value in body.items() if key != "idempotency_key"}
    try:
        result = request_export(
            actor=actor, filters=filters, idempotency_key=body["idempotency_key"]
        )
    except ExportAccessDenied:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    except ExportError:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    return JsonResponse(_payload(result.export), status=200 if result.duplicate else 202)


@require_GET
def detail(request: HttpRequest, export_id: UUID) -> JsonResponse:
    actor = _identity(request)
    if actor is None:
        return JsonResponse({"detail": "Exportação não encontrada."}, status=404)
    export = get_export(actor=actor, export_id=export_id)
    if export is None:
        return JsonResponse({"detail": "Exportação não encontrada."}, status=404)
    return JsonResponse(_payload(export, detail=True))


@require_GET
def download(request: HttpRequest, export_id: UUID) -> HttpResponseBase:
    actor = _identity(request)
    if actor is None:
        return JsonResponse({"detail": "Exportação não disponível."}, status=404)
    export = get_export(actor=actor, export_id=export_id)
    if (
        export is None
        or export.state != "available"
        or export.expires_at <= timezone.now()
        or export.zip_artifact_id is None
    ):
        export_metrics.record("denied")
        return JsonResponse({"detail": "Exportação não disponível."}, status=404)
    try:
        stream = ArtifactStorageService(
            object_store_from_environment()  # type: ignore[arg-type]
        ).read_verified(
            export.zip_artifact_id
        )
        AuditService().append(
            action="export.download",
            entity_type="export",
            entity_id=str(export.id),
            result="success",
            actor_id=actor.user_id,
            actor_role=actor.role,
            context={"size_bytes": export.produced_bytes},
        )
    except Exception:
        export_metrics.record("denied")
        return JsonResponse({"detail": "Exportação não disponível."}, status=404)
    export_metrics.record("download")
    response = FileResponse(stream, content_type="application/zip", as_attachment=True)
    response["Content-Length"] = str(
        export.zip_artifact.size_bytes if export.zip_artifact else export.produced_bytes
    )
    response["Content-Disposition"] = f'attachment; filename="export-{str(export.id)[:12]}.zip"'
    response["Cache-Control"] = "no-store"
    return response


@require_http_methods(["POST"])
def cleanup(request: HttpRequest) -> JsonResponse:
    actor = _identity(request)
    if actor is None or not authorize(actor.role, Action.ADMINISTER_SYSTEM, actor_id=actor.user_id):
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    return JsonResponse({"cleaned": cleanup_expired()})
