"""Read-only job signals and durable process freshness evidence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from nfx.infrastructure.dependencies import DependencyCheck
from nfx.jobs.models import Job, JobOutcomeKind, JobState, ProcessHeartbeat

COMPONENTS = ("worker", "scheduler")
_SAFE_OUTCOMES = tuple(JobOutcomeKind.values)
_SAFE_STATES = tuple(JobState.values)
JOB_DASHBOARD_FILTERS = {
    "pending": Q(state__in=(JobState.QUEUED, JobState.RUNNING)),
    "failed": Q(
        last_outcome__in=(
            JobOutcomeKind.TEMPORARY,
            JobOutcomeKind.PERMANENT,
            JobOutcomeKind.PARTIAL,
        )
    ),
    "blocked": Q(state=JobState.BLOCKED),
}
JOB_OBSERVABILITY_QUERY_KEYS = frozenset(("from", "to", "filter"))
MAX_JOB_OBSERVABILITY_QUERY_DAYS = 366
MAX_JOB_OBSERVABILITY_QUERY_ROWS = 50
_SAFE_JOB_ERRORS = frozenset(
    {
        "artifact_unavailable",
        "authorization_blocked",
        "authorization_revoked",
        "certificate_invalid",
        "deletion_failed",
        "handler_failed",
        "handler_not_registered",
        "invalid_export_reference",
        "invalid_operation",
        "lease_expired",
        "operation_missing",
        "official_cooldown",
        "partial_result",
        "permanent_failure",
        "policy_required",
        "recovery_required",
        "render_audit_unavailable",
        "render_reference_invalid",
        "render_reference_missing",
        "renderer_failed",
        "retry_exhausted",
        "temporary_failure",
    }
)


class InvalidJobObservabilityQuery(ValueError):
    """A filtered job read is outside its bounded contract."""


@dataclass(frozen=True)
class JobObservabilityFilter:
    start: date
    end: date
    filter_name: str

    @property
    def boundary(self) -> str:
        return "[from,to)"


def _query_value(query: Mapping[str, object], key: str) -> object | None:
    getlist = getattr(query, "getlist", None)
    values: list[object] = list(getlist(key)) if callable(getlist) else []
    if len(values) > 1:
        raise InvalidJobObservabilityQuery("query parameter is repeated")
    if values:
        return values[0]
    return query.get(key)


def _query_date(query: Mapping[str, object], key: str) -> date:
    value = _query_value(query, key)
    if not isinstance(value, str) or not value:
        raise InvalidJobObservabilityQuery("query date is required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidJobObservabilityQuery("query date is invalid") from exc


def normalize_job_observability_query(
    query: Mapping[str, object],
) -> JobObservabilityFilter:
    """Parse the dashboard's required civil-date and job-card filter."""
    if set(query.keys()) - JOB_OBSERVABILITY_QUERY_KEYS:
        raise InvalidJobObservabilityQuery("unsupported query parameter")
    start = _query_date(query, "from")
    end = _query_date(query, "to")
    filter_name = _query_value(query, "filter")
    if not isinstance(filter_name, str) or filter_name not in JOB_DASHBOARD_FILTERS:
        raise InvalidJobObservabilityQuery("job filter is invalid")
    duration = (end - start).days
    if duration < 1 or duration > MAX_JOB_OBSERVABILITY_QUERY_DAYS:
        raise InvalidJobObservabilityQuery("query period is outside the allowed range")
    return JobObservabilityFilter(start=start, end=end, filter_name=filter_name)


def job_created_at_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """Return the dashboard's Brasília/civil-date half-open bounds."""
    zone = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(start, datetime.min.time()), timezone=zone),
        timezone.make_aware(datetime.combine(end, datetime.min.time()), timezone=zone),
    )


def job_observability_queryset(
    start: date, end: date, *, filter_name: str | None = None
) -> QuerySet[Job]:
    """Return the canonical job selection shared by cards and drill-downs."""
    if filter_name is not None and filter_name not in JOB_DASHBOARD_FILTERS:
        raise InvalidJobObservabilityQuery("job filter is invalid")
    start_at, end_at = job_created_at_bounds(start, end)
    queryset = Job.objects.filter(created_at__gte=start_at, created_at__lt=end_at)
    if filter_name is not None:
        queryset = queryset.filter(JOB_DASHBOARD_FILTERS[filter_name])
    return queryset


def _safe_job_error(value: object) -> str:
    return value if isinstance(value, str) and value in _SAFE_JOB_ERRORS else ""


