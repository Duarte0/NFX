from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.audit.models import AuditEvent
from nfx.certificates.models import Certificate, CertificateState
from nfx.companies.models import Company, CompanyStatus
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest
from nfx.jobs.models import Job


def _client(role: str, *, expired: bool = False) -> Client:
    user = User.objects.create(
        email=f"certificate-inventory-{role}-{uuid4().hex}@example.test",
        name="Synthetic certificate inventory user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"certificate-inventory-token-{uuid4().hex}"
    now = timezone.now()
    IdentitySession.objects.create(
        token_hash=_digest(token),
        user=user,
        revocation_version=user.revocation_version,
        last_activity_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    if expired:
        expired_at = now - timedelta(minutes=1)
        IdentitySession.objects.filter(token_hash=_digest(token)).update(
            created_at=expired_at - timedelta(seconds=1),
            expires_at=expired_at,
            last_activity_at=expired_at,
        )
    client = Client()
    client.cookies["nfx_session"] = token
    return client


def _company(name: str) -> Company:
    return Company.objects.create(
        cnpj=f"company-certificate-{uuid4().hex}",
        legal_name=name,
        status=CompanyStatus.ACTIVE,
    )


def _certificate(
    company: Company,
    *,
    evaluated_at: datetime,
    not_after: datetime,
    state: str = CertificateState.CURRENT,
) -> Certificate:
    return Certificate.objects.create(
        id=uuid4(),
        company=company,
        encrypted_data_key=b"encrypted-data-key",
        data_key_nonce=b"data-key-nonce",
        encrypted_password=b"encrypted-password",
        password_nonce=b"password-nonce",
        fingerprint_sha256=uuid4().hex + uuid4().hex,
        certificate_cnpj=company.cnpj,
        not_before=evaluated_at - timedelta(days=1),
        not_after=not_after,
        state=state,
        activated_at=evaluated_at if state == CertificateState.CURRENT else None,
    )


@pytest.mark.django_db(transaction=True)
def test_certificate_cards_reconcile_with_current_expired_and_expiring_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluated_at = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("django.utils.timezone.now", lambda: evaluated_at)
    companies = [_company(f"Empresa Certificado {index}") for index in range(4)]
    _certificate(companies[0], evaluated_at=evaluated_at, not_after=evaluated_at)
    _certificate(
        companies[1], evaluated_at=evaluated_at, not_after=evaluated_at + timedelta(days=1)
    )
    _certificate(
        companies[2], evaluated_at=evaluated_at, not_after=evaluated_at + timedelta(days=30)
    )
    _certificate(
        companies[3], evaluated_at=evaluated_at, not_after=evaluated_at + timedelta(days=31)
    )
    _certificate(
        _company("Empresa História Substituída"),
        evaluated_at=evaluated_at,
        not_after=evaluated_at,
        state=CertificateState.REPLACED,
    )
    _certificate(
        _company("Empresa Pendente"),
        evaluated_at=evaluated_at,
        not_after=evaluated_at + timedelta(days=1),
        state=CertificateState.PENDING,
    )
    _certificate(
        _company("Empresa Falha de Armazenamento"),
        evaluated_at=evaluated_at,
        not_after=evaluated_at + timedelta(days=1),
        state=CertificateState.STORAGE_FAILED,
    )

    client = _client(Role.OPERATOR)
    dashboard = client.get("/api/dashboard").json()
    cards = {card["id"]: card for card in dashboard["cards"]}

    for name, expected in (("current", 4), ("expired", 1), ("expiring", 2)):
        assert cards[f"certificates.{name}"]["current"]["value"] == expected
        assert cards[f"certificates.{name}"]["drilldown"] == {
            "href": f"?filter={name}#empresas",
            "filters": {"filter": name},
        }
        response = client.get("/api/certificates/inventory", {"filter": name})
        assert response.status_code == 200
        payload = response.json()
        assert payload["filter"] == {"filter": name}
        assert payload["total"] == expected
        assert payload["evaluated_at"] == evaluated_at.isoformat()
        assert payload["freshness"] == {
            "status": "fresh",
            "evaluated_at": evaluated_at.isoformat(),
            "age_seconds": 0,
        }
        assert all("fingerprint" not in row for row in payload["certificates"])
        assert "encrypted" not in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_certificate_inventory_has_stable_bounded_cursor_pages_and_zero() -> None:
    evaluated_at = timezone.now()
    companies = [_company(f"Empresa Página {index}") for index in range(3)]
    for company in companies:
        _certificate(
            company,
            evaluated_at=evaluated_at,
            not_after=evaluated_at + timedelta(days=31),
        )
    client = _client(Role.ADMINISTRATOR)

    first = client.get(
        "/api/certificates/inventory", {"filter": "current", "limit": "2"}
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["total"] == 3
    assert first_payload["truncated"] is True
    assert first_payload["next_cursor"]

    second = client.get(
        "/api/certificates/inventory",
        {"filter": "current", "limit": "2", "cursor": first_payload["next_cursor"]},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["total"] == 3
    assert second_payload["truncated"] is False
    assert {
        row["id"] for row in first_payload["certificates"] + second_payload["certificates"]
    } == {str(certificate.id) for certificate in Certificate.objects.all()}

    empty = client.get("/api/certificates/inventory", {"filter": "expired"})
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert empty.json()["certificates"] == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "query",
    [
        {},
        {"filter": "unknown"},
        {"filter": ["current", "expired"]},
        {"filter": "current", "status": "current"},
    ],
)
def test_certificate_inventory_rejects_invalid_filters_without_unfiltered_fallback(
    query: dict[str, object],
) -> None:
    _certificate(
        _company("Empresa Não Exposta"),
        evaluated_at=timezone.now(),
        not_after=timezone.now() + timedelta(days=31),
    )

    response = _client(Role.OPERATOR).get("/api/certificates/inventory", query)

    assert response.status_code == 400
    assert "Empresa Não Exposta" not in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_certificate_inventory_enforces_certificate_policy_and_is_side_effect_free() -> None:
    _certificate(
        _company("Empresa Protegida"),
        evaluated_at=timezone.now(),
        not_after=timezone.now() + timedelta(days=31),
    )
    expired_client = _client(Role.OPERATOR, expired=True)
    viewer_client = _client(Role.VIEWER)
    permitted = _client(Role.OPERATOR)

    assert Client().get("/api/certificates/inventory", {"filter": "current"}).status_code == 403
    assert (
        expired_client.get("/api/certificates/inventory", {"filter": "current"}).status_code
        == 403
    )
    assert viewer_client.get(
        "/api/certificates/inventory", {"filter": "current"}
    ).status_code == 403
    viewer_dashboard = viewer_client.get("/api/dashboard").json()
    assert not any(card["id"].startswith("certificates.") for card in viewer_dashboard["cards"])
    assert viewer_dashboard["capabilities"]["certificates"] == {"status": "admin_only"}

    before = {"audit": AuditEvent.objects.count(), "jobs": Job.objects.count()}
    assert permitted.get("/api/certificates/inventory", {"filter": "current"}).status_code == 200
    assert permitted.get("/api/certificates/inventory", {"filter": "current"}).status_code == 200
    assert {"audit": AuditEvent.objects.count(), "jobs": Job.objects.count()} == before


@pytest.mark.django_db(transaction=True)
def test_certificate_inventory_source_failure_is_unavailable_without_erasing_dashboard_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.certificates.views.certificate_inventory_queryset",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic source")),
    )
    client = _client(Role.OPERATOR)

    response = client.get("/api/certificates/inventory", {"filter": "current"})
    dashboard = client.get("/api/dashboard")

    assert response.status_code == 503
    assert "synthetic source" not in response.content.decode()
    assert dashboard.status_code == 200
    cards = {card["id"]: card for card in dashboard.json()["cards"]}
    assert cards["certificates.current"]["status"] in {"ready", "zero"}
    assert cards["documents.total"]["status"] in {"ready", "zero"}
