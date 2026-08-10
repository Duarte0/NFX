"""Validated, fail-closed process configuration.

Only this module reads deployment configuration.  It deliberately has no Django
dependency so web, worker and scheduler validate the same contract before doing
any work.
"""

from __future__ import annotations

import base64
import binascii
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class ConfigurationError(RuntimeError):
    """A safe configuration error: its message never contains supplied values."""


PROFILES = frozenset({"test", "development", "homologation", "runtime"})
LOCAL_TRANSPORTS = frozenset({"simulator", "memory", "local"})
KNOWN_NFX_KEYS = frozenset(
    {
        "NFX_PROFILE",
        "NFX_PROCESS",
        "NFX_ALLOWED_HOSTS",
        "NFX_SECRET_KEY",
        "NFX_SECRET_KEY_FILE",
        "NFX_CERTIFICATE_MASTER_KEY",
        "NFX_CERTIFICATE_MASTER_KEY_FILE",
        "NFX_FISCAL_TRANSPORT",
        "NFX_FISCAL_DESTINATION",
        "NFX_FISCAL_ALLOWLIST",
        "NFX_WORKER_HEARTBEAT_TIMEOUT_SECONDS",
        "NFX_SCHEDULER_HEARTBEAT_TIMEOUT_SECONDS",
        "NFX_JOB_BACKLOG_DELAY_SECONDS",
        "NFX_BACKUP_ROOT",
    }
)


@dataclass(frozen=True)
class PublicSettings:
    profile: str
    process: str
    fiscal_transport: str
    fiscal_destination: str
    fiscal_allowlist: tuple[str, ...]
    allowed_hosts: tuple[str, ...]


@dataclass(frozen=True)
class SecretSettings:
    django_secret_key: str
    database_url: str
    minio_secret_key: str
    certificate_master_key: bytes


@dataclass(frozen=True)
class OperationalSettings:
    worker_heartbeat_timeout_seconds: int
    scheduler_heartbeat_timeout_seconds: int
    job_backlog_delay_seconds: int
    backup_root: str


@dataclass(frozen=True)
class Settings:
    public: PublicSettings
    secrets: SecretSettings
    operational: OperationalSettings


def _error(field: str) -> ConfigurationError:
    return ConfigurationError(f"Invalid configuration: {field}")


def _read_secret(environ: Mapping[str, str], name: str, file_name: str | None = None) -> str:
    value = environ.get(name)
    if file_name is None:
        return _validate_secret(value, name)
    source = environ.get(file_name)
    if value and source:
        raise _error(f"{name} source")
    if source:
        try:
            value = Path(source).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise _error(file_name) from exc
    return _validate_secret(value, name)


def _validate_secret(value: str | None, name: str) -> str:
    if not value or "CHANGE_ME" in value:
        raise _error(name)
    return value


def _read_certificate_master_key(
    environ: Mapping[str, str],
) -> bytes:
    encoded = _read_secret(
        environ,
        "NFX_CERTIFICATE_MASTER_KEY",
        "NFX_CERTIFICATE_MASTER_KEY_FILE",
    )
    try:
        key = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (UnicodeEncodeError, ValueError, binascii.Error) as exc:
        raise _error("NFX_CERTIFICATE_MASTER_KEY") from exc
    if len(key) != 32:
        raise _error("NFX_CERTIFICATE_MASTER_KEY")
    return key


def _validate_database_url(value: str | None) -> str:
    value = _validate_secret(value, "DATABASE_URL")
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as exc:
        raise _error("DATABASE_URL") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path:
        raise _error("DATABASE_URL")
    if port is not None and not 1 <= port <= 65535:
        raise _error("DATABASE_URL")
    return value


def _duration_seconds(values: Mapping[str, str], name: str, default: int) -> int:
    raw = values.get(name, str(default))
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise _error(name) from exc
    if not 1 <= parsed <= 86400:
        raise _error(name)
    return parsed


