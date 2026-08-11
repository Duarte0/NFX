"""Read-only, capability-aware dashboard aggregation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone

from nfx.certificates.models import Certificate, CertificateState
from nfx.collection.models import CollectionExecution, CollectionExecutionState
from nfx.companies.models import Company, CompanyStatus
from nfx.documents.models import Document, DocumentFamily
from nfx.documents.rendering import RenderUnavailable, renderer_metadata
from nfx.identity.models import Role
from nfx.infrastructure.configuration import load_settings
from nfx.infrastructure.dependencies import dependencies_from_environment
from nfx.jobs.models import Job, JobOutcomeKind, JobState
from nfx.jobs.observability import (
    ComponentHealth,
    HeartbeatService,
    JobMetricsSnapshot,
    JobObservability,
    OperationalHealth,
)

MAX_PERIOD_DAYS = 366
_ALLOWED_PERIOD_KEYS = frozenset(("from", "to"))
_CERTIFICATE_WARNING_DAYS = 30


class InvalidDashboardParams(ValueError):
    """A dashboard query is outside the bounded read contract."""


@dataclass(frozen=True)
class DatePeriod:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days


@dataclass(frozen=True)
class DashboardPeriod:
    current: DatePeriod
    previous: DatePeriod


def _rendering_capability() -> dict[str, str]:
    try:
        metadata = renderer_metadata()
    except RenderUnavailable:
        return {"status": "unavailable", "reason": "renderer_unavailable"}
    return {
        "status": "available",
        "reason": f"{metadata.renderer_id}:{metadata.version}",
    }


def _single(query: Mapping[str, object], key: str) -> object | None:
    getlist = getattr(query, "getlist", None)
    values: list[object] = list(getlist(key)) if callable(getlist) else []
    if len(values) > 1:
        raise InvalidDashboardParams("period parameter is repeated")
    if values:
        return values[0]
    return query.get(key)


def _parse_date(value: object | None) -> date | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise InvalidDashboardParams("period date is invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidDashboardParams("period date is invalid") from exc


def normalize_period(query: Mapping[str, object], *, today: date | None = None) -> DashboardPeriod:
    """Normalize an inclusive/exclusive civil-date interval and its predecessor."""
    if set(query.keys()) - _ALLOWED_PERIOD_KEYS:
        raise InvalidDashboardParams("unsupported period parameter")
    current_day = today or timezone.localdate()
    requested_start = _parse_date(_single(query, "from"))
    requested_end = _parse_date(_single(query, "to"))
    if requested_start is None and requested_end is None:
        start = current_day.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
    elif requested_start is None or requested_end is None:
        raise InvalidDashboardParams("both period bounds are required")
    else:
        start, end = requested_start, requested_end
    assert start is not None and end is not None
    duration = (end - start).days
    if duration < 1 or duration > MAX_PERIOD_DAYS:
        raise InvalidDashboardParams("period is outside the allowed range")
    return DashboardPeriod(
        current=DatePeriod(start, end),
        previous=DatePeriod(start - timedelta(days=duration), start),
    )


def _local_bounds(period: DatePeriod) -> tuple[datetime, datetime]:
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(period.start, datetime.min.time()), timezone=zone)
    end = timezone.make_aware(datetime.combine(period.end, datetime.min.time()), timezone=zone)
    return start, end


def _signal(
    value: int | None, evaluated_at: datetime, *, nonzero_status: str = "ready"
) -> dict[str, object]:
    if value is None:
        return {
            "value": None,
            "status": "unavailable",
            "freshness": {"status": "unknown", "evaluated_at": None, "age_seconds": None},
        }
    return {
        "value": value,
        "status": "zero" if value == 0 else nonzero_status,
        "freshness": {
            "status": "fresh",
            "evaluated_at": evaluated_at.isoformat(),
            "age_seconds": 0,
        },
    }


def _card_status(current: dict[str, object], previous: dict[str, object] | None) -> str:
    if current["status"] == "unavailable":
        return "unavailable"
    if previous is not None and previous["status"] == "unavailable":
        return "degraded"
    return str(current["status"])


def _period_card(
    *,
    card_id: str,
    label: str,
    current: int | None,
    previous: int | None,
    evaluated_at: datetime,
    href: str | None,
    filters: dict[str, str] | None = None,
    nonzero_status: str = "ready",
) -> dict[str, object]:
    current_signal = _signal(current, evaluated_at, nonzero_status=nonzero_status)
    previous_signal = _signal(previous, evaluated_at, nonzero_status=nonzero_status)
    return {
        "id": card_id,
        "label": label,
        "kind": "period",
        "current": current_signal,
        "previous": previous_signal,
        "status": _card_status(current_signal, previous_signal),
        "freshness": current_signal["freshness"],
        "drilldown": {"href": href, "filters": filters or {}} if href else None,
    }


def _snapshot_card(
    *,
    card_id: str,
    label: str,
    value: int | None,
    evaluated_at: datetime,
    href: str | None,
    filters: dict[str, str] | None = None,
) -> dict[str, object]:
    current = _signal(value, evaluated_at)
    return {
        "id": card_id,
        "label": label,
        "kind": "snapshot",
        "current": current,
        "previous": None,
        "status": current["status"],
        "freshness": current["freshness"],
        "drilldown": {"href": href, "filters": filters or {}} if href else None,
    }


def _safe_source(
    source: Callable[[], dict[str, int]], *, evaluated_at: datetime
) -> tuple[dict[str, int] | None, dict[str, object]]:
    try:
        return source(), {"status": "fresh", "evaluated_at": evaluated_at.isoformat()}
    except Exception:
        # A bounded safe code is returned; database/provider details stay server-side.
        return None, {"status": "unavailable", "evaluated_at": None, "error": "source_unavailable"}


def _period_documents(period: DatePeriod) -> QuerySet[Document]:
    start, end = _local_bounds(period)
    return Document.objects.filter(emitted_at__gte=start, emitted_at__lt=end)


def _document_counts(period: DatePeriod) -> dict[str, int]:
    documents = _period_documents(period)
    return {
        "total": documents.count(),
        "nfe": documents.filter(family=DocumentFamily.NFE).count(),
        "nfse": documents.filter(family=DocumentFamily.NFSE).count(),
        "entrada": documents.filter(family=DocumentFamily.NFE, role="entrada").count(),
        "saida": documents.filter(family=DocumentFamily.NFE, role="saida").count(),
        "tomados": documents.filter(family=DocumentFamily.NFSE, category="tomada").count(),
        "prestados": documents.filter(family=DocumentFamily.NFSE, category="prestada").count(),
    }


def _collection_counts(period: DatePeriod) -> dict[str, int]:
    start, end = _local_bounds(period)
    executions = CollectionExecution.objects.filter(created_at__gte=start, created_at__lt=end)
    return {
        "recent": executions.count(),
        "completed": executions.filter(
            state__in=(CollectionExecutionState.CONCLUDED, CollectionExecutionState.EMPTY)
        ).count(),
        "running": executions.filter(state=CollectionExecutionState.RUNNING).count(),
        "failed": executions.filter(state=CollectionExecutionState.FAILED).count(),
        "blocked": executions.filter(state=CollectionExecutionState.BLOCKED).count(),
        "partial": executions.filter(state=CollectionExecutionState.PARTIAL).count(),
    }


def _job_counts(period: DatePeriod) -> dict[str, int]:
    start, end = _local_bounds(period)
    jobs = Job.objects.filter(created_at__gte=start, created_at__lt=end)
    return {
        "recent": jobs.count(),
        "pending": jobs.filter(state__in=(JobState.QUEUED, JobState.RUNNING)).count(),
        "completed": jobs.filter(state=JobState.COMPLETED).count(),
        "blocked": jobs.filter(state=JobState.BLOCKED).count(),
        "failed": jobs.filter(
            last_outcome__in=(
                JobOutcomeKind.TEMPORARY,
                JobOutcomeKind.PERMANENT,
                JobOutcomeKind.PARTIAL,
            )
        ).count(),
    }


def _company_counts() -> dict[str, int]:
    return {
        "active": Company.objects.filter(status=CompanyStatus.ACTIVE).count(),
        "inactive": Company.objects.filter(
            status__in=(CompanyStatus.DEACTIVATED, CompanyStatus.REGISTERED)
        ).count(),
    }


def _certificate_counts(now: datetime) -> dict[str, int]:
    current = Certificate.objects.filter(state=CertificateState.CURRENT)
    warning = now + timedelta(days=_CERTIFICATE_WARNING_DAYS)
    return {
        "current": current.count(),
        "expired": current.filter(not_after__lt=now).count(),
        "expiring": current.filter(not_after__gte=now, not_after__lte=warning).count(),
    }


def _health_payload(now: datetime) -> dict[str, object]:
    settings = load_settings()
    dependencies = dependencies_from_environment().check()
    metrics: JobMetricsSnapshot | None = None
    components: dict[str, ComponentHealth] | None = None
    if not {"postgres", "schema"}.intersection(dependencies.unavailable):
        metrics = JobObservability().snapshot()
        components = HeartbeatService.inspect(
            now=now,
            timeouts={
                "worker": timedelta(seconds=settings.operational.worker_heartbeat_timeout_seconds),
                "scheduler": timedelta(
                    seconds=settings.operational.scheduler_heartbeat_timeout_seconds
                ),
            },
        )
    health = OperationalHealth(
        worker_timeout=timedelta(seconds=settings.operational.worker_heartbeat_timeout_seconds),
        scheduler_timeout=timedelta(
            seconds=settings.operational.scheduler_heartbeat_timeout_seconds
        ),
        backlog_delay=timedelta(seconds=settings.operational.job_backlog_delay_seconds),
    )
    return health.evaluate(dependencies, metrics, components, now=now)


def build_dashboard(
    *, period: DashboardPeriod, role: str, now: datetime | None = None
) -> dict[str, object]:
    evaluated_at = now or timezone.now()
    cards: list[dict[str, object]] = []

    company_counts, _ = _safe_source(_company_counts, evaluated_at=evaluated_at)
    if company_counts is not None:
        cards.extend(
            (
                _snapshot_card(
                    card_id="companies.active",
                    label="Empresas ativas",
                    value=company_counts["active"],
                    evaluated_at=evaluated_at,
                    href="#coletas",
                ),
                _snapshot_card(
                    card_id="companies.inactive",
                    label="Empresas inativas",
                    value=company_counts["inactive"],
                    evaluated_at=evaluated_at,
                    href="#coletas",
                ),
            )
        )
    else:
        cards.extend(
            _snapshot_card(
                card_id=card_id,
                label=label,
                value=None,
                evaluated_at=evaluated_at,
                href="#coletas",
            )
            for card_id, label in (
                ("companies.active", "Empresas ativas"),
                ("companies.inactive", "Empresas inativas"),
            )
        )

    document_current, _ = _safe_source(
        lambda: _document_counts(period.current), evaluated_at=evaluated_at
    )
    document_previous, _ = _safe_source(
        lambda: _document_counts(period.previous), evaluated_at=evaluated_at
    )
    document_cards: list[tuple[str, str, str, dict[str, str]]] = [
        ("total", "Documentos no período", "#documentos", {}),
        ("nfe", "NF-e", "?family=nfe#documentos", {"family": "nfe"}),
        ("nfse", "NFS-e", "?family=nfse#documentos", {"family": "nfse"}),
        (
            "entrada",
            "NF-e de entrada",
            "?family=nfe&direction=entrada#documentos",
            {"family": "nfe", "direction": "entrada"},
        ),
        (
            "saida",
            "NF-e de saída",
            "?family=nfe&direction=saida#documentos",
            {"family": "nfe", "direction": "saida"},
        ),
        (
            "tomados",
            "NFS-e tomadas",
            "?family=nfse&nfse_category=tomado#documentos",
            {"family": "nfse", "nfse_category": "tomado"},
        ),
        (
            "prestados",
            "NFS-e prestadas",
            "?family=nfse&nfse_category=prestado#documentos",
            {"family": "nfse", "nfse_category": "prestado"},
        ),
    ]
    cards.extend(
        _period_card(
            card_id=f"documents.{key}",
            label=label,
            current=document_current.get(key) if document_current else None,
            previous=document_previous.get(key) if document_previous else None,
            evaluated_at=evaluated_at,
            href=href,
            filters=filters,
        )
        for key, label, href, filters in document_cards
    )

    collection_current, _ = _safe_source(
        lambda: _collection_counts(period.current), evaluated_at=evaluated_at
    )
    collection_previous, _ = _safe_source(
        lambda: _collection_counts(period.previous), evaluated_at=evaluated_at
    )
    for key, label, status in (
        ("recent", "Coletas recentes", "ready"),
        ("running", "Coletas em execução", "ready"),
        ("failed", "Coletas com falha", "degraded"),
        ("blocked", "Coletas bloqueadas", "degraded"),
        ("partial", "Coletas parciais", "partial"),
    ):
        cards.append(
            _period_card(
                card_id=f"collections.{key}",
                label=label,
                current=collection_current.get(key) if collection_current else None,
                previous=collection_previous.get(key) if collection_previous else None,
                evaluated_at=evaluated_at,
                href="#coletas",
                nonzero_status=status,
            )
        )

    job_current, _ = _safe_source(lambda: _job_counts(period.current), evaluated_at=evaluated_at)
    job_previous, _ = _safe_source(lambda: _job_counts(period.previous), evaluated_at=evaluated_at)
    for key, label, status in (
        ("pending", "Processamento pendente", "ready"),
        ("failed", "Processamento com falha", "degraded"),
        ("blocked", "Processamento bloqueado", "degraded"),
    ):
        cards.append(
            _period_card(
                card_id=f"jobs.{key}",
                label=label,
                current=job_current.get(key) if job_current else None,
                previous=job_previous.get(key) if job_previous else None,
                evaluated_at=evaluated_at,
                href="#coletas",
                nonzero_status=status,
            )
        )

    capabilities: dict[str, object] = {
        "fiscal_sources": {"status": "unavailable", "reason": "not_implemented"},
        "documents": {"status": "available", "reason": "persisted_document_contract"},
        "rendering": _rendering_capability(),
        "disk": {"status": "unavailable", "reason": "p9_operational_slice_pending"},
        "backup": {"status": "unavailable", "reason": "p9_backup_slice_pending"},
        "certificates": {"status": "available" if role != Role.VIEWER else "admin_only"},
        "operational_health": {
            "status": "available" if role == Role.ADMINISTRATOR else "admin_only"
        },
    }
    if role != Role.VIEWER:
        certificate_counts, _ = _safe_source(
            lambda: _certificate_counts(evaluated_at), evaluated_at=evaluated_at
        )
        for key, label in (
            ("current", "Certificados atuais"),
            ("expired", "Certificados vencidos"),
            ("expiring", "Certificados próximos do vencimento"),
        ):
            cards.append(
                _snapshot_card(
                    card_id=f"certificates.{key}",
                    label=label,
                    value=certificate_counts.get(key) if certificate_counts else None,
                    evaluated_at=evaluated_at,
                    href="#empresas",
                )
            )

    result: dict[str, Any] = {
        "read_only": True,
        "evaluated_at": evaluated_at.isoformat(),
        "period": {
            "current": {
                "from": period.current.start.isoformat(),
                "to": period.current.end.isoformat(),
            },
            "previous": {
                "from": period.previous.start.isoformat(),
                "to": period.previous.end.isoformat(),
            },
            "boundary": "[from,to)",
        },
        "cards": cards,
        "capabilities": capabilities,
    }
    if role == Role.ADMINISTRATOR:
        try:
            result["operational_health"] = _health_payload(evaluated_at)
        except Exception:
            result["operational_health"] = {
                "status": "unavailable",
                "read_only": True,
                "reason": "health_unavailable",
            }
    return result
