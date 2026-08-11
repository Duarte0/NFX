"""Server-authoritative collection commands and safe execution reconciliation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from nfx.audit.services import AuditService
from nfx.certificates.models import Certificate, CertificateState
from nfx.certificates.services import certificate_status
from nfx.collection.models import (
    ACTIVE_COLLECTION_STATES,
    CollectionExecution,
    CollectionExecutionState,
    CollectionOrigin,
    CollectionScope,
    IngestionOutcome,
    IngestionRecovery,
    InitialCollectionRequest,
    InitialCollectionRequestState,
)
from nfx.companies.models import Company, CompanyFlow, CompanyStatus, FlowFamily, FlowState
from nfx.identity.policy import Action, authorize
from nfx.identity.services import SessionIdentity
from nfx.jobs.handlers import HandlerOutcome, register_handler
from nfx.jobs.models import Job, JobOutcomeKind
from nfx.jobs.policy import PolicyNotFound, select_policy
from nfx.jobs.services import JobEngine


class CollectionError(ValueError):
    code = "collection_error"


class CollectionAccessDenied(CollectionError):
    code = "access_denied"


class InvalidCollectionScope(CollectionError):
    code = "invalid_scope"


class CollectionCompanyInactive(CollectionError):
    code = "company_inactive"


class CollectionFlowPaused(CollectionError):
    code = "flow_paused"


class CollectionCertificateUnavailable(CollectionError):
    code = "certificate_unavailable"


class CollectionPolicyUnavailable(CollectionError):
    code = "policy_unavailable"


class CollectionCooldown(CollectionError):
    code = "cooldown_active"


class CollectionBlocked(CollectionError):
    code = "collection_blocked"


class CollectionRetryNotEligible(CollectionError):
    code = "retry_not_eligible"


class CollectionExecutionQueryError(ValueError):
    """A filtered execution read is outside its bounded contract."""


COLLECTION_DASHBOARD_STATE_FILTERS: dict[str, str | None] = {
    "recent": None,
    "running": CollectionExecutionState.RUNNING,
    "failed": CollectionExecutionState.FAILED,
    "blocked": CollectionExecutionState.BLOCKED,
    "partial": CollectionExecutionState.PARTIAL,
}
COLLECTION_EXECUTION_QUERY_KEYS = frozenset(("from", "to", "state"))
MAX_COLLECTION_EXECUTION_QUERY_DAYS = 366
MAX_COLLECTION_EXECUTION_QUERY_ROWS = 50
_SAFE_EXECUTION_ERRORS = frozenset(
    {
        "official_cooldown",
        "partial_result",
        "permanent_failure",
        "retry_exhausted",
        "temporary_failure",
    }
)


@dataclass(frozen=True)
class CollectionExecutionFilter:
    start: date
    end: date
    state: str
    model_state: str | None

    @property
    def boundary(self) -> str:
        return "[from,to)"


@dataclass(frozen=True)
class CollectionRequest:
    executions: tuple[CollectionExecution, ...]
    duplicate: bool = False


def _now(value: datetime | None) -> datetime:
    result = value or timezone.now()
    if timezone.is_naive(result):
        raise ValueError("now must be timezone-aware")
    return result


def _scope(value: CollectionScope | str) -> CollectionScope:
    try:
        return value if isinstance(value, CollectionScope) else CollectionScope(value)
    except (TypeError, ValueError) as exc:
        raise InvalidCollectionScope("scope is invalid") from exc


def _query_value(query: Mapping[str, object], key: str) -> object | None:
    getlist = getattr(query, "getlist", None)
    values: list[object] = list(getlist(key)) if callable(getlist) else []
    if len(values) > 1:
        raise CollectionExecutionQueryError("query parameter is repeated")
    if values:
        return values[0]
    return query.get(key)


def _query_date(query: Mapping[str, object], key: str) -> date:
    value = _query_value(query, key)
    if not isinstance(value, str) or not value:
        raise CollectionExecutionQueryError("query date is required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CollectionExecutionQueryError("query date is invalid") from exc


def normalize_collection_execution_filter(
    query: Mapping[str, object],
) -> CollectionExecutionFilter:
    """Parse the dashboard's required civil-date and card-state read filter."""
    if set(query.keys()) - COLLECTION_EXECUTION_QUERY_KEYS:
        raise CollectionExecutionQueryError("unsupported query parameter")
    start = _query_date(query, "from")
    end = _query_date(query, "to")
    state = _query_value(query, "state")
    if not isinstance(state, str) or state not in COLLECTION_DASHBOARD_STATE_FILTERS:
        raise CollectionExecutionQueryError("execution state is invalid")
    duration = (end - start).days
    if duration < 1 or duration > MAX_COLLECTION_EXECUTION_QUERY_DAYS:
        raise CollectionExecutionQueryError("query period is outside the allowed range")
    return CollectionExecutionFilter(
        start=start,
        end=end,
        state=state,
        model_state=COLLECTION_DASHBOARD_STATE_FILTERS[state],
    )


