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
TEMPLATE_PATH = Path(__file__).parents[2] / ".env.example"


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


def template_assignments() -> dict[str, list[str]]:
    assignments: dict[str, list[str]] = {}
    for line in TEMPLATE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        assignments.setdefault(name, []).append(value)
    return assignments


def test_environment_template_uses_external_secret_placeholders_once() -> None:
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    assignments = template_assignments()

    assert all(len(values) == 1 for values in assignments.values())
    assert assignments["NFX_SECRET_KEY"][0].startswith("CHANGE_ME_")
    assert assignments["NFX_CERTIFICATE_MASTER_KEY"][0].startswith("CHANGE_ME_")
    assert "NFX_SECRET_KEY_FILE" in text
    assert "NFX_CERTIFICATE_MASTER_KEY_FILE" in text
    assert "nunca preencha ambos" in text
    assert "base64url" in text

    assert assignments["NFX_PROFILE"] == ["development"]
    assert assignments["NFX_FISCAL_TRANSPORT"] == ["simulator"]
    assert assignments["NFX_FISCAL_DESTINATION"] == ["simulator://empty"]
    assert assignments["NFX_FISCAL_ALLOWLIST"] == ["simulator://empty"]


@pytest.mark.parametrize("name", ["NFX_SECRET_KEY", "NFX_CERTIFICATE_MASTER_KEY"])
def test_required_template_secrets_cannot_be_absent_or_placeholder(name: str) -> None:
    values = environment()
    values.pop(name)
    with pytest.raises(ConfigurationError):
        load_settings(values)

    values = environment(**{name: "CHANGE_ME"})
    with pytest.raises(ConfigurationError):
        load_settings(values)


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


def test_both_secret_sources_are_rejected_and_certificate_file_is_supported(tmp_path: Path) -> None:
    certificate_material = "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
    certificate_file = tmp_path / "certificate-key"
    certificate_file.write_text(certificate_material, encoding="utf-8")

    settings = load_settings(
        environment(
            NFX_CERTIFICATE_MASTER_KEY="",
            NFX_CERTIFICATE_MASTER_KEY_FILE=str(certificate_file),
        )
    )
    assert settings.secrets.certificate_master_key == b"\x01" * 32

    django_file = tmp_path / "django-key-conflict"
    django_file.write_text(CANARY, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_settings(environment(NFX_SECRET_KEY_FILE=str(django_file)))

    with pytest.raises(ConfigurationError):
        load_settings(
            environment(
                NFX_CERTIFICATE_MASTER_KEY=certificate_material,
                NFX_CERTIFICATE_MASTER_KEY_FILE=str(certificate_file),
            )
        )


@pytest.mark.parametrize("value", ["CHANGE_ME", "not-base64url-key"])
def test_malformed_certificate_master_key_fails_closed(value: str) -> None:
    with pytest.raises(ConfigurationError):
        load_settings(environment(NFX_CERTIFICATE_MASTER_KEY=value))


def test_certificate_master_key_requires_external_base64url_32_byte_material() -> None:
    settings = load_settings(environment())
    assert settings.secrets.certificate_master_key == b"\x00" * 32
    with pytest.raises(ConfigurationError):
        load_settings(environment(NFX_CERTIFICATE_MASTER_KEY="too-short"))


def test_operational_thresholds_have_safe_defaults_and_are_validated() -> None:
    settings = load_settings(environment())
    assert settings.operational.worker_heartbeat_timeout_seconds == 30
    assert settings.operational.scheduler_heartbeat_timeout_seconds == 30
    assert settings.operational.job_backlog_delay_seconds == 300
    with pytest.raises(ConfigurationError):
        load_settings(environment(NFX_JOB_BACKLOG_DELAY_SECONDS="0"))


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


def test_bootstrap_secret_is_only_allowlisted_for_the_explicit_command_boundary() -> None:
    values = environment(NFX_BOOTSTRAP_ADMIN_PASSWORD="synthetic-bootstrap-secret")
    with pytest.raises(ConfigurationError):
        load_settings(values)

    settings = load_settings(values, allow_bootstrap_admin=True)
    assert not hasattr(settings.public, "bootstrap_admin_password")
    assert not hasattr(settings.secrets, "bootstrap_admin_password")
