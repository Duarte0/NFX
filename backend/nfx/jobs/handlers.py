"""Explicit handler boundary used by the worker and synthetic tests."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from nfx.jobs.models import Job

JobHandler = Callable[[Job], Mapping[str, Any] | None]
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