def _collection_execution_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    zone = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(start, datetime.min.time()), timezone=zone),
        timezone.make_aware(datetime.combine(end, datetime.min.time()), timezone=zone),
    )


def collection_execution_queryset(
    start: date, end: date, *, state: str | None = None
) -> QuerySet[CollectionExecution]:
    """Return the canonical, half-open execution query used by dashboard and drill-down."""
    if state is not None and state not in COLLECTION_DASHBOARD_STATE_FILTERS:
        raise CollectionExecutionQueryError("execution state is invalid")
    start_at, end_at = _collection_execution_bounds(start, end)
    queryset = CollectionExecution.objects.filter(created_at__gte=start_at, created_at__lt=end_at)
    model_state = COLLECTION_DASHBOARD_STATE_FILTERS.get(state) if state is not None else None
    if model_state is not None:
        queryset = queryset.filter(state=model_state)
    return queryset


def _safe_execution_error(value: str) -> str:
    return value if value in _SAFE_EXECUTION_ERRORS else ""


def collection_execution_summary(execution: CollectionExecution) -> dict[str, object]:
    """Serialize only bounded collection metadata for a read-only drill-down."""
    return {
        "id": str(execution.id),
        "company_id": str(execution.company_id),
        "company_name": execution.company.legal_name,
        "family": execution.family,
        "requested_scope": execution.requested_scope,
        "state": execution.state,
        "outcome": execution.outcome,
        "recovery": execution.recovery,
        "safe_error": _safe_execution_error(execution.safe_error),
        "created_at": execution.created_at.isoformat(),
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
    }


def list_collection_execution_summaries(
    selected: CollectionExecutionFilter,
) -> dict[str, object]:
    queryset = collection_execution_queryset(
        selected.start,
        selected.end,
        state=selected.state,
    ).select_related("company")
    rows = list(
        queryset.order_by("-created_at", "-id")[: MAX_COLLECTION_EXECUTION_QUERY_ROWS + 1]
    )
    filter_payload = {
        "from": selected.start.isoformat(),
        "to": selected.end.isoformat(),
        "state": selected.state,
    }
    return {
        "read_only": True,
        "filter": filter_payload,
        "boundary": selected.boundary,
        "total": queryset.count(),
        "limit": MAX_COLLECTION_EXECUTION_QUERY_ROWS,
        "truncated": len(rows) > MAX_COLLECTION_EXECUTION_QUERY_ROWS,
        "executions": [
            collection_execution_summary(row)
            for row in rows[:MAX_COLLECTION_EXECUTION_QUERY_ROWS]
        ],
    }


def _families(scope: CollectionScope) -> tuple[str, ...]:
    if scope == CollectionScope.COMPLETE:
        return (FlowFamily.NFE, FlowFamily.NFSE)
    return (scope.value,)


def _require_actor(origin: CollectionOrigin, actor: SessionIdentity | None) -> None:
    if origin == CollectionOrigin.AUTOMATIC:
        if actor is not None:
            raise CollectionAccessDenied("automatic commands have no actor")
        return
    if actor is None or not authorize(
        actor.role, Action.CONTROL_COLLECTIONS, actor_id=actor.user_id
    ):
        raise CollectionAccessDenied("collection control access required")


