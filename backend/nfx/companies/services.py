from __future__ import annotations

import logging
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from nfx.adapters.opencnpj import OpenCnpjClient, OpenCnpjResponse
from nfx.audit.services import AuditService
from nfx.companies.metrics import company_metrics
from nfx.companies.models import (
    AdnCoverageSnapshot,
    AdnCoverageStatus,
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
_SAFE_ADN_REFERENCE = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")


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


class CompanyListQueryError(ValueError):
    """A company list query is outside its bounded read contract."""


COMPANY_LIFECYCLE_STATUS_FILTERS: dict[str, tuple[str, ...]] = {
    "active": (CompanyStatus.ACTIVE,),
    "inactive": (CompanyStatus.REGISTERED, CompanyStatus.DEACTIVATED),
}
COMPANY_LIST_QUERY_KEYS = frozenset(("lifecycle", "status", "search", "limit", "cursor"))
MAX_COMPANY_LIST_SEARCH_LENGTH = 255
MAX_COMPANY_LIST_ROWS = 100


@dataclass(frozen=True)
class CompanyListFilter:
    lifecycle: str | None
    status: str | None
    search: str | None
    limit: int
    cursor: UUID | None

    @property
    def statuses(self) -> tuple[str, ...] | None:
        if self.lifecycle is not None:
            return COMPANY_LIFECYCLE_STATUS_FILTERS[self.lifecycle]
        if self.status is not None:
            return (self.status,)
        return None

    @property
    def filter_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.lifecycle is not None:
            payload["lifecycle"] = self.lifecycle
        elif self.status is not None:
            payload["status"] = self.status
        if self.search is not None:
            payload["search"] = self.search
        return payload


def _company_query_values(query: Mapping[str, object], key: str) -> list[object]:
    getlist = getattr(query, "getlist", None)
    if callable(getlist):
        return list(getlist(key))
    value = query.get(key)
    if isinstance(value, list | tuple):
        return list(value)
    return [] if value is None else [value]


def _company_query_single(query: Mapping[str, object], key: str) -> object | None:
    values = _company_query_values(query, key)
    if len(values) > 1:
        raise CompanyListQueryError("company list parameter is repeated")
    return values[0] if values else None


def normalize_company_list_filter(query: Mapping[str, object]) -> CompanyListFilter:
    """Normalize the legacy company filters plus one dashboard lifecycle filter."""
    if set(query.keys()) - COMPANY_LIST_QUERY_KEYS:
        raise CompanyListQueryError("unsupported company list parameter")

    lifecycle_value = _company_query_single(query, "lifecycle")
    lifecycle: str | None
    if lifecycle_value is None:
        lifecycle = None
    elif (
        not isinstance(lifecycle_value, str)
        or lifecycle_value not in COMPANY_LIFECYCLE_STATUS_FILTERS
    ):
        raise CompanyListQueryError("company lifecycle filter is invalid")
    else:
        lifecycle = lifecycle_value

    status_value = _company_query_single(query, "status")
    status: str | None
    if status_value in (None, ""):
        status = None
    elif not isinstance(status_value, str) or status_value not in CompanyStatus.values:
        raise CompanyListQueryError("company status filter is invalid")
    else:
        status = status_value
    if lifecycle is not None and status is not None:
        raise CompanyListQueryError("company filters conflict")

    search_value = _company_query_single(query, "search")
    if search_value in (None, ""):
        search = None
    elif not isinstance(search_value, str):
        raise CompanyListQueryError("company search is invalid")
    else:
        search = search_value.strip()
        if len(search) > MAX_COMPANY_LIST_SEARCH_LENGTH or any(
            ord(character) < 32 for character in search
        ):
            raise CompanyListQueryError("company search is invalid")
        search = search or None

    limit_value = _company_query_single(query, "limit")
    try:
        limit = int(str(limit_value)) if limit_value is not None else 50
    except (TypeError, ValueError) as exc:
        raise CompanyListQueryError("company limit is invalid") from exc
    limit = min(max(limit, 1), MAX_COMPANY_LIST_ROWS)

    cursor_value = _company_query_single(query, "cursor")
    if cursor_value in (None, ""):
        cursor = None
    elif not isinstance(cursor_value, str):
        raise CompanyListQueryError("company cursor is invalid")
    else:
        try:
            cursor = UUID(cursor_value)
        except ValueError as exc:
            raise CompanyListQueryError("company cursor is invalid") from exc

    return CompanyListFilter(
        lifecycle=lifecycle,
        status=status,
        search=search,
        limit=limit,
        cursor=cursor,
    )


def company_queryset_for_lifecycle(lifecycle: str) -> QuerySet[Company]:
    """Return the canonical company status queryset used by dashboard cards."""
    try:
        statuses = COMPANY_LIFECYCLE_STATUS_FILTERS[lifecycle]
    except KeyError as exc:
        raise CompanyListQueryError("company lifecycle filter is invalid") from exc
    return Company.objects.filter(status__in=statuses)


def company_list_queryset(
    selected: CompanyListFilter, *, apply_cursor: bool = True
) -> QuerySet[Company]:
    """Build the bounded list query from the same lifecycle/status predicates as the dashboard."""
    queryset = Company.objects.prefetch_related("flows", "enrichment_snapshots").order_by("id")
    if selected.statuses is not None:
        queryset = queryset.filter(status__in=selected.statuses)
    if selected.search is not None:
        queryset = queryset.filter(
            Q(legal_name__icontains=selected.search) | Q(cnpj__icontains=selected.search)
        )
    if apply_cursor and selected.cursor is not None:
        queryset = queryset.filter(id__gt=selected.cursor)
    return queryset


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


def record_adn_coverage(
    *,
    company_id: UUID | str,
    source: str,
    status: str,
    policy_version: str,
    evidence_reference: str = "",
    verified_at: datetime | None = None,
) -> AdnCoverageSnapshot:
    """Persist only the bounded coverage evidence emitted by the ADN adapter."""
    if not _SAFE_ADN_REFERENCE.fullmatch(source):
        raise CompanyError("ADN coverage source is invalid.")
    if not _SAFE_ADN_REFERENCE.fullmatch(policy_version):
        raise CompanyError("ADN coverage policy is invalid.")
    if evidence_reference and not _SAFE_ADN_REFERENCE.fullmatch(evidence_reference):
        raise CompanyError("ADN coverage evidence is invalid.")
    try:
        normalized_status = AdnCoverageStatus(status)
    except (TypeError, ValueError) as exc:
        raise CompanyError("ADN coverage status is invalid.") from exc
    company = _company(company_id)
    snapshot = AdnCoverageSnapshot.objects.create(
        company=company,
        source=source,
        status=normalized_status,
        policy_version=policy_version,
        evidence_reference=evidence_reference,
        verified_at=verified_at or timezone.now(),
    )
    AuditService().append(
        action="adn.coverage",
        entity_type="adn_coverage",
        entity_id=str(snapshot.id),
        result=normalized_status,
        actor_role="system",
        context={
            "company_id": str(company.id),
            "source": source,
            "status": normalized_status,
            "policy_version": policy_version,
            "evidence_reference": evidence_reference,
        },
    )
    return snapshot


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
