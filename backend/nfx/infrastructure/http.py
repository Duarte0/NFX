from __future__ import annotations

import contextvars
import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from logging import Logger
from typing import Any

from django.http import HttpRequest, HttpResponse

from nfx.infrastructure.redaction import redact

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")
_STRUCTURED_FIELDS = frozenset(
    {
        "attempt",
        "component",
        "duration_ms",
        "error_class",
        "event",
        "job_id",
        "job_type",
        "outcome",
        "process_id",
        "reason",
        "result",
        "status",
    }
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.msg
        args = redact(record.args)
        if args:
            message = message % args
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "process": os.getenv("NFX_PROCESS", "web"),
            "environment": os.getenv("NFX_PROFILE", "unknown"),
            "correlation_id": correlation_id.get(),
            "message": redact(message),
        }
        for field in _STRUCTURED_FIELDS:
            if field in record.__dict__:
                entry["job_ref" if field == "job_id" else field] = redact(
                    getattr(record, field)
                )
        return json.dumps(redact(entry), sort_keys=True)


def safe_log(logger: Logger, level: str, message: str, **fields: Any) -> None:
    """Emit bounded structured fields without making logging part of a state transition."""
    safe_fields = {key: fields[key] for key in fields if key in _STRUCTURED_FIELDS}
    try:
        getattr(logger, level)(message, extra=safe_fields)
    except Exception:
        # A broken handler, formatter, or sink must never turn durable work into
        # an application failure.
        return


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class CorrelationIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        value = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        token = correlation_id.set(value)
        try:
            response = self.get_response(request)
            response["X-Correlation-ID"] = value
            return response
        finally:
            correlation_id.reset(token)
