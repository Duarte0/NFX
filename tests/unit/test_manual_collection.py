from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.audit.models import AuditEvent
from nfx.certificates.models import Certificate, CertificateState
from nfx.collection.models import (
    CollectionExecution,
    CollectionExecutionState,
    CollectionOrigin,
    CollectionScope,
    InitialCollectionRequest,
)
from nfx.collection.services import (
    CollectionBlocked,
    CollectionFlowPaused,
    process_initial_collection_requests,
    reconcile_collection_job,
    request_collection,
)
from nfx.companies.models import Company, CompanyStatus, FlowFamily, FlowState
from nfx.companies.services import create_company
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import SessionIdentity, _digest
from nfx.jobs.handlers import clear_handlers, register_handler
from nfx.jobs.models import Job, JobOutcomeKind, JobPolicy
from nfx.jobs.policy import create_policy
from nfx.jobs.services import JobEngine, process_one

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
VALID_CNPJ = "11222333000181"


def actor(role: str = Role.ADMINISTRATOR) -> SessionIdentity:
    user = User.objects.create(
        email=f"{role}-{User.objects.count()}@example.test",
        name="Synthetic actor",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    return SessionIdentity(str(user.id), user.email, user.name, user.role)


def company() -> Company:
    result = create_company(
        actor=actor(), cnpj=VALID_CNPJ, legal_name="Synthetic Company", ip_address="127.0.0.1"
    )
    result.status = CompanyStatus.ACTIVE
    result.save(update_fields=["status", "updated_at"])
    return result


def certificate_for(company: Company) -> Certificate:
    return Certificate.objects.create(
        company=company,
        encrypted_data_key=b"synthetic-key",
        data_key_nonce=b"synthetic-nonce",
        encrypted_password=b"synthetic-password",
        password_nonce=b"synthetic-password-nonce",
        fingerprint_sha256="a" * 64,
        certificate_cnpj=company.cnpj,
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=365),
        state=CertificateState.CURRENT,
    )


def policy(family: str, *, retry_limit: int = 2) -> JobPolicy:
    return create_policy(
        source_scope="synthetic",
        flow_scope=family,
        version=1,
        valid_from=NOW - timedelta(days=1),
        retry_limit=retry_limit,
        backoff_initial_seconds=1,
        backoff_cap_seconds=10,
    )


@pytest.fixture(autouse=True)
def reset_handlers() -> None:
    clear_handlers()
    yield
    clear_handlers()


@pytest.mark.django_db
def test_complete_request_expands_to_independent_flows_and_duplicate_reuses_active() -> None:
    company_row = company()
    certificate_for(company_row)
    policy(FlowFamily.NFE)
    policy(FlowFamily.NFSE)

    first = request_collection(
        company_id=company_row.id,
        scope=CollectionScope.COMPLETE,
        origin=CollectionOrigin.MANUAL,
        actor=actor(Role.OPERATOR),
        ip_address="127.0.0.1",
        now=NOW,
    )
    duplicate = request_collection(
        company_id=company_row.id,
        scope=CollectionScope.COMPLETE,
        origin=CollectionOrigin.MANUAL,
        actor=actor(Role.OPERATOR),
        ip_address="127.0.0.1",
        now=NOW,
    )

    assert len(first.executions) == 2
    assert duplicate.duplicate is True
    assert {row.id for row in duplicate.executions} == {row.id for row in first.executions}
    assert Job.objects.count() == 2
    assert AuditEvent.objects.filter(action="collection.request", result="duplicate").exists()


@pytest.mark.django_db
def test_request_revalidates_paused_and_blocked_flows() -> None:
    company_row = company()
    certificate_for(company_row)
    policy(FlowFamily.NFE)
    flow = company_row.flows.get(family=FlowFamily.NFE)
    flow.state = FlowState.PAUSED
    flow.save(update_fields=["state", "updated_at"])
    with pytest.raises(CollectionFlowPaused):
        request_collection(
            company_id=company_row.id,
            scope=CollectionScope.NFE,
            origin=CollectionOrigin.MANUAL,
            actor=actor(Role.OPERATOR),
            ip_address="127.0.0.1",
            now=NOW,
        )

    flow.state = FlowState.ENABLED
    flow.collection_state = CollectionExecutionState.BLOCKED
    flow.blocked_reason = "certificate_required"
    flow.save(update_fields=["state", "collection_state", "blocked_reason", "updated_at"])
    with pytest.raises(CollectionBlocked):
        request_collection(
            company_id=company_row.id,
            scope=CollectionScope.NFE,
            origin=CollectionOrigin.MANUAL,
            actor=actor(Role.OPERATOR),
            ip_address="127.0.0.1",
            now=NOW,
        )


@pytest.mark.django_db
def test_job_outcomes_update_execution_and_flow_without_fiscal_network() -> None:
    company_row = company()
    certificate_for(company_row)
    policy(FlowFamily.NFE)
    requested = request_collection(
        company_id=company_row.id,
        scope=CollectionScope.NFE,
        origin=CollectionOrigin.MANUAL,
        actor=actor(Role.OPERATOR),
        ip_address="127.0.0.1",
        now=NOW,
    )
    execution = requested.executions[0]

    def synthetic_handler(job: Job) -> object:
        reconcile_collection_job(
            job, JobOutcomeKind.SUCCESS, {"query_valid": True, "unit_count": 0}
        )
        return {"query_valid": True, "unit_count": 0}

    register_handler("collection.synthetic", synthetic_handler)  # type: ignore[arg-type]
    execution.job.job_type = "collection.synthetic"
    execution.job.save(update_fields=["job_type", "updated_at"])
    assert process_one(JobEngine(clock=lambda: NOW), owner="worker-synthetic") is True

    execution.refresh_from_db()
    flow = company_row.flows.get(family=FlowFamily.NFE)
    assert execution.state == CollectionExecutionState.EMPTY
    assert flow.collection_state == CollectionExecutionState.EMPTY
    assert flow.active_execution_id is None
    assert execution.safe_summary == {"query_valid": True, "unit_count": 0}


@pytest.mark.django_db
def test_initial_handoff_is_consumed_idempotently_through_same_service() -> None:
    company_row = company()
    certificate = certificate_for(company_row)
    policy(FlowFamily.NFE)
    policy(FlowFamily.NFSE)
    handoff = InitialCollectionRequest.objects.create(
        company=company_row,
        certificate=certificate,
        kind="initial",
        idempotency_key=f"initial:{company_row.id}",
    )

    first = process_initial_collection_requests(now=NOW)
    second = process_initial_collection_requests(now=NOW)

    handoff.refresh_from_db()
    assert first == 1
    assert second == 0
    assert handoff.state == "consumed"
    assert (
        CollectionExecution.objects.filter(
            company=company_row, origin=CollectionOrigin.AUTOMATIC
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_collection_http_allows_safe_viewer_read_and_rejects_mutation() -> None:
    company_row = company()
    viewer = actor(Role.VIEWER)
    token = "synthetic-collection-session"
    IdentitySession.objects.create(
        token_hash=_digest(token),
        user=User.objects.get(id=viewer.user_id),
        revocation_version=1,
        last_activity_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    client = Client()
    client.cookies["nfx_session"] = token

    listed = client.get("/api/collections")
    rejected = client.post(
        f"/api/companies/{company_row.id}/collection/request",
        data='{"scope":"nfe"}',
        content_type="application/json",
    )
    assert listed.status_code == 200
    assert listed.json()["collections"][0]["company_id"] == str(company_row.id)
    assert rejected.status_code == 403