def _audit(
    *,
    result: str,
    company_id: UUID | str,
    family: str = "",
    actor: SessionIdentity | None,
    ip_address: str,
    origin: CollectionOrigin | str,
    reason: str = "",
    correlation_id: str = "",
    entity_id: str = "",
) -> None:
    AuditService().append(
        action="collection.request",
        entity_type="collection_execution",
        entity_id=entity_id or str(company_id),
        result=result,
        actor_id=actor.user_id if actor else None,
        actor_role=actor.role if actor else "system",
        ip_address=ip_address,
        reason=reason,
        correlation_id=correlation_id,
        context={"company_id": str(company_id), "family": family, "origin": str(origin)},
    )


def _current_certificate(company: Company, now: datetime) -> Certificate:
    certificate = (
        Certificate.objects.filter(company=company, state=CertificateState.CURRENT)
        .order_by("-activated_at")
        .first()
    )
    if certificate is None or certificate_status(certificate, now=now) not in {
        "valido",
        "proximo_vencimento",
    }:
        raise CollectionCertificateUnavailable("certificate_unavailable")
    return certificate


def _active_execution(flow: CompanyFlow) -> CollectionExecution | None:
    if flow.active_execution_id is None:
        return None
    execution = CollectionExecution.objects.filter(
        id=flow.active_execution_id, state__in=ACTIVE_COLLECTION_STATES
    ).first()
    if execution is None:
        flow.active_execution_id = None
        flow.save(update_fields=["active_execution", "updated_at"])
    return execution


