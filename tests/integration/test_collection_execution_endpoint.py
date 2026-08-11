from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.audit.models import AuditEvent
from nfx.collection.models import (
    CollectionExecution,
    CollectionExecutionState,
    CollectionOrigin,
    CollectionScope,
    IngestionOutcome,
    IngestionRecovery,
)
from nfx.companies.models import Company, CompanyStatus, FlowFamily
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest
from nfx.jobs.models import Job


def client(role: str = Role.VIEWER) -> Client:
    user = User.objects.create(
        email=f"collection-query-{role}-{uuid4().hex}@example.test",
        name="Synthetic collection query user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"collection-query-token-{uuid4().hex}"
    IdentitySession.objects.create(
        token_hash=_digest(token),
        user=user,
        revocation_version=user.revocation_version,
        last_activity_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    result = Client()
    result.cookies["nfx_session"] = token
    return result


def execution(
    company: Company,
    *,
    state: str,
    created_at: datetime,
    family: str = FlowFamily.NFE,
    safe_error: str = "",
) -> CollectionExecution:
    row = CollectionExecution.objects.create(
        company=company,
        family=family,
        requested_scope=CollectionScope.NFE,
        origin=CollectionOrigin.MANUAL,
        state=state,
        outcome=IngestionOutcome.UNKNOWN,
        recovery=IngestionRecovery.NONE,
        correlation_id=f"secret-correlation-{uuid4().hex}",
        safe_summary={
            "fiscal_xml": "<secret>",
            "object_key": "secret-object-key",
            "correlation": "unbounded-secret",
        },
        safe_error=safe_error,
    )
    CollectionExecution.objects.filter(id=row.id).update(created_at=created_at)
    row.refresh_from_db()
    return row


@pytest.mark.django_db(transaction=True)
def test_collection_cards_reconcile_with_bounded_filtered_execution_read() -> None:
    company_a = Company.objects.create(
        cnpj="11222333000181", legal_name="Empresa A", status=CompanyStatus.ACTIVE
    )
    company_b = Company.objects.create(
        cnpj="22333444000182", legal_name="Empresa B", status=CompanyStatus.ACTIVE
    )
    company_c = Company.objects.create(
        cnpj="33444555000183", legal_name="Empresa C", status=CompanyStatus.ACTIVE
    )
    start = datetime(2026, 8, 1, 3, tzinfo=UTC)
    end = datetime(2026, 9, 1, 3, tzinfo=UTC)
    execution(company_a, state=CollectionExecutionState.RUNNING, created_at=start)
    execution(company_b, state=CollectionExecutionState.RUNNING, created_at=end)
    execution(
        company_a, state=CollectionExecutionState.FAILED, created_at=end - timedelta(seconds=2)
    )
    execution(
        company_b, state=CollectionExecutionState.BLOCKED, created_at=end - timedelta(seconds=3)
    )
    execution(
        company_c, state=CollectionExecutionState.PARTIAL, created_at=end - timedelta(seconds=4)
    )
    execution(
        company_a,
        state=CollectionExecutionState.CONCLUDED,
        created_at=end - timedelta(seconds=5),
    )

    read_client = client()
    response = read_client.get(
        "/api/collections/executions",
        {"from": "2026-08-01", "to": "2026-09-01", "state": "running"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filter"] == {
        "from": "2026-08-01",
        "to": "2026-09-01",
        "state": "running",
    }
    assert payload["boundary"] == "[from,to)"
    assert payload["total"] == 1
    assert len(payload["executions"]) == 1
    assert payload["executions"][0]["company_name"] == "Empresa A"
    assert payload["executions"][0]["state"] == CollectionExecutionState.RUNNING
    assert "secret-object-key" not in response.content.decode()
    assert "<secret>" not in response.content.decode()
    assert "correlation_id" not in payload["executions"][0]
    expected_totals = {
        "recent": 5,
        "running": 1,
        "failed": 1,
        "blocked": 1,
        "partial": 1,
    }
    dashboard = read_client.get(
        "/api/dashboard", {"from": "2026-08-01", "to": "2026-09-01"}
    )
    assert dashboard.status_code == 200
    dashboard_cards = {card["id"]: card for card in dashboard.json()["cards"]}
    for state, expected in expected_totals.items():
        assert dashboard_cards[f"collections.{state}"]["current"]["value"] == expected
        filtered = read_client.get(
            "/api/collections/executions",
            {"from": "2026-08-01", "to": "2026-09-01", "state": state},
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == expected


@pytest.mark.django_db(transaction=True)
def test_dashboard_collection_links_preserve_period_and_each_canonical_filter() -> None:
    response = client().get(
        "/api/dashboard", {"from": "2026-08-01", "to": "2026-09-01"}
    )

    assert response.status_code == 200
    cards = {card["id"]: card for card in response.json()["cards"]}
    for state in ("recent", "running", "failed", "blocked", "partial"):
        card = cards[f"collections.{state}"]
        assert card["drilldown"]["filters"] == {
            "from": "2026-08-01",
            "to": "2026-09-01",
            "state": state,
        }
        assert card["drilldown"]["href"] == (
            f"?from=2026-08-01&to=2026-09-01&state={state}#coletas"
        )


@pytest.mark.django_db(transaction=True)
def test_collection_execution_read_rejects_anonymous_invalid_and_expired_sessions() -> None:
    params = {"from": "2026-08-01", "to": "2026-09-01", "state": "recent"}
    assert Client().get("/api/collections/executions", params).status_code == 403
    assert (
        client()
        .get("/api/collections/executions", {**params, "state": "invalid"})
        .status_code
        == 400
    )
    expired = client()
    user = User.objects.filter(email__startswith="collection-query-visualizador-").order_by(
        "-created_at"
    ).first()
    assert user is not None
    expired_at = timezone.now() - timedelta(seconds=2)
    IdentitySession.objects.filter(user=user).update(
        created_at=expired_at - timedelta(seconds=1),
        expires_at=expired_at,
        last_activity_at=expired_at,
    )
    assert expired.get("/api/collections/executions", params).status_code == 403


@pytest.mark.django_db(transaction=True)
def test_collection_execution_read_has_no_operational_side_effects() -> None:
    company = Company.objects.create(
        cnpj="11222333000181", legal_name="Empresa sem escrita", status=CompanyStatus.ACTIVE
    )
    execution(
        company,
        state=CollectionExecutionState.RUNNING,
        created_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    before = (CollectionExecution.objects.count(), Job.objects.count(), AuditEvent.objects.count())

    response = client().get(
        "/api/collections/executions",
        {"from": "2026-08-01", "to": "2026-09-01", "state": "recent"},
    )

    assert response.status_code == 200
    assert (
        CollectionExecution.objects.count(),
        Job.objects.count(),
        AuditEvent.objects.count(),
    ) == before

    empty = client().get(
        "/api/collections/executions",
        {"from": "2027-01-01", "to": "2027-02-01", "state": "recent"},
    )
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert empty.json()["executions"] == []


@pytest.mark.django_db(transaction=True)
def test_collection_execution_source_failure_is_not_reported_as_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.collection.views.list_collection_execution_summaries",
        lambda selected: (_ for _ in ()).throw(RuntimeError("provider details")),
    )

    response = client().get(
        "/api/collections/executions",
        {"from": "2026-08-01", "to": "2026-09-01", "state": "recent"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Não foi possível consultar as execuções de coleta."}
    assert "provider details" not in response.content.decode()
