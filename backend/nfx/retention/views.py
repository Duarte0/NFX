from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from functools import wraps
from typing import cast
from uuid import UUID

from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from nfx.audit.services import AuditService, AuditUnavailable
from nfx.identity.policy import Action
from nfx.identity.services import require_authorized, resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME, protected
from nfx.retention.deletion import (
    DeletionError,
    DeletionNotEligible,
    DeletionNotFound,
    DeletionStaleScope,
    operation_payload,
    request_deletion,
    resume_deletion,
)
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


def _body(request: HttpRequest) -> dict[str, object] | None:
    try:
        value = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _audit_denial(request: HttpRequest, document_id: UUID, code: str, reason: str = "") -> bool:
    retention_metrics.record_deletion("blocked")
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return True
    try:
        AuditService().append(
            action="document.delete.denied",
            entity_type="document",
            entity_id=str(document_id),
            result="denied",
            actor_id=identity.user_id,
            actor_role=identity.role,
            ip_address=str(request.META.get("REMOTE_ADDR", "")),
            correlation_id=hashlib.sha256(f"delete-denied:{document_id}".encode()).hexdigest()[:32],
            reason=reason.strip()[:1000] or "request_rejected",
            context={"code": code},
        )
    except AuditUnavailable:
        return False
    return True


def _audit_access_denial(request: HttpRequest, *, entity_type: str, entity_id: str) -> bool:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return True
    try:
        AuditService().append(
            action="document.delete.denied",
            entity_type=entity_type,
            entity_id=entity_id,
            result="denied",
            actor_id=identity.user_id,
            actor_role=identity.role,
            ip_address=str(request.META.get("REMOTE_ADDR", "")),
            correlation_id=hashlib.sha256(f"delete-access:{entity_id}".encode()).hexdigest()[:32],
            reason="authorization_denied",
            context={"code": "access_denied"},
        )
    except AuditUnavailable:
        return False
    return True


def _protected_deletion(
    view: Callable[..., HttpResponseBase],
) -> Callable[..., HttpResponseBase]:
    @wraps(view)
    def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
        identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME))
        if not require_authorized(identity, Action.DELETE_RETENTION.value):
            retention_metrics.record_deletion("blocked")
            entity_type = "document" if "document_id" in kwargs else "retention"
            entity_id = str(kwargs.get("document_id") or kwargs.get("operation_id") or "")
            if not _audit_access_denial(
                request, entity_type=entity_type, entity_id=entity_id
            ):
                return JsonResponse(
                    {"detail": "Operação temporariamente indisponível."}, status=503
                )
            return JsonResponse({"detail": "Acesso negado."}, status=403)
        return view(request, *args, **kwargs)

    return wrapped


@require_POST
@_protected_deletion
def request(request: HttpRequest, document_id: UUID) -> JsonResponse:
    body = _body(request)
    if body is None:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    try:
        result = request_deletion(
            actor=identity,
            document_id=document_id,
            scope_hash_value=body.get("scope_hash"),
            scope_version=body.get("scope_version"),
            confirmation=body.get("confirmation"),
            reason=body.get("reason"),
        )
    except DeletionNotFound:
        _audit_denial(request, document_id, "not_found")
        return JsonResponse({"detail": "Documento não encontrado."}, status=404)
    except DeletionStaleScope:
        if not _audit_denial(request, document_id, "scope_changed", str(body.get("reason", ""))):
            return JsonResponse({"detail": "Operação temporariamente indisponível."}, status=503)
        return JsonResponse(
            {"detail": "A prévia está desatualizada.", "reason_code": "scope_changed"},
            status=409,
        )
    except DeletionNotEligible as exc:
        if not _audit_denial(request, document_id, exc.code, str(body.get("reason", ""))):
            return JsonResponse({"detail": "Operação temporariamente indisponível."}, status=503)
        return JsonResponse(
            {"detail": "O documento não é elegível.", "reason_code": exc.code}, status=409
        )
    except DeletionError as exc:
        if not _audit_denial(request, document_id, exc.code, str(body.get("reason", ""))):
            return JsonResponse({"detail": "Operação temporariamente indisponível."}, status=503)
        status = 409 if exc.code == "operation_active" else 400
        return JsonResponse(
            {"detail": "Não foi possível solicitar a exclusão.", "reason_code": exc.code},
            status=status,
        )
    return JsonResponse(
        operation_payload(result.operation), status=200 if result.duplicate else 202
    )


@require_GET
@_protected_deletion
def deletion_status(request: HttpRequest, operation_id: UUID) -> JsonResponse:
    from nfx.retention.models import DeletionOperation

    operation = DeletionOperation.objects.filter(pk=operation_id).first()
    if operation is None:
        return JsonResponse({"detail": "Operação não encontrada."}, status=404)
    return JsonResponse(operation_payload(operation))


@require_POST
@_protected_deletion
def resume(request: HttpRequest, operation_id: UUID) -> JsonResponse:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    try:
        operation = resume_deletion(actor=identity, operation_id=operation_id)
    except DeletionNotFound:
        return JsonResponse({"detail": "Operação não encontrada."}, status=404)
    except DeletionError:
        return JsonResponse({"detail": "Não foi possível retomar a operação."}, status=409)
    return JsonResponse(
        operation_payload(operation), status=200 if operation.state == "completed" else 202
    )
