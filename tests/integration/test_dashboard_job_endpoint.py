from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.audit.models import AuditEvent
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest
from nfx.jobs.models import Job, JobOutcomeKind, JobState


def _client(role: str, *, expires_at: datetime | None = None) -> Client:
    user = User.objects.create(
        email=f"job-dashboard-{role}-{uuid4().hex}@example.test",
        name="Synthetic job dashboard user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"job-dashboard-token-{uuid4().hex}"
    now = timezone.now()
    session = IdentitySession.objects.create(
        token_hash=_digest(token),
        user=user,
        revocation_version=user.revocation_version,
        last_activity_at=now,
        expires_at=expires_at if expires_at and expires_at > now else now + timedelta(minutes=30),
    )
    if expires_at is not None and expires_at <= now:
        IdentitySession.objects.filter(id=session.id).update(
            created_at=expires_at - timedelta(minutes=30),
            expires_at=expires_at,
        )
    client = Client()
    client.cookies["nfx_session"] = token
    return client


def _job(
    *,
    created_at: datetime,
    state: str = JobState.QUEUED,
    outcome: str = "",
    job_type: str = "synthetic.dashboard",
    safe_error: str = "",
    payload: dict[str, str] | None = None,
) -> Job:
    row = Job.objects.create(
        job_type=job_type,
        logical_target=f"company:{uuid4().hex}",
        payload=payload or {"reference": "synthetic"},
        idempotency_key=f"dashboard-job-{uuid4().hex}",
        scheduled_at=created_at,
        state=state,
        last_outcome=outcome,
        safe_error=safe_error,
        attempt_count=1 if outcome else 0,
        lease_owner="synthetic-worker" if state == JobState.RUNNING else None,
        lease_issued_at=created_at if state == JobState.RUNNING else None,
        lease_expires_at=created_at + timedelta(minutes=1) if state == JobState.RUNNING else None,
    )
    Job.objects.filter(id=row.id).update(created_at=created_at)
    return Job.objects.get(id=row.id)


@pytest.mark.django_db(transaction=True)
def test_job_cards_and_filtered_list_reconcile_at_both_period_boundaries() -> None:
    brasilia = ZoneInfo("America/Sao_Paulo")
    start = datetime(2026, 8, 1, tzinfo=brasilia)
    end = datetime(2026, 9, 1, tzinfo=brasilia)
    _job(created_at=start, job_type="synthetic.pending.start")
    _job(created_at=end - timedelta(seconds=1), job_type="synthetic.pending.end")
    _job(
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        outcome=JobOutcomeKind.TEMPORARY,
        safe_error="temporary_failure",
        job_type="synthetic.failed",
    )
    _job(
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
        state=JobState.BLOCKED,
        outcome=JobOutcomeKind.PERMANENT,
        safe_error="permanent_failure",
        job_type="synthetic.blocked",
    )
    _job(created_at=end, job_type="synthetic.outside")

    client = _client(Role.VIEWER)
    dashboard = client.get("/api/dashboard", {"from": "2026-08-01", "to": "2026-09-01"})
    assert dashboard.status_code == 200
    cards = {card["id"]: card for card in dashboard.json()["cards"]}

    for name in ("pending", "failed", "blocked"):
        assert cards[f"jobs.{name}"]["drilldown"] == {
            "href": f"?from=2026-08-01&to=2026-09-01&filter={name}#dashboard",
            "filters": {"from": "2026-08-01", "to": "2026-09-01", "filter": name},
        }
        response = client.get(
            "/api/jobs/observability",
            {"from": "2026-08-01", "to": "2026-09-01", "filter": name},
        )
        assert response.status_code == 200
        payload = response.json()
        assert cards[f"jobs.{name}"]["current"]["value"] == payload["total"]
        assert payload["filter"] == {
            "from": "2026-08-01",
            "to": "2026-09-01",
            "filter": name,
        }
        assert payload["boundary"] == "[from,to)"

    assert cards["jobs.pending"]["current"]["value"] == 3
    assert client.get(
        "/api/jobs/observability",
        {"from": "2026-08-01", "to": "2026-09-01", "filter": "pending"},
    ).json()["total"] == 3
    assert client.get(
        "/api/jobs/observability",
        {"from": "2026-08-01", "to": "2026-09-01", "filter": "failed"},
    ).json()["total"] == 2
    assert client.get(
        "/api/jobs/observability",
        {"from": "2026-08-01", "to": "2026-09-01", "filter": "blocked"},
    ).json()["total"] == 1
    empty = client.get(
        "/api/jobs/observability",
        {"from": "2026-09-01", "to": "2026-09-02", "filter": "blocked"},
    )
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert empty.json()["jobs"] == []


@pytest.mark.django_db(transaction=True)
def test_job_list_is_bounded_stable_redacted_and_side_effect_free() -> None:
    created_at = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    for index in range(52):
        _job(
            created_at=created_at,
            job_type=f"synthetic.job.{index}",
            payload={"secret": "payload-must-not-leak"},
            safe_error="raw-provider-error-token",
        )
    client = _client(Role.OPERATOR)
    before = {"jobs": Job.objects.count(), "audit": AuditEvent.objects.count()}
    query = {"from": "2026-08-01", "to": "2026-09-01", "filter": "pending"}

    first = client.get("/api/jobs/observability", query)
    second = client.get("/api/jobs/observability", query)

    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    payload = first.json()
    assert payload["total"] == 52
    assert payload["limit"] == 50
    assert payload["truncated"] is True
    assert len(payload["jobs"]) == 50
    assert all(
        set(row) == {
            "id",
            "job_type",
            "state",
            "outcome",
            "created_at",
            "scheduled_at",
            "last_attempt_at",
            "completed_at",
            "attempt_count",
            "safe_error",
        }
        for row in payload["jobs"]
    )
    serialized = first.content.decode()
    assert "payload-must-not-leak" not in serialized
    assert "raw-provider-error-token" not in serialized
    assert "lease_owner" not in serialized
    assert "logical_target" not in serialized
    assert {"jobs": Job.objects.count(), "audit": AuditEvent.objects.count()} == before


@pytest.mark.django_db(transaction=True)
def test_concurrent_identical_job_reads_are_deterministic_and_side_effect_free() -> None:
    created_at = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    for index in range(4):
        _job(created_at=created_at, job_type=f"synthetic.concurrent.{index}")
    session_client = _client(Role.VIEWER)
    session_token = session_client.cookies["nfx_session"].value
    query = {"from": "2026-08-01", "to": "2026-09-01", "filter": "pending"}
    before = {"jobs": Job.objects.count(), "audit": AuditEvent.objects.count()}

    def read_job_list(_: int) -> tuple[int, bytes]:
        client = Client()
        client.cookies["nfx_session"] = session_token
        response = client.get("/api/jobs/observability", query)
        return response.status_code, response.content

    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(read_job_list, range(8)))

    assert {status for status, _ in responses} == {200}
    assert len({content for _, content in responses}) == 1
    assert Job.objects.count() == before["jobs"]
    assert AuditEvent.objects.count() == before["audit"]


