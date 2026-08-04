"""One redaction boundary for logs, audit payloads and error rendering."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(r"(?:password|secret|pfx|key|token|cookie|authorization|xml|pdf)", re.I)
_SENSITIVE_QUERY = re.compile(r"(?:password|secret|token|key|cookie|authorization)", re.I)


def _redact_string(value: str) -> str:
    if (
        value.startswith("%PDF")
        or value.lstrip().startswith("<?xml")
        or value.lstrip().startswith("<")
    ):
        return REDACTED
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value
    if parsed.username or parsed.password:
        return REDACTED
    query = parse_qsl(parsed.query, keep_blank_values=True)
    if any(_SENSITIVE_QUERY.search(key) for key, _ in query):
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, REDACTED, ""))
    return value


def redact(value: Any) -> Any:
    if isinstance(value, BaseException):
        # Exception arguments are arbitrary external data. Preserve only their
        # safe class; callers must not turn exception text into an output channel.
        return {"error_class": type(value).__name__}
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _SENSITIVE_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, set):
        return {redact(item) for item in value}
    if isinstance(value, bytes):
        return REDACTED
    if isinstance(value, str):
        return _redact_string(value)
    return value
