from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path

import pytest
from nfx.adapters.fiscal import EmptyFiscalSimulator, FiscalDestinationError, FiscalDestinationGuard
from nfx.infrastructure.configuration import ConfigurationError, load_settings
from nfx.infrastructure.http import JsonFormatter
from nfx.infrastructure.redaction import REDACTED, redact

CANARY = "synthetic-secret-canary"


def environment(**overrides: str) -> dict[str, str]:
    values = {
        "NFX_PROFILE": "test",
        "NFX_SECRET_KEY": CANARY,
        "NFX_CERTIFICATE_MASTER_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        "NFX_FISCAL_TRANSPORT": "simulator",
        "NFX_FISCAL_DESTINATION": "simulator://empty",
        "DATABASE_URL": "postgresql://user:password@database.test:5432/nfx_test",
        "MINIO_ROOT_PASSWORD": "synthetic-minio-secret",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize("profile", ["test", "development"])
def test_local_profiles_default_to_the_empty_simulator(profile: str) -> None:
    values = environment(NFX_PROFILE=profile)
    values.pop("NFX_FISCAL_TRANSPORT")
    values.pop("NFX_FISCAL_DESTINATION")
    settings = load_settings(values)
    assert settings.public.fiscal_destination == "simulator://empty"
    assert EmptyFiscalSimulator().collect() == ()


@pytest.mark.parametrize("profile", ["homologation", "runtime"])
def test_non_local_profiles_require_explicit_allowlisted_simulator(profile: str) -> None:
    settings = load_settings(
        environment(
            NFX_PROFILE=profile,
            NFX_FISCAL_ALLOWLIST="simulator://empty",
        )
    )
    assert settings.public.profile == profile


@pytest.mark.parametrize(
    "overrides",
    [
        {"NFX_PROFILE": "unknown"},
        {"NFX_SECRET_KEY": ""},
        {"NFX_SECRET_KEY": "CHANGE_ME"},
        {"NFX_FISCAL_DESTINATION": "http://example.test"},
        {"NFX_UNRECOGNIZED": "value"},
        {"NFX_PROFILE": "runtime"},
        {"NFX_FISCAL_DESTINATION": "https://user:pass@example.test"},
    ],
)
def test_invalid_configuration_fails_without_disclosing_values(overrides: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(environment(**overrides))
    assert CANARY not in str(exc_info.value)
    assert "value" not in str(exc_info.value)


def test_secret_can_be_loaded_from_a_mounted_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "django-key"
    secret_file.write_text(CANARY, encoding="utf-8")
    settings = load_settings(environment(NFX_SECRET_KEY="", NFX_SECRET_KEY_FILE=str(secret_file)))
    assert settings.secrets.django_secret_key == CANARY


def test_certificate_master_key_requires_external_base64url_32_byte_material() -> None:
    settings = load_settings(environment())
    assert settings.secrets.certificate_master_key == b"\x00" * 32
    with pytest.raises(ConfigurationError):
        load_settings(environment(NFX_CERTIFICATE_MASTER_KEY="too-short"))


def test_redaction_handles_nested_values_exceptions_urls_and_binary_payloads() -> None:
    payload = {
        "password": CANARY,
        "nested": [{"Authorization": f"Bearer {CANARY}"}],
        "url": f"https://example.test/callback?token={CANARY}",
        "xml": "<?xml version='1.0'?><secret>" + CANARY + "</secret>",
        "pdf": b"%PDF-1.7 synthetic",
        "error": RuntimeError(CANARY),
    }
    snapshot = json.dumps(redact(payload), sort_keys=True, default=str)
    assert CANARY not in snapshot
    assert REDACTED in snapshot


def test_logging_snapshot_redacts_nested_secret_canary() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("nfx-test-redaction")
    logger.handlers = [handler]
    logger.propagate = False
    logger.warning("fiscal payload=%s", {"token": CANARY})
    assert CANARY not in stream.getvalue()


def test_prohibited_destination_and_redirect_make_zero_network_calls() -> None:
    calls: list[str] = []
    guard = FiscalDestinationGuard(load_settings(environment()).public)

    with pytest.raises(FiscalDestinationError):
        guard.send("https://sefaz.example.test/", calls.append)
    with pytest.raises(FiscalDestinationError):
        guard.send("simulator://empty", calls.append, redirects=("https://adn.example.test/",))

    assert calls == []


@pytest.mark.parametrize(
    "destination", ["SIMULATOR://EMPTY", "simulator://empty:443", "simulator://empty/path"]
)
def test_equivalent_or_changed_simulator_urls_are_rejected(destination: str) -> None:
    guard = FiscalDestinationGuard(load_settings(environment()).public)
    with pytest.raises(FiscalDestinationError):
        guard.validate(destination)


def test_empty_allowlist_is_not_valid_for_runtime() -> None:
    with pytest.raises(ConfigurationError):
        load_settings(environment(NFX_PROFILE="runtime", NFX_FISCAL_ALLOWLIST=""))


def test_runtime_requires_an_explicit_transport_and_destination() -> None:
    values = environment(NFX_PROFILE="runtime", NFX_FISCAL_ALLOWLIST="simulator://empty")
    values.pop("NFX_FISCAL_TRANSPORT")
    with pytest.raises(ConfigurationError):
        load_settings(values)