@pytest.mark.django_db(transaction=True)
def test_job_list_rejects_invalid_filters_and_expired_or_anonymous_sessions() -> None:
    query = {"from": "2026-08-01", "to": "2026-09-01", "filter": "pending"}
    for invalid in (
        {"from": "2026-08-01", "to": "2026-09-01"},
        {**query, "filter": "unknown"},
        {**query, "extra": "value"},
    ):
        assert _client(Role.VIEWER).get("/api/jobs/observability", invalid).status_code == 400
    assert Client().get("/api/jobs/observability", query).status_code == 403
    expired = _client(Role.VIEWER, expires_at=timezone.now() - timedelta(seconds=1))
    assert expired.get("/api/jobs/observability", query).status_code == 403


@pytest.mark.django_db(transaction=True)
def test_job_source_failure_degrades_only_processing_cards_and_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nfx.operations.dashboard._job_counts",
        lambda period: (_ for _ in ()).throw(RuntimeError("raw database failure")),
    )
    cards = {
        card["id"]: card
        for card in _client(Role.VIEWER)
        .get("/api/dashboard", {"from": "2026-08-01", "to": "2026-09-01"})
        .json()["cards"]
    }

    assert cards["jobs.pending"]["status"] == "unavailable"
    assert cards["jobs.pending"]["current"]["value"] is None
    assert cards["documents.total"]["status"] != "unavailable"

    monkeypatch.setattr(
        "nfx.jobs.observability.job_observability_queryset",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("raw database failure")),
    )
    response = _client(Role.VIEWER).get(
        "/api/jobs/observability",
        {"from": "2026-08-01", "to": "2026-09-01", "filter": "pending"},
    )
    assert response.status_code == 503
    assert "raw database failure" not in response.content.decode()
