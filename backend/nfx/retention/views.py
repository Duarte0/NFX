from __future__ import annotations

import hashlib
import time
from typing import cast
from uuid import UUID

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from nfx.audit.services import AuditService, AuditUnavailable
from nfx.identity.policy import Action
from nfx.identity.services import resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME, protected
from nfx.retention.metrics import retention_metrics
from nfx.retention.services import (
    RULE_VERSION,
    InvalidRetentionParams,
    RetentionParams,
    list_retention_documents,
    parse_retention_params,
    retention_detail,
    retention_preview,
)


def _audit_read(
    request: HttpRequest,
    *,
    action: str,
    entity_id: str,
    result: str,
    context: dict[str, object],
) -> bool:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return False
    try:
        AuditService().append(
            action=action,
            entity_type="retention",
            entity_id=entity_id,
            result=result,
            actor_id=identity.user_id,
            actor_role=identity.role,
            ip_address=str(request.META.get("REMOTE_ADDR", "")),
            correlation_id=hashlib.sha256(f"{action}:{entity_id}".encode()).hexdigest()[:32],
            context=context,
        )
    except AuditUnavailable:
        return False
    return True


def _params(request: HttpRequest) -> RetentionParams | JsonResponse:
    try:
        return parse_retention_params(request.GET)
    except InvalidRetentionParams:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)


@require_GET
@protected(Action.READ_RETENTION)
def documents(request: HttpRequest) -> JsonResponse:
    params = _params(request)
    if isinstance(params, JsonResponse):
        return params
    payload = list_retention_documents(params)
    for item in cast(list[dict[str, object]], payload["documents"]):
        retention_metrics.record_decision(str(item["state"]))
    if not _audit_read(
        request,
        action="retention.list",
        entity_id="",
        result="success" if payload["documents"] else "empty",
        context={
            "count": len(cast(list[object], payload["documents"])),
            "scope": "bounded",
            "rule_version": RULE_VERSION,
        },
    ):
        return JsonResponse({"detail": "Consulta temporariamente indisponível."}, status=503)
    return JsonResponse(payload)


@require_GET
@protected(Action.READ_RETENTION)
def detail(request: HttpRequest, document_id: UUID) -> JsonResponse:
    params = _params(request)
    if isinstance(params, JsonResponse):
        return params
    result = retention_detail(document_id, as_of=params.as_of)
    found = result is not None
    if result is not None:
        decision = cast(dict[str, object], result["decision"])
        retention_metrics.record_decision(str(decision["state"]))
    if not _audit_read(
        request,
        action="retention.detail",
        entity_id=str(document_id),
        result="success" if found else "not_found",
        context={"scope": "detail", "rule_version": RULE_VERSION},
    ):
        return JsonResponse({"detail": "Consulta temporariamente indisponível."}, status=503)
    if result is None:
        return JsonResponse({"detail": "Documento não encontrado."}, status=404)
    return JsonResponse(result)


@require_GET
@protected(Action.READ_RETENTION)
def preview(request: HttpRequest, document_id: UUID) -> JsonResponse:
    params = _params(request)
    if isinstance(params, JsonResponse):
        return params
    expected_scope_hash = request.GET.get("scope_hash")
    if expected_scope_hash is not None and (
        len(expected_scope_hash) != 64
        or any(char not in "0123456789abcdef" for char in expected_scope_hash)
    ):
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    started = time.perf_counter()
    payload, stale = retention_preview(
        document_id,
        as_of=params.as_of,
        expected_scope_hash=expected_scope_hash,
    )
    if payload is None:
        result = "not_found"
    elif stale:
        result = "stale"
    else:
        result = "success"
    retention_metrics.record_preview(result)
    if not _audit_read(
        request,
        action="retention.preview",
        entity_id=str(document_id),
        result=result,
        context={
            "scope": "metadata",
            "rule_version": RULE_VERSION,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    ):
        return JsonResponse({"detail": "Prévia temporariamente indisponível."}, status=503)
    if payload is None:
        return JsonResponse({"detail": "Documento não encontrado."}, status=404)
    if stale:
        return JsonResponse(payload, status=409)
    return JsonResponse(payload)
