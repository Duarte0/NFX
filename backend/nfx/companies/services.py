from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from nfx.adapters.opencnpj import OpenCnpjClient, OpenCnpjResponse
from nfx.audit.services import AuditService
from nfx.companies.metrics import company_metrics
from nfx.companies.models import (
    Company,
    CompanyFlow,
    CompanyStatus,
    EnrichmentSnapshot,
    EnrichmentStatus,
    FlowFamily,
    FlowState,
)
from nfx.identity.policy import Action, authorize
from nfx.identity.services import SessionIdentity

logger = logging.getLogger(__name__)
_CNPJ_CHARS = re.compile(r"^[A-Z0-9]+$")


class CompanyError(ValueError):
    pass


class InvalidCnpj(CompanyError):
    pass


class DuplicateCompanyCnpj(CompanyError):
    pass


class CompanyVersionConflict(CompanyError):
    pass


class CompanyCnpjImmutable(CompanyError):
    pass


class CompanyNotFound(CompanyError):
    pass


class CompanyInactive(CompanyError):
    pass


class InvalidCompanyFlow(CompanyError):
    pass


def normalize_cnpj(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidCnpj("CNPJ inválido.")
    normalized = re.sub(r"[.\-/\s]", "", value).upper()
    if not normalized or not _CNPJ_CHARS.fullmatch(normalized):
        raise InvalidCnpj("CNPJ inválido.")
    if normalized.isdigit():
        if len(normalized) != 14 or len(set(normalized)) == 1:
            raise InvalidCnpj("CNPJ inválido.")
        first = sum(
            int(digit) * weight
            for digit, weight in zip(normalized[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
        )
        first_digit = (11 - first % 11) % 10
        second = sum(
            int(digit) * weight
            for digit, weight in zip(
                normalized[:12] + str(first_digit), (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
            )
        )
        if normalized[-2:] != f"{first_digit}{(11 - second % 11) % 10}":
            raise InvalidCnpj("CNPJ inválido.")
    return normalized


def _require_company_access(actor: SessionIdentity) -> None:
    if not authorize(actor.role, Action.ADMINISTER_COMPANIES, actor_id=actor.user_id):
        raise CompanyError("Acesso de empresa necessário.")


def _validated_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompanyError("Razão social obrigatória.")
    return value.strip()


def _validated_reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompanyError("Motivo obrigatório.")
    return value.strip()


def _context(company: Company) -> dict[str, object]:
    return {
        "after": {
            "cnpj": company.cnpj,
            "legal_name": company.legal_name,
            "status": company.status,
            "first_collection_at": company.first_collection_at,
            "version": company.version,
        }
    }


def _company(company_id: str | UUID, *, lock: bool = False) -> Company:
    queryset: QuerySet[Company] = Company.objects.all()
    if lock:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(id=company_id)
    except Company.DoesNotExist as exc:
        raise CompanyNotFound("Empresa não encontrada.") from exc


def create_company(
    *, actor: SessionIdentity, cnpj: str, legal_name: str, ip_address: str
) -> Company:
    _require_company_access(actor)
    normalized = normalize_cnpj(cnpj)
    name = _validated_name(legal_name)
    try:
        with transaction.atomic():
            company = Company.objects.create(cnpj=normalized, legal_name=name)
            CompanyFlow.objects.bulk_create(
                [CompanyFlow(company=company, family=family) for family, _ in FlowFamily.choices]
            )
            AuditService().append(
                action="company.create",
                entity_type="company",
                entity_id=str(company.id),
                result="success",
                actor_id=actor.user_id,
                actor_role=actor.role,
                ip_address=ip_address,
                context=_context(company),
            )
            return company
    except IntegrityError as exc:
        raise DuplicateCompanyCnpj("Já existe uma empresa com este CNPJ.") from exc


def update_company(
    *,
    actor: SessionIdentity,
    company_id: str,
    version: int,
    legal_name: str,
    cnpj: str | None,
    ip_address: str,
) -> Company:
    _require_company_access(actor)
    name = _validated_name(legal_name)
    with transaction.atomic():
        company = _company(company_id, lock=True)
        if company.version != version:
            raise CompanyVersionConflict("Empresa alterada por outra solicitação.")
        normalized = company.cnpj if cnpj is None else normalize_cnpj(cnpj)
        if company.first_collection_at is not None and normalized != company.cnpj:
            raise CompanyCnpjImmutable("O CNPJ não pode ser alterado após a primeira coleta.")
        before = _context(company)
        company.cnpj = normalized
        company.legal_name = name
        company.version += 1
        try:
            company.save(update_fields=["cnpj", "legal_name", "version", "updated_at"])
        except IntegrityError as exc:
            raise DuplicateCompanyCnpj("Já existe uma empresa com este CNPJ.") from exc
        after = _context(company)
        after["before"] = before["after"]
        AuditService().append(
            action="company.update",
            entity_type="company",
            entity_id=str(company.id),
            result="success",
            actor_id=actor.user_id,
            actor_role=actor.role,
            ip_address=ip_address,
            context=after,
        )
        return company


def deactivate_company(
    *, actor: SessionIdentity, company_id: str, reason: str, ip_address: str
) -> Company:
    _require_company_access(actor)
    reason = _validated_reason(reason)
    with transaction.atomic():
        company = _company(company_id, lock=True)
        before = _context(company)
        company.status = CompanyStatus.DEACTIVATED
        company.deactivation_reason = reason
        company.deactivated_at = timezone.now()
        company.version += 1
        company.save(
            update_fields=[
                "status",
                "deactivation_reason",
                "deactivated_at",
                "version",
                "updated_at",
            ]
        )
        context = _context(company)
        context["before"] = before["after"]
        AuditService().append(
            action="company.deactivate",
            entity_type="company",
            entity_id=str(company.id),
            result="success",
            actor_id=actor.user_id,
            actor_role=actor.role,
            ip_address=ip_address,
            reason=reason,
            context=context,
        )
        return company


def activate_company(*, actor: SessionIdentity, company_id: str, ip_address: str) -> Company:
    _require_company_access(actor)
    with transaction.atomic():
        company = _company(company_id, lock=True)
        before = _context(company)
        company.status = CompanyStatus.ACTIVE
        company.version += 1
        company.save(update_fields=["status", "version", "updated_at"])
        context = _context(company)
        context["before"] = before["after"]
        AuditService().append(
            action="company.activate",
            entity_type="company",
            entity_id=str(company.id),
            result="success",
            actor_id=actor.user_id,
            actor_role=actor.role,
            ip_address=ip_address,
            context=context,
        )
        return company


def set_flow_state(
    *,
    actor: SessionIdentity,
    company_id: str,
    family: str,
    state: str,
    ip_address: str,
) -> CompanyFlow:
    _require_company_access(actor)
    if family not in FlowFamily.values or state not in FlowState.values:
        raise InvalidCompanyFlow("Fluxo ou estado inválido.")
    with transaction.atomic():
        company = _company(company_id, lock=True)
        if company.status != CompanyStatus.ACTIVE:
            raise CompanyInactive("A empresa precisa estar ativa para alterar o fluxo.")
        flow = CompanyFlow.objects.select_for_update().get(company=company, family=family)
        before = flow.state
        flow.state = state
        flow.save(update_fields=["state", "updated_at"])
        AuditService().append(
            action="company.flow_change",
            entity_type="company_flow",
            entity_id=str(flow.pk),
            result="success",
            actor_id=actor.user_id,
            actor_role=actor.role,
            ip_address=ip_address,
            context={
                "company_id": str(company.id),
                "family": family,
                "before": before,
                "after": state,
            },
        )
        return flow


def mark_first_collection(company_id: str, collected_at: datetime | None = None) -> Company:
    """Called by the future durable collector after its first durable document commit."""
    with transaction.atomic():
        company = _company(company_id, lock=True)
        if company.first_collection_at is None:
            company.first_collection_at = collected_at or timezone.now()
            company.version += 1
            company.save(update_fields=["first_collection_at", "version", "updated_at"])
        return company


def can_execute_flow(company_id: str, family: str, *, certificate_valid: bool) -> bool:
    if family not in FlowFamily.values or not certificate_valid:
        return False
    company = Company.objects.filter(id=company_id, status=CompanyStatus.ACTIVE).first()
    return bool(
        company
        and CompanyFlow.objects.filter(
            company=company, family=family, state=FlowState.ENABLED
        ).exists()
    )


@dataclass(frozen=True)
class EnrichmentResult:
    snapshot: EnrichmentSnapshot
    duration_ms: float


def _normalize_response(response: OpenCnpjResponse | object) -> OpenCnpjResponse:
    if not isinstance(response, OpenCnpjResponse):
        if isinstance(response, dict):
            return OpenCnpjResponse("success", response)
        if response is None:
            return OpenCnpjResponse("empty")
        return OpenCnpjResponse("malformed", error_code="resposta_nao_json")
    if response.status == "success" and not isinstance(response.payload, dict | list):
        return OpenCnpjResponse("malformed", error_code="conteudo_invalido")
    return response


def request_enrichment(
    *,
    actor: SessionIdentity,
    company_id: str,
    client: OpenCnpjClient,
    ip_address: str,
) -> EnrichmentResult:
    _require_company_access(actor)
    company = _company(company_id)
    started = time.perf_counter()
    try:
        response = _normalize_response(client.fetch(company.cnpj))
    except TimeoutError as exc:
        response = OpenCnpjResponse("timeout", error_code=type(exc).__name__)
    except FileNotFoundError as exc:
        response = OpenCnpjResponse("not_found", error_code=type(exc).__name__)
    except Exception as exc:  # external adapter failures are informational, never fiscal state
        response = OpenCnpjResponse("unavailable", error_code=type(exc).__name__)
    duration_ms = (time.perf_counter() - started) * 1000
    status_map = {
        "success": EnrichmentStatus.SUCCESS,
        "empty": EnrichmentStatus.EMPTY,
        "not_found": EnrichmentStatus.NOT_FOUND,
        "timeout": EnrichmentStatus.TIMEOUT,
        "unavailable": EnrichmentStatus.UNAVAILABLE,
        "malformed": EnrichmentStatus.MALFORMED,
    }
    status = status_map.get(response.status, EnrichmentStatus.UNAVAILABLE)
    payload: object = response.payload if status == EnrichmentStatus.SUCCESS else {}
    if status == EnrichmentStatus.SUCCESS and not isinstance(payload, dict | list):
        status, payload = EnrichmentStatus.MALFORMED, {}
    with transaction.atomic():
        snapshot = EnrichmentSnapshot.objects.create(
            company=company,
            requested_cnpj=company.cnpj,
            status=status,
            payload=cast(dict[str, Any] | list[Any], payload),
            error_code=response.error_code,
        )
        AuditService().append(
            action="company.enrichment",
            entity_type="company",
            entity_id=str(company.id),
            result=status,
            actor_id=actor.user_id,
            actor_role=actor.role,
            ip_address=ip_address,
            context={"source": "opencnpj", "status": status, "duration_ms": round(duration_ms, 2)},
        )
    company_metrics.record_enrichment(status, duration_ms)
    logger.info(
        "company_public_enrichment",
        extra={
            "company_id": str(company.id),
            "source": "opencnpj",
            "status": status,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return EnrichmentResult(snapshot=snapshot, duration_ms=duration_ms)