def request_collection(
    *,
    company_id: UUID | str,
    scope: CollectionScope | str,
    origin: CollectionOrigin | str,
    actor: SessionIdentity | None,
    ip_address: str,
    now: datetime | None = None,
    retry_execution_id: UUID | str | None = None,
) -> CollectionRequest:
    selected_scope = _scope(scope)
    selected_origin = (
        origin if isinstance(origin, CollectionOrigin) else CollectionOrigin(origin)
    )
    _require_actor(selected_origin, actor)
    current = _now(now)
    company_key = str(company_id)
    families = _families(selected_scope)
    correlation = f"collection:{uuid4()}"
    try:
        with transaction.atomic():
            company = (
                Company.objects.select_for_update()
                .filter(id=company_id)
                .first()
            )
            if company is None:
                raise CollectionCompanyInactive("company_not_found")
            if company.status != CompanyStatus.ACTIVE:
                raise CollectionCompanyInactive("company_inactive")
            _current_certificate(company, current)
            flows = {
                flow.family: flow
                for flow in CompanyFlow.objects.select_for_update()
                .filter(company=company, family__in=families)
                .order_by("family")
            }
            if len(flows) != len(families):
                raise CollectionFlowPaused("flow_unavailable")

            existing: list[CollectionExecution] = []
            for family in families:
                active = _active_execution(flows[family])
                if active is not None:
                    existing.append(active)
            if existing:
                _audit(
                    result="duplicate",
                    company_id=company.id,
                    family=",".join(families),
                    actor=actor,
                    ip_address=ip_address,
                    origin=selected_origin,
                    reason="active_execution",
                    correlation_id=correlation,
                )
                return CollectionRequest(tuple(existing), duplicate=True)

            policies = {}
            for family in families:
                flow = flows[family]
                if flow.state != FlowState.ENABLED:
                    raise CollectionFlowPaused("flow_paused")
                if flow.collection_state == CollectionExecutionState.BLOCKED:
                    raise CollectionBlocked(flow.blocked_reason or "collection_blocked")
                if flow.cooldown_until is not None and flow.cooldown_until > current:
                    raise CollectionCooldown("cooldown_active")
                try:
                    policies[family] = select_policy(source="synthetic", flow=family, at=current)
                except PolicyNotFound as exc:
                    raise CollectionPolicyUnavailable("policy_unavailable") from exc

            retry_of: CollectionExecution | None = None
            if selected_origin == CollectionOrigin.RETRY:
                if retry_execution_id is None:
                    raise CollectionRetryNotEligible("retry_reference_required")
                retry_of = (
                    CollectionExecution.objects.select_for_update()
                    .filter(id=retry_execution_id, company=company)
                    .first()
                )
                if retry_of is None or retry_of.family not in families or retry_of.state not in {
                    CollectionExecutionState.FAILED,
                    CollectionExecutionState.PARTIAL,
                }:
                    raise CollectionRetryNotEligible("retry_not_eligible")

            created: list[CollectionExecution] = []
            for family in families:
                flow = flows[family]
                execution = CollectionExecution.objects.create(
                    company=company,
                    family=family,
                    requested_scope=selected_scope,
                    origin=selected_origin,
                    requester_id=actor.user_id if actor else None,
                    retry_of=retry_of if retry_of and retry_of.family == family else None,
                    effective_policy=policies[family],
                    state=CollectionExecutionState.QUEUED,
                    correlation_id=correlation,
                )
                job = JobEngine(clock=lambda: current).enqueue(
                    job_type="collection.synthetic",
                    logical_target=f"company:{company.id}:flow:{family}",
                    payload={
                        "execution_id": str(execution.id),
                        "company_id": str(company.id),
                        "family": family,
                        "scope": selected_scope.value,
                        "origin": selected_origin.value,
                        "outcome": "valid_empty",
                    },
                    idempotency_key=f"collection:{execution.id}",
                    scheduled_at=current,
                    policy=policies[family],
                )
                execution.job = job
                execution.save(update_fields=["job", "updated_at"])
                flow.active_execution = execution
                flow.collection_state = CollectionExecutionState.QUEUED
                flow.last_attempt_at = current
                flow.next_scheduled_at = current
                flow.cooldown_until = None
                flow.safe_error = ""
                flow.blocked_reason = ""
                flow.save(
                    update_fields=[
                        "active_execution",
                        "collection_state",
                        "last_attempt_at",
                        "next_scheduled_at",
                        "cooldown_until",
                        "safe_error",
                        "blocked_reason",
                        "updated_at",
                    ]
                )
                created.append(execution)
            _audit(
                result="retry" if selected_origin == CollectionOrigin.RETRY else "requested",
                company_id=company.id,
                family=",".join(families),
                actor=actor,
                ip_address=ip_address,
                origin=selected_origin,
                correlation_id=correlation,
                entity_id=str(created[0].id),
            )
            return CollectionRequest(tuple(created))
    except CollectionError as exc:
        _audit(
            result="rejected",
            company_id=company_key,
            family=",".join(families),
            actor=actor,
            ip_address=ip_address,
            origin=selected_origin,
            reason=exc.code,
            correlation_id=correlation,
        )
        raise
    except IntegrityError as exc:
        _audit(
            result="rejected",
            company_id=company_key,
            family=",".join(families),
            actor=actor,
            ip_address=ip_address,
            origin=selected_origin,
            reason="concurrent_request",
            correlation_id=correlation,
        )
        raise CollectionError("concurrent_request") from exc


def _safe_summary(result: Mapping[str, Any]) -> dict[str, bool | int | str]:
    allowed = {
        "query_valid",
        "unit_count",
        "coverage",
        "next_cursor",
        "next_nsu",
        "ingestion_outcome",
        "ingestion_recovery",
        "ingestion_reason",
    }
    summary: dict[str, bool | int | str] = {}
    for key in allowed:
        value = result.get(key)
        if isinstance(value, bool | int | str):
            summary[key] = value
    return summary


