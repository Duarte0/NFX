from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from nfx.infrastructure.configuration import ConfigurationError, load_settings

ROOT = Path(__file__).parents[2]


def _runtime_compose() -> dict[str, object]:
    return yaml.safe_load((ROOT / "docker-compose.runtime.yml").read_text(encoding="utf-8"))


def test_runtime_compose_has_private_services_and_one_published_proxy() -> None:
    document = _runtime_compose()
    services = document["services"]
    assert set(services) == {
        "proxy",
        "web",
        "worker",
        "scheduler",
        "postgres",
        "minio",
        "minio-init",
    }

    published = {
        name: service.get("ports", [])
        for name, service in services.items()
        if service.get("ports")
    }
    assert set(published) == {"proxy"}
    assert len(published["proxy"]) == 2
    assert all("8443" in port or "8080" in port for port in published["proxy"])

    app_images = {services[name]["image"] for name in ("web", "worker", "scheduler")}
    assert len(app_images) == 1
    assert "NFX_APP_IMAGE" in str(next(iter(app_images)))
    assert services["postgres"]["volumes"]
    assert services["minio"]["volumes"]

    for name in ("web", "worker", "scheduler"):
        assert services[name]["healthcheck"]
        assert services[name]["mem_limit"]
        assert services[name]["cpus"]
        assert services[name]["tmpfs"]


def test_runtime_proxy_requires_external_tls_and_uses_bounded_forwarding() -> None:
    proxy = _runtime_compose()["services"]["proxy"]
    text = (ROOT / "deploy/nginx/runtime.conf").read_text(encoding="utf-8")

    assert "NFX_TLS_DIR" in str(proxy["volumes"])
    assert ":/etc/nginx/tls:ro" in str(proxy["volumes"])
    assert proxy["build"]["target"] == "runtime-proxy"
    assert "listen 8443 ssl" in text
    assert "listen 8080" in text
    assert "ssl_certificate /etc/nginx/tls/tls.crt" in text
    assert "ssl_certificate_key /etc/nginx/tls/tls.key" in text
    assert "client_max_body_size 10m" in text
    assert "proxy_connect_timeout 5s" in text
    assert "proxy_read_timeout 30s" in text
    assert "Strict-Transport-Security" in text
    assert "X-Content-Type-Options" in text


def test_runtime_secrets_are_external_and_not_embedded_in_compose() -> None:
    document = (ROOT / "docker-compose.runtime.yml").read_text(encoding="utf-8")
    assert "NFX_SECRET_KEY_FILE: /run/secrets/nfx_secret_key" in document
    assert "NFX_CERTIFICATE_MASTER_KEY_FILE: /run/secrets/nfx_certificate_master_key" in document
    assert "NFX_SECRET_DIR" in document
    assert "NFX_SECRET_KEY:" not in document
    assert "NFX_CERTIFICATE_MASTER_KEY:" not in document
    assert "DATABASE_URL: ${DATABASE_URL:?" in document
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in document


def test_runtime_allowed_hosts_are_validated_and_available_to_django() -> None:
    settings = load_settings(
        {
            "NFX_PROFILE": "runtime",
            "NFX_SECRET_KEY": "synthetic-secret",
            "NFX_CERTIFICATE_MASTER_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "NFX_FISCAL_TRANSPORT": "simulator",
            "NFX_FISCAL_DESTINATION": "simulator://empty",
            "NFX_FISCAL_ALLOWLIST": "simulator://empty",
            "NFX_ALLOWED_HOSTS": "nfx.internal,localhost",
            "DATABASE_URL": "postgresql://user:password@database.test:5432/nfx_test",
            "MINIO_ROOT_PASSWORD": "synthetic-minio-secret",
        }
    )
    assert settings.public.allowed_hosts == ("nfx.internal", "localhost")

    with pytest.raises(ConfigurationError):
        load_settings(
            {
                "NFX_PROFILE": "runtime",
                "NFX_SECRET_KEY": "synthetic-secret",
                "NFX_CERTIFICATE_MASTER_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                "NFX_FISCAL_TRANSPORT": "simulator",
                "NFX_FISCAL_DESTINATION": "simulator://empty",
                "NFX_FISCAL_ALLOWLIST": "simulator://empty",
                "NFX_ALLOWED_HOSTS": "https://nfx.internal",
                "DATABASE_URL": "postgresql://user:password@database.test:5432/nfx_test",
                "MINIO_ROOT_PASSWORD": "synthetic-minio-secret",
            }
        )
