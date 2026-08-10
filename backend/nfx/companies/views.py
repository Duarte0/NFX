from __future__ import annotations

import json
from uuid import UUID

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from nfx.adapters.opencnpj import UnavailableOpenCnpjClient
from nfx.companies.models import Company, CompanyFlow, EnrichmentSnapshot
from nfx.companies.services import (
    CompanyCnpjImmutable,
    CompanyError,
    CompanyInactive,
    CompanyNotFound,
    CompanyVersionConflict,
    DuplicateCompanyCnpj,
    InvalidCnpj,
    InvalidCompanyFlow,
    activate_company,
    create_company,
    deactivate_company,
    request_enrichment,
    set_flow_state,
    update_company,
)
from nfx.identity.policy import Action
from nfx.identity.services import resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME, protected


def _json_body(request: HttpRequest) -> dict[str, object] | None:
    try:
        body = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return body if isinstance(body, dict) else None


def _ip(request: HttpRequest) -> str:
    return str(request.META.get("REMOTE_ADDR", ""))


def _company_payload(company: Company) -> dict[str, object]:
    flows = {
        flow.family: {"state": flow.state, "id": str(flow.pk)}
        for flow in CompanyFlow.objects.filter(company=company)
    }
    latest = EnrichmentSnapshot.objects.filter(company=company).first()
    return {
        "id": str(company.id),
        "cnpj": company.cnpj,
        "legal_name": company.legal_name,
        "status": company.status,
        "first_collection_at": company.first_collection_at.isoformat()
        if company.first_collection_at
        else None,
        "deactivation_reason": company.deactivation_reason,
        "deactivated_at": company.deactivated_at.isoformat() if company.deactivated_at else None,
        "version": company.version,
        "flows": flows,
        "enrichment": _enrichment_payload(latest) if latest else None,
    }


def _enrichment_payload(snapshot: EnrichmentSnapshot) -> dict[str, object]:
    return {
        "source": snapshot.source,
        "obtained_at": snapshot.obtained_at.isoformat(),
        "status": snapshot.status,
        "public_non_authoritative": snapshot.public_non_authoritative,
        "payload": snapshot.payload,
        "error_code": snapshot.error_code,
    }


def _error(exc: Exception) -> JsonResponse:
    if isinstance(exc, DuplicateCompanyCnpj):
        return JsonResponse({"detail": str(exc)}, status=409)
    if isinstance(exc, CompanyVersionConflict | CompanyCnpjImmutable):
        return JsonResponse({"detail": str(exc)}, status=409)
    if isinstance(exc, CompanyNotFound):
        return JsonResponse({"detail": str(exc)}, status=404)
    if isinstance(exc, InvalidCnpj | CompanyInactive | InvalidCompanyFlow | CompanyError):
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"detail": "Não foi possível concluir a operação."}, status=400)


@require_GET
@protected(Action.ADMINISTER_COMPANIES)
def companies(request: HttpRequest) -> JsonResponse:
    queryset = Company.objects.prefetch_related("flows", "enrichment_snapshots").order_by("id")
    status = request.GET.get("status")
    search = request.GET.get("search", "").strip()
    if status:
        queryset = queryset.filter(status=status)
    if search:
        queryset = queryset.filter(legal_name__icontains=search) | queryset.filter(
            cnpj__icontains=search
        )
    try:
        limit = min(max(int(request.GET.get("limit", "50")), 1), 100)
        cursor = UUID(request.GET["cursor"]) if request.GET.get("cursor") else None
    except (KeyError, ValueError):
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    if cursor:
        queryset = queryset.filter(id__gt=cursor)
    rows = list(queryset[: limit + 1])
    return JsonResponse(
        {
            "companies": [_company_payload(row) for row in rows[:limit]],
            "next_cursor": str(rows[limit].id) if len(rows) > limit else None,
        }
    )


