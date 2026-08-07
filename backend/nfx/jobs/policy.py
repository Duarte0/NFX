"""Validated selection and creation of versioned job policies."""

from __future__ import annotations

import re
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone

from nfx.jobs.models import JobPolicy

_SCOPE = re.compile(r"^(?:\*|[a-z][a-z0-9_.:-]{0,63})$")


class PolicyError(RuntimeError):
    """Base error for policy selection and validation."""


class InvalidPolicy(PolicyError, ValueError):
    """A policy is malformed or cannot safely be persisted."""


class PolicyNotFound(PolicyError):
    """No valid policy covers the requested source and flow."""


class AmbiguousPolicy(PolicyError):
    """More than one policy has the same effective scope and validity."""


def _validate_policy_values(
    *,
    source_scope: str,
    flow_scope: str,
    version: int,
    valid_from: datetime,
    valid_until: datetime | None,
    retry_limit: int,
    backoff_initial_seconds: int,
    backoff_cap_seconds: int,
    jitter_seconds: int,
    cooldown_seconds: int,
) -> None:
    if not _SCOPE.fullmatch(source_scope) or not _SCOPE.fullmatch(flow_scope):
        raise InvalidPolicy("source and flow scopes must be safe identifiers or *")
    if version < 1:
        raise InvalidPolicy("policy version must be positive")
    if timezone.is_naive(valid_from) or (
        valid_until is not None and timezone.is_naive(valid_until)
    ):
        raise InvalidPolicy("policy validity must be timezone-aware")
    if valid_until is not None and valid_until <= valid_from:
        raise InvalidPolicy("policy validity interval is empty")
    if retry_limit < 0 or backoff_initial_seconds < 1 or backoff_cap_seconds < 1:
        raise InvalidPolicy("policy timing values are invalid")
    if backoff_cap_seconds < backoff_initial_seconds:
        raise InvalidPolicy("backoff cap must not be below the initial delay")
    if jitter_seconds < 0 or cooldown_seconds < 0:
        raise InvalidPolicy("policy timing values are invalid")


def create_policy(
    *,
    source_scope: str,
    flow_scope: str,
    version: int,
    valid_from: datetime,
    valid_until: datetime | None = None,
    retry_limit: int = 3,
    backoff_initial_seconds: int = 1,
    backoff_cap_seconds: int = 3600,
    jitter_seconds: int = 0,
    cooldown_seconds: int = 0,
) -> JobPolicy:
    _validate_policy_values(
        source_scope=source_scope,
        flow_scope=flow_scope,
        version=version,
        valid_from=valid_from,
        valid_until=valid_until,
        retry_limit=retry_limit,
        backoff_initial_seconds=backoff_initial_seconds,
        backoff_cap_seconds=backoff_cap_seconds,
        jitter_seconds=jitter_seconds,
        cooldown_seconds=cooldown_seconds,
    )
    policy = JobPolicy(
        source_scope=source_scope,
        flow_scope=flow_scope,
        version=version,
        valid_from=valid_from,
        valid_until=valid_until,
        retry_limit=retry_limit,
        backoff_initial_seconds=backoff_initial_seconds,
        backoff_cap_seconds=backoff_cap_seconds,
        jitter_seconds=jitter_seconds,
        cooldown_seconds=cooldown_seconds,
    )
    try:
        policy.full_clean(validate_unique=True)
        policy.save(force_insert=True)
    except (IntegrityError, ValidationError) as exc:
        raise InvalidPolicy("policy validation failed") from exc
    return policy


def select_policy(*, source: str, flow: str, at: datetime) -> JobPolicy:
    if not _SCOPE.fullmatch(source) or not _SCOPE.fullmatch(flow):
        raise InvalidPolicy("source and flow must be safe identifiers")
    if timezone.is_naive(at):
        raise InvalidPolicy("policy selection time must be timezone-aware")
    candidates = list(
        JobPolicy.objects.filter(
            source_scope__in=(source, "*"),
            flow_scope__in=(flow, "*"),
            valid_from__lte=at,
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=at))
    )
    if not candidates:
        raise PolicyNotFound(f"no policy for {source}/{flow}")
    specificity = max(
        (int(policy.source_scope == source) + int(policy.flow_scope == flow))
        for policy in candidates
    )
    matches = [
        policy
        for policy in candidates
        if int(policy.source_scope == source) + int(policy.flow_scope == flow) == specificity
    ]
    if len(matches) != 1:
        raise AmbiguousPolicy(f"multiple policies for {source}/{flow}")
    return matches[0]
