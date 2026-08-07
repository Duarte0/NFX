"""Transactional contracts for durable jobs, leases, and safe handlers."""

from __future__ import annotations

import logging
import random
import re
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone

from nfx.jobs.handlers import HandlerOutcome, get_handler
from nfx.jobs.models import Job, JobOutcomeKind, JobPolicy, JobState
from nfx.jobs.policy import select_policy

logger = logging.getLogger(__name__)

_SAFE_KEY = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]{0,127}$")
_FORBIDDEN = re.compile(
    r"(?:pfx|pem|xml|pdf|token|credential|password|secret|private|content|binary|blob)", re.I
)
_SAFE_ERROR = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class JobEngineError(RuntimeError):
    """Base error for rejected job operations."""


class InvalidJobPayload(JobEngineError, ValueError):
    """Payload or result contains data outside the referential safe contract."""


class InvalidTransition(JobEngineError):
    """The job is not in a state that supports the requested operation."""


class LeaseLost(JobEngineError):
    """The caller no longer owns a valid lease."""


def _validate_safe_value(value: Any, *, path: str = "payload") -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if not _SAFE_KEY.fullmatch(name) or _FORBIDDEN.search(name):
                raise InvalidJobPayload(f"unsafe field at {path}")
            result[name] = _validate_safe_value(item, path=f"{path}.{name}")
        return result
    if isinstance(value, list):
        return [_validate_safe_value(item, path=f"{path}[]") for item in value]
    if value is None or isinstance(value, bool | int | float | str):
        if isinstance(value, str) and (value.lstrip().startswith("<") or value.startswith("%PDF")):
            raise InvalidJobPayload(f"unsafe value at {path}")
        return value
    raise InvalidJobPayload(f"unsupported value at {path}")


def _safe_error_code(value: str) -> str:
    return value if _SAFE_ERROR.fullmatch(value) else "handler_failed"


