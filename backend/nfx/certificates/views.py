from __future__ import annotations

from uuid import UUID

from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from nfx.certificates.models import Certificate, CertificateState
from nfx.certificates.services import (
    CertificateAlreadyAssigned,
    CertificateCnpjMismatch,
    CertificateError,
    CertificateExpired,
    CertificateInventoryQueryError,
    CertificateNotFound,
    CertificateStorageFailure,
    CertificateTooLarge,
    CertificateUnreadable,
    CertificateWrongPassword,
    add_certificate,
    certificate_inventory_after_cursor,
    certificate_inventory_queryset,
    certificate_inventory_row,
    certificate_payload,
    normalize_certificate_inventory_query,
)
from nfx.companies.models import Company
from nfx.identity.policy import Action
from nfx.identity.services import resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME, protected


def _error(exc: Exception) -> JsonResponse:
    if isinstance(exc, CertificateNotFound):
        return JsonResponse({"detail": str(exc)}, status=404)
    if isinstance(exc, CertificateAlreadyAssigned):
        return JsonResponse({"detail": str(exc)}, status=409)
    if isinstance(
    exc,
    (
        CertificateTooLarge
        | CertificateWrongPassword
        | CertificateUnreadable
        | CertificateExpired
        | CertificateCnpjMismatch
    ),
    ):
        return JsonResponse({"detail": str(exc)}, status=400)
    if isinstance(exc, CertificateStorageFailure):
        return JsonResponse(
            {"detail": "Não foi possível armazenar o certificado com integridade."}, status=503
        )
    return JsonResponse(
        {"detail": "Não foi possível concluir a operação do certificado."}, status=400
    )


@require_GET
@protected(Action.ADMINISTER_CERTIFICATES)
def certificate_detail(request: HttpRequest, company_id: UUID) -> JsonResponse:
    try:
        company = Company.objects.get(pk=company_id)
    except Company.DoesNotExist:
        return _error(CertificateNotFound("Empresa não encontrada."))
    certificate = Certificate.objects.filter(
        company=company, state=CertificateState.CURRENT
    ).first()
    response = JsonResponse({"certificate": certificate_payload(certificate)})
    response["Cache-Control"] = "no-store"
    return response


@require_GET
@protected(Action.ADMINISTER_CERTIFICATES)
def certificate_inventory(request: HttpRequest) -> JsonResponse:
    try:
        selected = normalize_certificate_inventory_query(request.GET)
    except CertificateInventoryQueryError:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)

    evaluated_at = timezone.now()
    try:
        filtered = certificate_inventory_queryset(selected.filter_name, evaluated_at)
        total = filtered.count()
        rows = list(
            certificate_inventory_after_cursor(filtered, selected.cursor)[: selected.limit + 1]
        )
        page = rows[: selected.limit]
        payload = [certificate_inventory_row(certificate, now=evaluated_at) for certificate in page]
    except Exception:
        return JsonResponse(
            {"detail": "Não foi possível consultar o inventário de certificados."}, status=503
        )

    response = JsonResponse(
        {
            "certificates": payload,
            "filter": selected.filter_payload,
            "evaluated_at": evaluated_at.isoformat(),
            "freshness": {
                "status": "fresh",
                "evaluated_at": evaluated_at.isoformat(),
                "age_seconds": 0,
            },
            "total": total,
            "limit": selected.limit,
            "truncated": len(rows) > selected.limit,
            "next_cursor": (
                f"{page[-1].company_id}:{page[-1].id}"
                if len(rows) > selected.limit and page
                else None
            ),
        }
    )
    response["Cache-Control"] = "no-store"
    return response


@require_POST
@protected(Action.ADMINISTER_CERTIFICATES)
def certificate_upload(request: HttpRequest, company_id: UUID) -> JsonResponse:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    uploaded = request.FILES.get("certificate")
    password = request.POST.get("password")
    if identity is None or uploaded is None or not isinstance(password, str) or not password:
        return JsonResponse({"detail": "Arquivo .pfx e senha são obrigatórios."}, status=400)
    filename = uploaded.name or ""
    if not filename.lower().endswith(".pfx"):
        return JsonResponse({"detail": "O arquivo deve ter extensão .pfx."}, status=400)
    if uploaded.size is not None and uploaded.size > 5 * 1024 * 1024:
        return _error(CertificateTooLarge("O arquivo do certificado excede o limite permitido."))
    pfx = uploaded.read(5 * 1024 * 1024 + 1)
    try:
        certificate = add_certificate(
            actor=identity,
            company_id=str(company_id),
            pfx=pfx,
            password=password,
            ip_address=str(request.META.get("REMOTE_ADDR", "")),
        )
    except CertificateError as exc:
        return _error(exc)
    response = JsonResponse({"certificate": certificate_payload(certificate)}, status=201)
    response["Cache-Control"] = "no-store"
    return response
