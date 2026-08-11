from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.audit.models import AuditEvent
from nfx.companies.models import Company, CompanyStatus
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest


def _client(role: str, *, expired: bool = False) -> Client:
    user = User.objects.create(
        email=f"company-list-{role}-{uuid4().hex}@example.test",
        name="Synthetic company-list user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"company-list-token-{uuid4().hex}"
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


def _company(status: str, name: str) -> Company:
    return Company.objects.create(
        cnpj=f"company-list-{uuid4().hex}",
        legal_name=name,
        status=status,
        deactivation_reason="synthetic" if status == CompanyStatus.DEACTIVATED else None,
    )


@pytest.mark.django_db(transaction=True)
def test_company_cards_reconcile_with_active_and_inactive_filtered_totals() -> None:
    active = _company(CompanyStatus.ACTIVE, "Empresa Ativa")
    _company(CompanyStatus.REGISTERED, "Empresa Cadastrada")
    _company(CompanyStatus.DEACTIVATED, "Empresa Desativada")
    client = _client(Role.OPERATOR)

    dashboard = client.get("/api/dashboard").json()
    cards = {card["id"]: card for card in dashboard["cards"]}
    assert cards["companies.active"]["drilldown"] == {
        "href": "?lifecycle=active#empresas",
        "filters": {"lifecycle": "active"},
    }
    assert cards["companies.inactive"]["drilldown"] == {
        "href": "?lifecycle=inactive#empresas",
        "filters": {"lifecycle": "inactive"},
    }

    active_response = client.get("/api/companies", {"lifecycle": "active"})
    assert active_response.status_code == 200
    assert active_response.json()["filter"] == {"lifecycle": "active"}
    assert active_response.json()["total"] == 1
    assert [row["id"] for row in active_response.json()["companies"]] == [str(active.id)]

    inactive_response = client.get("/api/companies", {"lifecycle": "inactive"})
    assert inactive_response.status_code == 200
    assert inactive_response.json()["filter"] == {"lifecycle": "inactive"}
    assert inactive_response.json()["total"] == 2
    assert {row["status"] for row in inactive_response.json()["companies"]} == {
        CompanyStatus.REGISTERED,
        CompanyStatus.DEACTIVATED,
    }


@pytest.mark.django_db(transaction=True)
def test_company_list_total_is_full_filtered_total_across_stable_cursor_pages() -> None:
    companies = [_company(CompanyStatus.ACTIVE, f"Empresa {index}") for index in range(3)]
    client = _client(Role.ADMINISTRATOR)

    first = client.get("/api/companies", {"lifecycle": "active", "limit": "2"})
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["total"] == 3
    assert first_payload["limit"] == 2
    assert first_payload["truncated"] is True
    assert first_payload["next_cursor"] == first_payload["companies"][-1]["id"]

    second = client.get(
        "/api/companies",
        {"lifecycle": "active", "limit": "2", "cursor": first_payload["next_cursor"]},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["total"] == 3
    assert second_payload["truncated"] is False
    assert [row["id"] for row in first_payload["companies"] + second_payload["companies"]] == [
        str(company.id) for company in sorted(companies, key=lambda item: item.id)
    ]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("query", [
    {"lifecycle": ["active", "inactive"]},
    {"lifecycle": "active", "status": "ativa"},
    {"lifecycle": "unsupported"},
])
def test_company_list_rejects_ambiguous_or_invalid_lifecycle_filters(
    query: dict[str, str | list[str]],
) -> None:
    response = _client(Role.OPERATOR).get("/api/companies", query)

    assert response.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_company_list_denies_anonymous_expired_and_visualizer_without_leaking_rows() -> None:
    _company(CompanyStatus.ACTIVE, "Empresa Protegida")

    assert Client().get("/api/companies", {"lifecycle": "active"}).status_code == 403
    assert _client(Role.OPERATOR, expired=True).get(
        "/api/companies", {"lifecycle": "active"}
    ).status_code == 403
    viewer_response = _client(Role.VIEWER).get("/api/companies", {"lifecycle": "active"})
    assert viewer_response.status_code == 403
    assert "Empresa Protegida" not in viewer_response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_repeated_company_reads_are_side_effect_free() -> None:
    _company(CompanyStatus.ACTIVE, "Empresa Repetida")
    client = _client(Role.OPERATOR)
    before = AuditEvent.objects.count()

    assert client.get("/api/companies", {"lifecycle": "active"}).status_code == 200
    assert client.get("/api/companies", {"lifecycle": "active"}).status_code == 200

    assert AuditEvent.objects.count() == before


@pytest.mark.django_db(transaction=True)
def test_company_source_failure_is_unavailable_without_erasing_dashboard_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _company(CompanyStatus.ACTIVE, "Empresa Disponível")
    client = _client(Role.OPERATOR)

    monkeypatch.setattr(
        "nfx.companies.views.company_list_queryset",
        lambda selected, apply_cursor=True: (_ for _ in ()).throw(RuntimeError("source")),
    )

    response = client.get("/api/companies", {"lifecycle": "active"})
    dashboard = client.get("/api/dashboard")

    assert response.status_code == 503
    assert "source" not in response.content.decode()
    assert dashboard.status_code == 200
    assert {card["id"] for card in dashboard.json()["cards"]} >= {
        "companies.active",
        "documents.total",
    }