class JobEngine:
    """Owns all durable state transitions for background jobs."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = timezone.now,
        lease_duration: timedelta = timedelta(seconds=30),
        jitter_source: Callable[[int], int] | None = None,
    ) -> None:
        if lease_duration <= timedelta(0):
            raise ValueError("lease_duration must be positive")
        self.clock = clock
        self.lease_duration = lease_duration
        self.jitter_source = jitter_source or self._random_jitter

    @staticmethod
    def _random_jitter(max_seconds: int) -> int:
        return random.SystemRandom().randint(-max_seconds, max_seconds) if max_seconds else 0

    def enqueue(
        self,
        *,
        job_type: str,
        logical_target: str,
        payload: Mapping[str, Any],
        idempotency_key: str,
        priority: int = 0,
        scheduled_at: datetime | None = None,
        policy: JobPolicy | None = None,
        policy_source: str | None = None,
        policy_flow: str | None = None,
    ) -> Job:
        safe_payload = _validate_safe_value(payload)
        due_at = scheduled_at or self.clock()
        if timezone.is_naive(due_at):
            raise ValueError("scheduled_at must be timezone-aware")
        if not job_type or not logical_target or not idempotency_key:
            raise ValueError("job_type, logical_target, and idempotency_key are required")
        if policy is not None and (policy_source is not None or policy_flow is not None):
            raise ValueError("use policy or policy scope, not both")
        if (policy_source is None) != (policy_flow is None):
            raise ValueError("policy_source and policy_flow must be provided together")
        if policy_source is not None and policy_flow is not None:
            policy = select_policy(source=policy_source, flow=policy_flow, at=due_at)
        if policy is not None and not (
            policy.valid_from <= due_at
            and (policy.valid_until is None or due_at < policy.valid_until)
        ):
            raise ValueError("policy is not valid at the scheduled time")

        for _ in range(2):
            try:
                with transaction.atomic():
                    existing = (
                        Job.objects.select_for_update()
                        .filter(
                            idempotency_key=idempotency_key,
                            state__in=(JobState.QUEUED, JobState.RUNNING),
                        )
                        .first()
                    )
                    if existing is not None:
                        return existing
                    return Job.objects.create(
                        job_type=job_type,
                        logical_target=logical_target,
                        payload=safe_payload,
                        priority=priority,
                        idempotency_key=idempotency_key,
                        scheduled_at=due_at,
                        effective_policy=policy,
                    )
            except IntegrityError:
                # A concurrent insert won the partial unique constraint. The
                # next iteration observes it under a row lock.
                continue
        raise JobEngineError("could not resolve active idempotency key")

    def reclaim_expired(self) -> int:
        now = self.clock()
        with transaction.atomic():
            return Job.objects.filter(
                state=JobState.RUNNING,
                lease_expires_at__lte=now,
            ).update(
                state=JobState.QUEUED,
                scheduled_at=now,
                lease_owner=None,
                lease_issued_at=None,
                lease_expires_at=None,
                safe_error="lease_expired",
                updated_at=now,
            )

    def recover(self) -> tuple[int, int]:
        """Reclaim leases and report queued work due for a worker."""
        now = self.clock()
        with transaction.atomic():
            reclaimed = Job.objects.filter(
                state=JobState.RUNNING,
                lease_expires_at__lte=now,
            ).update(
                state=JobState.QUEUED,
                scheduled_at=now,
                lease_owner=None,
                lease_issued_at=None,
                lease_expires_at=None,
                safe_error="lease_expired",
                updated_at=now,
            )
            due = Job.objects.filter(state=JobState.QUEUED, scheduled_at__lte=now).count()
        return reclaimed, due

    def claim(self, owner: str) -> Job | None:
        if not owner or not owner.strip():
            raise ValueError("owner is required")
        now = self.clock()
        with transaction.atomic():
            Job.objects.filter(
                state=JobState.RUNNING,
                lease_expires_at__lte=now,
            ).update(
                state=JobState.QUEUED,
                scheduled_at=now,
                lease_owner=None,
                lease_issued_at=None,
                lease_expires_at=None,
                safe_error="lease_expired",
                updated_at=now,
            )
            job = (
                Job.objects.select_for_update(skip_locked=True)
                .filter(state=JobState.QUEUED, scheduled_at__lte=now)
                .order_by("-priority", "scheduled_at", "created_at")
                .first()
            )
            if job is None:
                return None
            job.state = JobState.RUNNING
            job.lease_owner = owner
            job.lease_issued_at = now
            job.lease_expires_at = now + self.lease_duration
            job.last_attempt_at = now
            job.attempt_count += 1
            job.updated_at = now
            job.save(
                update_fields=[
                    "state",
                    "lease_owner",
                    "lease_issued_at",
                    "lease_expires_at",
                    "last_attempt_at",
                    "attempt_count",
                    "updated_at",
                ]
            )
            return job

    def _lease_update(self, job_id: UUID | str, owner: str, **fields: Any) -> Job:
        now = self.clock()
        with transaction.atomic():
            updated = Job.objects.filter(
                id=job_id,
                state=JobState.RUNNING,
                lease_owner=owner,
                lease_expires_at__gt=now,
            ).update(**fields, updated_at=now)
            if not updated:
                if Job.objects.filter(id=job_id, state=JobState.RUNNING).exists():
                    raise LeaseLost("job lease is no longer valid")
                raise InvalidTransition("job is not running")
            return Job.objects.get(id=job_id)

    def renew(self, job_id: UUID | str, owner: str) -> Job:
        now = self.clock()
        return self._lease_update(
            job_id,
            owner,
            lease_expires_at=now + self.lease_duration,
        )

    def complete(
        self, job_id: UUID | str, owner: str, result: Mapping[str, Any] | None = None
    ) -> Job:
        safe_result = _validate_safe_value(result or {}, path="result")
        now = self.clock()
        return self._lease_update(
            job_id,
            owner,
            state=JobState.COMPLETED,
            lease_owner=None,
            lease_issued_at=None,
            lease_expires_at=None,
            safe_result=safe_result,
            safe_error="",
            completed_at=now,
            last_outcome=JobOutcomeKind.SUCCESS,
            cooldown_until=None,
            blocked_at=None,
            blocked_reason="",
        )

    def finalize(self, job_id: UUID | str, owner: str, outcome: HandlerOutcome) -> Job:
        """Apply a classified handler result while its lease is still valid."""
        if outcome.kind not in JobOutcomeKind.values:
            raise InvalidTransition("unknown handler outcome")
        safe_result = _validate_safe_value(outcome.result, path="result")
        error_code = _safe_error_code(outcome.error_code or outcome.kind)
        now = self.clock()
        with transaction.atomic():
            job = Job.objects.select_related("effective_policy").filter(id=job_id).first()
            if job is None or job.state != JobState.RUNNING:
                raise InvalidTransition("job is not running")
            if (
                job.lease_owner != owner
                or job.lease_expires_at is None
                or job.lease_expires_at <= now
            ):
                raise LeaseLost("job lease is no longer valid")
            fields: dict[str, Any] = {
                "safe_result": safe_result,
                "safe_error": error_code,
                "last_outcome": outcome.kind,
                "cooldown_until": None,
                "blocked_at": None,
                "blocked_reason": "",
                "lease_owner": None,
                "lease_issued_at": None,
                "lease_expires_at": None,
            }
            if outcome.kind == JobOutcomeKind.SUCCESS:
                fields.update(state=JobState.COMPLETED, completed_at=now)
            elif outcome.kind == JobOutcomeKind.PERMANENT:
                fields.update(
                    state=JobState.BLOCKED,
                    completed_at=None,
                    blocked_at=now,
                    blocked_reason=error_code,
                )
            else:
                policy = job.effective_policy
                if policy is None:
                    fields.update(
                        state=JobState.BLOCKED,
                        completed_at=None,
                        blocked_at=now,
                        blocked_reason="policy_required",
                        safe_error="policy_required",
                    )
                elif job.attempt_count > policy.retry_limit:
                    fields.update(
                        state=JobState.BLOCKED,
                        completed_at=None,
                        blocked_at=now,
                        blocked_reason="retry_exhausted",
                        safe_error="retry_exhausted",
                    )
                else:
                    due_at = now + self._retry_delay(job, policy)
                    if outcome.kind == JobOutcomeKind.COOLDOWN:
                        due_at = self._cooldown_due(outcome, policy, now)
                        fields["cooldown_until"] = due_at
                    fields.update(state=JobState.QUEUED, scheduled_at=due_at, completed_at=None)
            updated = Job.objects.filter(
                id=job_id,
                state=JobState.RUNNING,
                lease_owner=owner,
                lease_expires_at__gt=now,
            ).update(**fields, updated_at=now)
            if not updated:
                raise LeaseLost("job lease is no longer valid")
            return Job.objects.get(id=job_id)

    def _retry_delay(self, job: Job, policy: JobPolicy) -> timedelta:
        exponent = max(0, job.attempt_count - 1)
        base_seconds = min(
            policy.backoff_cap_seconds, policy.backoff_initial_seconds * (2**exponent)
        )
        jitter = self.jitter_source(policy.jitter_seconds)
        jitter = max(-policy.jitter_seconds, min(policy.jitter_seconds, jitter))
        return timedelta(seconds=min(policy.backoff_cap_seconds, max(0, base_seconds + jitter)))

    @staticmethod
    def _cooldown_due(outcome: HandlerOutcome, policy: JobPolicy, now: datetime) -> datetime:
        due_at = outcome.cooldown_until
        if due_at is None and policy.cooldown_seconds:
            due_at = now + timedelta(seconds=policy.cooldown_seconds)
        if due_at is None or timezone.is_naive(due_at) or due_at <= now:
            raise InvalidTransition("cooldown outcome requires a future timezone-aware deadline")
        return due_at

    def fail(
        self,
        job_id: UUID | str,
        owner: str,
        *,
        error_code: str = "handler_failed",
        scheduled_at: datetime | None = None,
    ) -> Job:
        due_at = scheduled_at or self.clock()
        if timezone.is_naive(due_at):
            raise ValueError("scheduled_at must be timezone-aware")
        return self._lease_update(
            job_id,
            owner,
            state=JobState.QUEUED,
            scheduled_at=due_at,
            lease_owner=None,
            lease_issued_at=None,
            lease_expires_at=None,
            safe_result=None,
            safe_error=_safe_error_code(error_code),
            completed_at=None,
            last_outcome=JobOutcomeKind.TEMPORARY,
            cooldown_until=None,
            blocked_at=None,
            blocked_reason="",
        )


def process_one(engine: JobEngine, *, owner: str) -> bool:
    """Run one registered handler, finalizing only through the lease contract."""
    try:
        job = engine.claim(owner)
    except OperationalError:
        logger.warning("job_database_unavailable")
        return False
    if job is None:
        return False
    handler = get_handler(job.job_type)
    if handler is None:
        try:
            if job.effective_policy is not None:
                engine.finalize(
                    job.id,
                    owner,
                    HandlerOutcome.temporary(error_code="handler_not_registered"),
                )
            else:
                engine.fail(job.id, owner, error_code="handler_not_registered")
        except LeaseLost:
            logger.warning("job_lease_lost", extra={"job_id": str(job.id)})
        return True
    try:
        result = handler(job)
        if isinstance(result, HandlerOutcome):
            engine.finalize(job.id, owner, result)
        else:
            engine.complete(job.id, owner, result)
    except LeaseLost:
        logger.warning("job_lease_lost", extra={"job_id": str(job.id)})
    except OperationalError:
        logger.warning("job_database_unavailable")
    except Exception:
        try:
            if job.effective_policy is not None:
                engine.finalize(
                    job.id,
                    owner,
                    HandlerOutcome.temporary(error_code="handler_failed"),
                )
            else:
                engine.fail(job.id, owner, error_code="handler_failed")
        except (LeaseLost, OperationalError):
            logger.warning("job_finalize_unavailable")
    return True


def run_worker_loop(
    engine: JobEngine,
    *,
    owner: str | None = None,
    poll_interval: float = 0.2,
    should_continue: Callable[[], bool] = lambda: True,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    worker_owner = owner or f"worker-{uuid4()}"
    while should_continue():
        process_one(engine, owner=worker_owner)
        if should_continue():
            sleep(poll_interval)


def run_scheduler_loop(
    engine: JobEngine,
    *,
    poll_interval: float = 0.2,
    should_continue: Callable[[], bool] = lambda: True,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    while should_continue():
        try:
            engine.recover()
        except OperationalError:
            logger.warning("scheduler_database_unavailable")
        if should_continue():
            sleep(poll_interval)
