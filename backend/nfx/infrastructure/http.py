from __future__ import annotations

import contextvars
import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from django.http import HttpRequest, HttpResponse

from nfx.infrastructure.redaction import redact

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.msg
        args = redact(record.args)
        if args:
            message = message % args
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname.lower(),
                "process": os.getenv("NFX_PROCESS", "web"),
                "environment": os.getenv("NFX_PROFILE", "unknown"),
                "correlation_id": correlation_id.get(),
                "message": redact(message),
            }
        )


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