@require_POST
@protected(Action.ADMINISTER_COMPANIES)
def company_create(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None or body is None:
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    cnpj, legal_name = body.get("cnpj"), body.get("legal_name")
    if not isinstance(cnpj, str) or not isinstance(legal_name, str):
        return JsonResponse({"detail": "CNPJ e razão social são obrigatórios."}, status=400)
    try:
        company = create_company(
            actor=identity, cnpj=cnpj, legal_name=legal_name, ip_address=_ip(request)
        )
    except CompanyError as exc:
        return _error(exc)
    company = Company.objects.prefetch_related("flows").get(id=company.id)
    return JsonResponse({"company": _company_payload(company)}, status=201)


@require_http_methods(["GET", "PATCH"])
@protected(Action.ADMINISTER_COMPANIES)
def company_detail(request: HttpRequest, company_id: UUID) -> JsonResponse:
    if request.method == "GET":
        try:
            company = Company.objects.prefetch_related("flows", "enrichment_snapshots").get(
                id=company_id
            )
        except Company.DoesNotExist:
            return _error(CompanyNotFound("Empresa não encontrada."))
        return JsonResponse({"company": _company_payload(company)})
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None or body is None or not isinstance(body.get("legal_name"), str):
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    legal_name = body["legal_name"]
    assert isinstance(legal_name, str)
    version = body.get("version")
    cnpj = body.get("cnpj")
    if (
        not isinstance(version, int)
        or version < 1
        or (cnpj is not None and not isinstance(cnpj, str))
    ):
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    try:
        company = update_company(
            actor=identity,
            company_id=str(company_id),
            version=version,
            legal_name=legal_name,
            cnpj=cnpj,
            ip_address=_ip(request),
        )
    except CompanyError as exc:
        return _error(exc)
    return JsonResponse({"company": _company_payload(company)})


@require_POST
@protected(Action.ADMINISTER_COMPANIES)
def company_activate(request: HttpRequest, company_id: UUID) -> JsonResponse:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        company = activate_company(
            actor=identity, company_id=str(company_id), ip_address=_ip(request)
        )
    except CompanyError as exc:
        return _error(exc)
    return JsonResponse({"company": _company_payload(company)})


@require_POST
@protected(Action.ADMINISTER_COMPANIES)
def company_deactivate(request: HttpRequest, company_id: UUID) -> JsonResponse:
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None or body is None or body.get("confirmed") is not True:
        return JsonResponse(
            {"detail": "Confirmação explícita e motivo são obrigatórios."}, status=400
        )
    reason = body.get("reason")
    if not isinstance(reason, str):
        return JsonResponse(
            {"detail": "Confirmação explícita e motivo são obrigatórios."}, status=400
        )
    try:
        company = deactivate_company(
            actor=identity, company_id=str(company_id), reason=reason, ip_address=_ip(request)
        )
    except CompanyError as exc:
        return _error(exc)
    return JsonResponse({"company": _company_payload(company)})


@require_POST
@protected(Action.ADMINISTER_COMPANIES)
def company_flow(request: HttpRequest, company_id: UUID, family: str) -> JsonResponse:
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    state = body.get("state") if body else None
    if identity is None or not isinstance(state, str):
        return JsonResponse({"detail": "Estado de fluxo inválido."}, status=400)
    try:
        flow = set_flow_state(
            actor=identity,
            company_id=str(company_id),
            family=family,
            state=state,
            ip_address=_ip(request),
        )
    except CompanyError as exc:
        return _error(exc)
    return JsonResponse({"flow": {"id": str(flow.pk), "family": flow.family, "state": flow.state}})


@require_POST
@protected(Action.ADMINISTER_COMPANIES)
def company_enrichment(request: HttpRequest, company_id: UUID) -> JsonResponse:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        result = request_enrichment(
            actor=identity,
            company_id=str(company_id),
            client=UnavailableOpenCnpjClient(),
            ip_address=_ip(request),
        )
    except CompanyError as exc:
        return _error(exc)
    return JsonResponse({"enrichment": _enrichment_payload(result.snapshot)})