def job_observability_summary(job: Job) -> dict[str, object]:
    """Serialize only bounded job metadata; never expose payload or lease details."""
    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "state": job.state if job.state in _SAFE_STATES else "",
        "outcome": job.last_outcome if job.last_outcome in _SAFE_OUTCOMES else None,
        "created_at": job.created_at.isoformat(),
        "scheduled_at": job.scheduled_at.isoformat(),
        "last_attempt_at": job.last_attempt_at.isoformat() if job.last_attempt_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "attempt_count": job.attempt_count,
        "safe_error": _safe_job_error(job.safe_error),
    }


def list_job_observability_summaries(
    selected: JobObservabilityFilter,
) -> dict[str, object]:
    queryset = job_observability_queryset(
        selected.start,
        selected.end,
        filter_name=selected.filter_name,
    )
    rows = list(queryset.order_by("-created_at", "-id")[: MAX_JOB_OBSERVABILITY_QUERY_ROWS + 1])
    return {
        "read_only": True,
        "filter": {
            "from": selected.start.isoformat(),
            "to": selected.end.isoformat(),
            "filter": selected.filter_name,
        },
        "boundary": selected.boundary,
        "total": queryset.count(),
        "limit": MAX_JOB_OBSERVABILITY_QUERY_ROWS,
        "truncated": len(rows) > MAX_JOB_OBSERVABILITY_QUERY_ROWS,
        "jobs": [job_observability_summary(row) for row in rows[:MAX_JOB_OBSERVABILITY_QUERY_ROWS]],
    }


@dataclass(frozen=True)
class JobMetricsSnapshot:
    queue_counts: Mapping[str, int]
    oldest_due_age_seconds: float | None
    claim_candidates: int
    retrying: int
    expired_lease_recoveries: int
    cooldowns: int
    blocked: int
    outcomes: Mapping[str, int]

    def as_dict(self) -> dict[str, object]:
        return {
            "queue_counts": dict(self.queue_counts),
            "oldest_due_age_seconds": self.oldest_due_age_seconds,
            "claim_candidates": self.claim_candidates,
            "retrying": self.retrying,
            "expired_lease_recoveries": self.expired_lease_recoveries,
            "cooldowns": self.cooldowns,
            "blocked": self.blocked,
            "outcomes": dict(self.outcomes),
        }


class JobObservability:
    """Compute bounded aggregates without mutating jobs or leases."""

    def __init__(self, *, clock: Callable[[], datetime] = timezone.now) -> None:
        self.clock = clock

    def snapshot(self) -> JobMetricsSnapshot:
        now = self.clock()
        state_counts = {state: 0 for state in _SAFE_STATES}
        for row in Job.objects.values("state").annotate(total=Count("id")):
            state = row["state"]
            if state in state_counts:
                state_counts[state] = int(row["total"])

        oldest = (
            Job.objects.filter(state=JobState.QUEUED, scheduled_at__lte=now)
            .order_by("scheduled_at")
            .values_list("scheduled_at", flat=True)
            .first()
        )
        age = max(0.0, (now - oldest).total_seconds()) if oldest is not None else None
        retrying = Job.objects.filter(state=JobState.QUEUED, attempt_count__gt=0).count()
        expired = Job.objects.filter(
            Q(state=JobState.QUEUED, safe_error="lease_expired")
            | Q(state=JobState.RUNNING, lease_expires_at__lte=now)
        ).count()
        cooldowns = Job.objects.filter(
            state=JobState.QUEUED, cooldown_until__gt=now
        ).count()
        outcome_counts = {outcome: 0 for outcome in _SAFE_OUTCOMES}
        for row in (
            Job.objects.exclude(last_outcome="")
            .values("last_outcome")
            .annotate(total=Count("id"))
        ):
            outcome = row["last_outcome"]
            if outcome in outcome_counts:
                outcome_counts[outcome] = int(row["total"])

        return JobMetricsSnapshot(
            queue_counts=state_counts,
            oldest_due_age_seconds=age,
            claim_candidates=state_counts[JobState.QUEUED],
            retrying=retrying,
            expired_lease_recoveries=expired,
            cooldowns=cooldowns,
            blocked=state_counts[JobState.BLOCKED],
            outcomes=outcome_counts,
        )


@dataclass(frozen=True)
class ComponentHealth:
    status: str
    process_id: str | None
    last_seen_at: datetime | None
    age_seconds: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "process_id": self.process_id,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "age_seconds": self.age_seconds,
        }