def _backup_root(values: Mapping[str, str]) -> str:
    value = values.get("NFX_BACKUP_ROOT", "/var/backups/nfx")
    path = Path(value)
    if not path.is_absolute() or path == Path("/") or ".." in path.parts:
        raise _error("NFX_BACKUP_ROOT")
    return str(path)


def _validate_destination(value: str, field: str) -> str:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as exc:
        raise _error(field) from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise _error(field)
    if parsed.scheme == "simulator" and parsed.netloc == "empty" and not parsed.path:
        return "simulator://empty"
    if parsed.scheme != "https" or not parsed.hostname or port not in {None, 443}:
        raise _error(field)
    return f"https://{parsed.hostname.lower()}{parsed.path or '/'}"


def _allowed_hosts(values: Mapping[str, str]) -> tuple[str, ...]:
    raw = values.get("NFX_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
    hosts = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    if not hosts:
        raise _error("NFX_ALLOWED_HOSTS")
    for host in hosts:
        if host == "*" or "/" in host or "://" in host or any(char.isspace() for char in host):
            raise _error("NFX_ALLOWED_HOSTS")
        if host.startswith(".") or host.endswith("."):
            raise _error("NFX_ALLOWED_HOSTS")
    return hosts


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if environ is None else environ
    unknown = sorted(key for key in values if key.startswith("NFX_") and key not in KNOWN_NFX_KEYS)
    if unknown:
        raise _error("unknown NFX setting")

    profile = values.get("NFX_PROFILE")
    if profile not in PROFILES:
        raise _error("NFX_PROFILE")
    process = values.get("NFX_PROCESS", "web")
    if process not in {"web", "worker", "scheduler"}:
        raise _error("NFX_PROCESS")

    transport = values.get("NFX_FISCAL_TRANSPORT", "simulator")
    destination = _validate_destination(
        values.get("NFX_FISCAL_DESTINATION", "simulator://empty"),
        "NFX_FISCAL_DESTINATION",
    )
    raw_allowlist = values.get("NFX_FISCAL_ALLOWLIST", "")
    allowlist = tuple(
        _validate_destination(item.strip(), "NFX_FISCAL_ALLOWLIST")
        for item in raw_allowlist.split(",")
        if item.strip()
    )
    if raw_allowlist and not allowlist:
        raise _error("NFX_FISCAL_ALLOWLIST")

    if profile in {"test", "development"}:
        if transport not in LOCAL_TRANSPORTS or destination != "simulator://empty":
            raise _error("fiscal transport for local profile")
        allowlist = ("simulator://empty",)
    elif (
        "NFX_FISCAL_TRANSPORT" not in values
        or "NFX_FISCAL_DESTINATION" not in values
        or transport != "simulator"
        or not raw_allowlist
        or destination not in allowlist
    ):
        # No production-capable transport exists in P0. Explicit settings can only
        # select the empty simulator and must still name the approved destination.
        raise _error("explicit fiscal transport and allowlist")

    return Settings(
        public=PublicSettings(
            profile,
            process,
            transport,
            destination,
            allowlist,
            _allowed_hosts(values),
        ),
        secrets=SecretSettings(
            django_secret_key=_read_secret(values, "NFX_SECRET_KEY", "NFX_SECRET_KEY_FILE"),
            database_url=_validate_database_url(values.get("DATABASE_URL")),
            minio_secret_key=_validate_secret(
                values.get("MINIO_ROOT_PASSWORD"), "MINIO_ROOT_PASSWORD"
            ),
            certificate_master_key=_read_certificate_master_key(values),
        ),
        operational=OperationalSettings(
            worker_heartbeat_timeout_seconds=_duration_seconds(
                values, "NFX_WORKER_HEARTBEAT_TIMEOUT_SECONDS", 30
            ),
            scheduler_heartbeat_timeout_seconds=_duration_seconds(
                values, "NFX_SCHEDULER_HEARTBEAT_TIMEOUT_SECONDS", 30
            ),
            job_backlog_delay_seconds=_duration_seconds(
                values, "NFX_JOB_BACKLOG_DELAY_SECONDS", 300
            ),
            backup_root=_backup_root(values),
        ),
    )
