from __future__ import annotations

import json
from uuid import UUID

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from nfx.collection.models import (
    CollectionExecution,
    CollectionOrigin,
    CollectionScope,
)
from nfx.collection.services import (
    CollectionBlocked,
    CollectionCertificateUnavailable,
    CollectionCooldown,
    CollectionError,
    CollectionFlowPaused,
    CollectionPolicyUnavailable,
    CollectionRetryNotEligible,
    request_collection,
)
from nfx.companies.models import AdnCoverageSnapshot, Company, CompanyFlow
from nfx.identity.policy import Action
from nfx.identity.services import resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME, protected


def _body(request: HttpRequest) -> dict[str, object] | None:
    try:
        value = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _ip(request: HttpRequest) -> str:
    return str(request.META.get("REMOTE_ADDR", ""))


def _execution_payload(execution: CollectionExecution) -> dict[str, object]:
    return {
        "id": str(execution.id),
        "company_id": str(execution.company_id),
        "family": execution.family,
        "requested_scope": execution.requested_scope,
        "origin": execution.origin,
        "state": execution.state,
        "outcome": execution.outcome,
        "recovery": execution.recovery,
        "safe_summary": execution.safe_summary,
        "safe_error": execution.safe_error,
        "correlation_id": execution.correlation_id,
        "created_at": execution.created_at.isoformat(),
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
    }


def _flow_payload(flow: CompanyFlow) -> dict[str, object]:
    latest = (
        CollectionExecution.objects.filter(company_id=flow.company_id, family=flow.family)
        .order_by("-created_at")
        .first()
    )
    coverage = None
    if flow.family == "nfse":
        snapshot = (
            AdnCoverageSnapshot.objects.filter(company_id=flow.company_id)
            .order_by("-verified_at", "-id")
            .first()
        )
        if snapshot is not None:
            coverage = {
                "status": snapshot.status,
                "source": snapshot.source,
                "verified_at": snapshot.verified_at.isoformat(),
                "policy_version": snapshot.policy_version,
            }
    return {
        "family": flow.family,
        "flow_state": flow.state,
        "collection_state": flow.collection_state,
        "last_attempt_at": flow.last_attempt_at.isoformat() if flow.last_attempt_at else None,
        "last_success_at": flow.last_success_at.isoformat() if flow.last_success_at else None,
        "next_scheduled_at": flow.next_scheduled_at.isoformat() if flow.next_scheduled_at else None,
        "cooldown_until": flow.cooldown_until.isoformat() if flow.cooldown_until else None,
        "blocked_reason": flow.blocked_reason,
        "safe_error": flow.safe_error,
        "progress": {"current": flow.progress_current, "total": flow.progress_total},
        "coverage": coverage,
        "active_execution": (
            _execution_payload(CollectionExecution.objects.get(id=flow.active_execution_id))
            if flow.active_execution_id
            else None
        ),
        "latest_execution": _execution_payload(latest) if latest else None,
    }


def _error(exc: Exception) -> JsonResponse:
    if isinstance(exc, CollectionBlocked | CollectionCooldown):
        return JsonResponse({"detail": getattr(exc, "code", "collection_rejected")}, status=409)
    if isinstance(
        exc,
        CollectionRetryNotEligible
        | CollectionFlowPaused
        | CollectionCertificateUnavailable
        | CollectionPolicyUnavailable,
    ):
        return JsonResponse({"detail": getattr(exc, "code", "collection_rejected")}, status=400)
    if isinstance(exc, CollectionError):
        return JsonResponse({"detail": getattr(exc, "code", "collection_rejected")}, status=400)
    return JsonResponse({"detail": "Não foi possível concluir a coleta."}, status=503)


@require_GET
@protected(Action.READ_DOCUMENTS)
def collections(_: HttpRequest) -> JsonResponse:
    rows = []
    for company in Company.objects.order_by("id"):
        rows.append(
            {
                "company_id": str(company.id),
                "legal_name": company.legal_name,
                "status": company.status,
                "flows": [_flow_payload(flow) for flow in company.flows.order_by("family")],
            }
        )
    return JsonResponse({"collections": rows})


@require_GET
@protected(Action.READ_DOCUMENTS)
def status(_: HttpRequest, company_id: UUID) -> JsonResponse:
    company = Company.objects.filter(id=company_id).first()
    if company is None:
        return JsonResponse({"detail": "Empresa não encontrada."}, status=404)
    return JsonResponse(
        {
            "company_id": str(company.id),
            "legal_name": company.legal_name,
            "status": company.status,
            "flows": [_flow_payload(flow) for flow in company.flows.order_by("family")],
        }
    )


@require_POST
@protected(Action.CONTROL_COLLECTIONS)
def request(request: HttpRequest, company_id: UUID) -> JsonResponse:
    body = _body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    scope = body.get("scope") if body else None
    if identity is None or not isinstance(scope, str):
        return JsonResponse({"detail": "Dados de coleta inválidos."}, status=400)
    try:
        result = request_collection(
            company_id=company_id,
            scope=CollectionScope(scope),
            origin=CollectionOrigin.MANUAL,
            actor=identity,
            ip_address=_ip(request),
        )
    except (ValueError, CollectionError) as exc:
        return _error(exc)
    return JsonResponse(
        {
            "duplicate": result.duplicate,
            "executions": [_execution_payload(row) for row in result.executions],
        },
        status=200 if result.duplicate else 202,
    )


@require_POST
@protected(Action.CONTROL_COLLECTIONS)
def retry(request: HttpRequest, company_id: UUID, execution_id: UUID) -> JsonResponse:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    execution = CollectionExecution.objects.filter(id=execution_id, company_id=company_id).first()
    if execution is None:
        return JsonResponse({"detail": "Execução não encontrada."}, status=404)
    try:
        result = request_collection(
            company_id=company_id,
            scope=execution.family,
            origin=CollectionOrigin.RETRY,
            actor=identity,
            ip_address=_ip(request),
            retry_execution_id=execution.id,
        )
    except (ValueError, CollectionError) as exc:
        return _error(exc)
    return JsonResponse(
        {
            "duplicate": result.duplicate,
            "executions": [_execution_payload(row) for row in result.executions],
        },
        status=200 if result.duplicate else 202,
    )