def reconcile_collection_job(
    job: Job, outcome: str, result: Mapping[str, Any] | None = None, *, now: datetime | None = None
) -> CollectionExecution:
    current = _now(now)
    summary = _safe_summary(result or {})
    with transaction.atomic():
        execution = CollectionExecution.objects.select_for_update().get(job=job)
        flow = CompanyFlow.objects.select_for_update().get(
            company=execution.company, family=execution.family
        )
        if execution.state in {
            CollectionExecutionState.CONCLUDED,
            CollectionExecutionState.EMPTY,
            CollectionExecutionState.BLOCKED,
            CollectionExecutionState.FAILED,
        }:
            return execution
        execution.safe_summary = summary
        execution.safe_error = ""
        raw_ingestion_outcome = summary.get("ingestion_outcome")
        raw_ingestion_recovery = summary.get("ingestion_recovery")
        try:
            execution.outcome = IngestionOutcome(str(raw_ingestion_outcome))
        except (TypeError, ValueError):
            execution.outcome = (
                IngestionOutcome.VALID_EMPTY
                if outcome == JobOutcomeKind.SUCCESS and summary.get("unit_count", 0) == 0
                else IngestionOutcome.SUCCESS
                if outcome == JobOutcomeKind.SUCCESS
                else IngestionOutcome.PARTIAL
                if outcome == JobOutcomeKind.PARTIAL
                else IngestionOutcome.COOLDOWN
                if outcome == JobOutcomeKind.COOLDOWN
                else IngestionOutcome.PERMANENT_FAILURE
                if outcome == JobOutcomeKind.PERMANENT
                else IngestionOutcome.TEMPORARY_FAILURE
            )
        try:
            execution.recovery = IngestionRecovery(str(raw_ingestion_recovery))
        except (TypeError, ValueError):
            execution.recovery = (
                IngestionRecovery.COOLDOWN
                if outcome == JobOutcomeKind.COOLDOWN
                else IngestionRecovery.BLOCKED
                if outcome == JobOutcomeKind.PERMANENT
                else IngestionRecovery.RETRY
                if outcome in {JobOutcomeKind.PARTIAL, JobOutcomeKind.TEMPORARY}
                else IngestionRecovery.NONE
            )
        execution.started_at = execution.started_at or current
        flow.last_attempt_at = flow.last_attempt_at or current
        terminal = False
        exhausted = bool(
            execution.effective_policy
            and job.attempt_count > execution.effective_policy.retry_limit
        )
        if outcome == JobOutcomeKind.SUCCESS:
            state = (
                CollectionExecutionState.EMPTY
                if summary.get("query_valid") is True and summary.get("unit_count", 0) == 0
                else CollectionExecutionState.CONCLUDED
            )
            execution.state = state
            execution.finished_at = current
            flow.last_success_at = current
            flow.next_scheduled_at = None
            flow.cooldown_until = None
            flow.safe_error = ""
            flow.blocked_reason = ""
            terminal = True
        elif outcome == JobOutcomeKind.COOLDOWN and exhausted:
            execution.state = CollectionExecutionState.BLOCKED
            execution.safe_error = "retry_exhausted"
            execution.finished_at = current
            flow.collection_state = CollectionExecutionState.BLOCKED
            flow.blocked_reason = execution.safe_error
            flow.safe_error = execution.safe_error
            flow.active_execution = None
            terminal = True
        elif outcome == JobOutcomeKind.COOLDOWN:
            execution.state = CollectionExecutionState.COOLDOWN
            execution.safe_error = "official_cooldown"
            flow.collection_state = CollectionExecutionState.COOLDOWN
            flow.safe_error = execution.safe_error
            flow.cooldown_until = current + timedelta(hours=1)
            flow.next_scheduled_at = flow.cooldown_until
        elif outcome == JobOutcomeKind.PERMANENT:
            execution.state = CollectionExecutionState.BLOCKED
            execution.safe_error = "permanent_failure"
            execution.finished_at = current
            flow.collection_state = CollectionExecutionState.BLOCKED
            flow.blocked_reason = execution.safe_error
            flow.safe_error = execution.safe_error
            flow.active_execution = None
            terminal = True
        elif outcome == JobOutcomeKind.PARTIAL and exhausted:
            execution.state = CollectionExecutionState.BLOCKED
            execution.safe_error = "retry_exhausted"
            execution.finished_at = current
            flow.collection_state = CollectionExecutionState.BLOCKED
            flow.blocked_reason = execution.safe_error
            flow.safe_error = execution.safe_error
            flow.active_execution = None
            terminal = True
        elif outcome == JobOutcomeKind.PARTIAL:
            execution.state = CollectionExecutionState.PARTIAL
            execution.safe_error = "partial_result"
            flow.collection_state = CollectionExecutionState.PARTIAL
            flow.safe_error = execution.safe_error
        elif exhausted:
            execution.state = CollectionExecutionState.BLOCKED
            execution.safe_error = "retry_exhausted"
            execution.finished_at = current
            flow.collection_state = CollectionExecutionState.BLOCKED
            flow.blocked_reason = execution.safe_error
            flow.safe_error = execution.safe_error
            flow.active_execution = None
            terminal = True
        else:
            execution.state = CollectionExecutionState.RETRYING
            execution.safe_error = "temporary_failure"
            flow.collection_state = CollectionExecutionState.RETRYING
            flow.safe_error = execution.safe_error
        if not terminal:
            flow.collection_state = execution.state
        else:
            flow.collection_state = execution.state
            flow.active_execution = None
        execution.save(
            update_fields=[
                "state",
                "outcome",
                "recovery",
                "safe_summary",
                "safe_error",
                "started_at",
                "finished_at",
                "updated_at",
            ]
        )
        flow.save(
            update_fields=[
                "collection_state",
                "last_attempt_at",
                "last_success_at",
                "next_scheduled_at",
                "cooldown_until",
                "blocked_reason",
                "safe_error",
                "active_execution",
                "updated_at",
            ]
        )
        return execution