class HeartbeatService:
    """Write only this process's identity and read the freshest component evidence."""

    def __init__(
        self,
        *,
        component: str,
        process_id: str,
        clock: Callable[[], datetime] = timezone.now,
    ) -> None:
        if component not in COMPONENTS or not process_id or not process_id.strip():
            raise ValueError("invalid heartbeat identity")
        self.component = component
        self.process_id = process_id
        self.clock = clock
        self.started_at = clock()

    def beat(self) -> None:
        now = self.clock()
        for attempt in range(2):
            try:
                with transaction.atomic():
                    row = (
                        ProcessHeartbeat.objects.select_for_update()
                        .filter(component=self.component, process_id=self.process_id)
                        .first()
                    )
                    if row is None:
                        ProcessHeartbeat.objects.create(
                            component=self.component,
                            process_id=self.process_id,
                            started_at=self.started_at,
                            last_seen_at=now,
                            status="running",
                        )
                    else:
                        ProcessHeartbeat.objects.filter(id=row.id).update(
                            last_seen_at=now, status="running"
                        )
                return
            except IntegrityError:
                if attempt == 1:
                    raise

    def stop(self) -> None:
        """Mark this process as stopped without touching another process's row."""
        ProcessHeartbeat.objects.filter(
            component=self.component, process_id=self.process_id
        ).update(status="stopping", last_seen_at=self.clock())

    @staticmethod
    def inspect(
        *,
        now: datetime,
        timeout: timedelta | None = None,
        timeouts: Mapping[str, timedelta] | None = None,
        components: tuple[str, ...] = COMPONENTS,
    ) -> dict[str, ComponentHealth]:
        rows = ProcessHeartbeat.objects.filter(component__in=components).order_by(
            "component", "-last_seen_at"
        )
        latest: dict[str, ProcessHeartbeat] = {}
        for heartbeat in rows:
            latest.setdefault(heartbeat.component, heartbeat)
        result: dict[str, ComponentHealth] = {}
        for component in components:
            current = latest.get(component)
            if current is None:
                result[component] = ComponentHealth("missing", None, None, None)
                continue
            age = max(0.0, (now - current.last_seen_at).total_seconds())
            component_timeout = (timeouts or {}).get(component, timeout)
            if component_timeout is None:
                raise ValueError("a heartbeat timeout is required")
            result[component] = ComponentHealth(
                "ready"
                if current.status == "running" and age <= component_timeout.total_seconds()
                else "stale"
                if current.status == "running"
                else "stopped",
                current.process_id,
                current.last_seen_at,
                age,
            )
        return result


class OperationalHealth:
    """Evaluate dependency, process freshness, and overdue durable backlog."""

    def __init__(
        self,
        *,
        worker_timeout: timedelta = timedelta(seconds=30),
        scheduler_timeout: timedelta = timedelta(seconds=30),
        backlog_delay: timedelta = timedelta(minutes=5),
    ) -> None:
        if min(worker_timeout, scheduler_timeout, backlog_delay) <= timedelta(0):
            raise ValueError("operational thresholds must be positive")
        self.worker_timeout = worker_timeout
        self.scheduler_timeout = scheduler_timeout
        self.backlog_delay = backlog_delay

    def evaluate(
        self,
        dependencies: DependencyCheck,
        metrics: JobMetricsSnapshot | None,
        components: Mapping[str, ComponentHealth] | None,
        *,
        now: datetime,
    ) -> dict[str, object]:
        unavailable = set(dependencies.unavailable)
        dependency_state = {
            name: "unavailable" if name in unavailable else "ready"
            for name in ("postgres", "schema", "minio")
        }
        durable_unavailable = bool(unavailable & {"postgres", "schema"}) or metrics is None

        if metrics is None:
            jobs: dict[str, object] = {"status": "unavailable"}
            backlog: dict[str, object] = {"status": "unavailable"}
        else:
            jobs = metrics.as_dict()
            jobs["status"] = "ready"
            delayed = (
                metrics.oldest_due_age_seconds is not None
                and metrics.oldest_due_age_seconds > self.backlog_delay.total_seconds()
            )
            backlog = {
                "status": "delayed" if delayed else "ready",
                "oldest_due_age_seconds": metrics.oldest_due_age_seconds,
            }

        process_state: dict[str, dict[str, object]] = {}
        if components is None or durable_unavailable:
            process_state = {
                component: ComponentHealth("unavailable", None, None, None).as_dict()
                for component in COMPONENTS
            }
        else:
            process_state = {
                component: components.get(
                    component, ComponentHealth("missing", None, None, None)
                ).as_dict()
                for component in COMPONENTS
            }

        degraded = (
            bool(unavailable)
            or jobs.get("status") != "ready"
            or backlog.get("status") != "ready"
            or any(item["status"] != "ready" for item in process_state.values())
        )
        status = "unavailable" if durable_unavailable else "degraded" if degraded else "ready"
        return {
            "status": status,
            "read_only": True,
            "dependencies": dependency_state,
            "processes": process_state,
            "jobs": jobs,
            "backlog": backlog,
            "capabilities": {
                "fiscal_sources": "unavailable",
                "disk": "unavailable",
                "backup": "unavailable",
                "documents": "unavailable",
                "quarantine": "unavailable",
                "rendering": "available",
            },
            "evaluated_at": now.isoformat(),
        }
