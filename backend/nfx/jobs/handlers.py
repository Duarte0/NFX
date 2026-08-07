"""Explicit handler boundary used by the worker and synthetic tests."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nfx.jobs.models import Job, JobOutcomeKind


@dataclass(frozen=True)
class HandlerOutcome:
    """Safe, classified result returned by a registered handler."""

    kind: str
    result: Mapping[str, Any] = field(default_factory=dict)
    error_code: str = ""
    cooldown_until: datetime | None = None

    @classmethod
    def success(cls, result: Mapping[str, Any] | None = None) -> HandlerOutcome:
        return cls(JobOutcomeKind.SUCCESS, result or {})

    @classmethod
    def temporary(
        cls, *, error_code: str = "temporary_failure", result: Mapping[str, Any] | None = None
    ) -> HandlerOutcome:
        return cls(JobOutcomeKind.TEMPORARY, result or {}, error_code)

    @classmethod
    def cooldown(
        cls,
        *,
        cooldown_until: datetime | None = None,
        error_code: str = "official_cooldown",
        result: Mapping[str, Any] | None = None,
    ) -> HandlerOutcome:
        return cls(JobOutcomeKind.COOLDOWN, result or {}, error_code, cooldown_until)

    @classmethod
    def permanent(
        cls, *, error_code: str = "permanent_failure", result: Mapping[str, Any] | None = None
    ) -> HandlerOutcome:
        return cls(JobOutcomeKind.PERMANENT, result or {}, error_code)

    @classmethod
    def partial(
        cls, *, error_code: str = "partial_failure", result: Mapping[str, Any] | None = None
    ) -> HandlerOutcome:
        return cls(JobOutcomeKind.PARTIAL, result or {}, error_code)


JobOutcome = HandlerOutcome
JobHandler = Callable[[Job], HandlerOutcome | Mapping[str, Any] | None]
_HANDLERS: dict[str, JobHandler] = {}


def register_handler(job_type: str, handler: JobHandler) -> None:
    if not job_type or not job_type.strip():
        raise ValueError("job_type is required")
    _HANDLERS[job_type] = handler


def unregister_handler(job_type: str) -> None:
    _HANDLERS.pop(job_type, None)


def clear_handlers() -> None:
    _HANDLERS.clear()


def get_handler(job_type: str) -> JobHandler | None:
    return _HANDLERS.get(job_type)