def collection_handler(job: Job) -> HandlerOutcome:
    execution = CollectionExecution.objects.select_related("effective_policy").get(job=job)
    if execution.state in {
        CollectionExecutionState.CONCLUDED,
        CollectionExecutionState.EMPTY,
        CollectionExecutionState.BLOCKED,
        CollectionExecutionState.FAILED,
    }:
        return HandlerOutcome.success(execution.safe_summary)
    outcome = str(job.payload.get("outcome", "valid_empty"))
    if outcome == "blocked":
        classified = HandlerOutcome.permanent(error_code="permanent_failure")
    elif outcome == "cooldown":
        classified = HandlerOutcome.cooldown(
            cooldown_until=timezone.now() + timedelta(hours=1), error_code="official_cooldown"
        )
    elif outcome in {"temporary", "failed"}:
        classified = HandlerOutcome.temporary(error_code="temporary_failure")
    elif outcome == "partial":
        classified = HandlerOutcome.partial(error_code="partial_result", result={"unit_count": 1})
    else:
        classified = HandlerOutcome.success(
            {"query_valid": True, "unit_count": 0, "coverage": "available"}
        )
    reconcile_collection_job(job, classified.kind, classified.result)
    return classified


def ensure_collection_handler() -> None:
    register_handler("collection.synthetic", collection_handler)


def process_initial_collection_requests(*, now: datetime | None = None) -> int:
    current = _now(now)
    processed = 0
    for handoff in InitialCollectionRequest.objects.filter(
        state=InitialCollectionRequestState.QUEUED
    ).order_by("created_at")[:100]:
        try:
            result = request_collection(
                company_id=handoff.company_id,
                scope=CollectionScope.COMPLETE,
                origin=CollectionOrigin.AUTOMATIC,
                actor=None,
                ip_address="",
                now=current,
            )
        except (CollectionPolicyUnavailable, CollectionCooldown, CollectionFlowPaused):
            continue
        except CollectionError as exc:
            InitialCollectionRequest.objects.filter(id=handoff.id).update(
                state=InitialCollectionRequestState.BLOCKED,
                safe_error=exc.code,
                processed_at=current,
            )
            continue
        InitialCollectionRequest.objects.filter(id=handoff.id).update(
            state=InitialCollectionRequestState.CONSUMED,
            safe_error="",
            processed_at=current,
        )
        processed += 1 if not result.duplicate else 0
    return processed
