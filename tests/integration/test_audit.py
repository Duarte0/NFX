from __future__ import annotations

import threading

import pytest
from django.contrib.auth.hashers import make_password
from django.db import DatabaseError, connections, transaction
from django.test import Client
from nfx.audit.models import AuditEvent
from nfx.audit.services import AuditService, AuditVerifier, MissingAuditReason, event_hash
from nfx.identity.models import Role, User


@pytest.mark.django_db
def test_append_redacts_canaries_and_uses_a_stable_hash_vector() -> None:
    canary = "synthetic-secret-canary"
    event = AuditService().append(
        action="auth.login_failure",
        entity_type="identity",
        entity_id="anonymous",
        result="denied",
        ip_address="127.0.0.1",
        context={"password": canary, "xml": "<?xml version='1.0'?><x/>"},
    )

    assert event.sequence == 1
    assert event.previous_hash == "0" * 64
    assert canary not in str(event.context)
    assert event.event_hash == event_hash(
        v=1,
        sequence=1,
        occurred_at=event.occurred_at.isoformat(),
        actor_id=None,
        actor_role="",
        ip_address="127.0.0.1",
        action="auth.login_failure",
        entity_type="identity",
        entity_id="anonymous",
        result="denied",
        reason="",
        correlation_id="",
        context=event.context,
        previous_hash="0" * 64,
    )


@pytest.mark.django_db
def test_required_reasons_and_append_only_guards_are_enforced() -> None:
    service = AuditService()
    with pytest.raises(MissingAuditReason):
        service.append(action="user.deactivate", entity_type="user", result="denied")
    event = service.append(
        action="user.deactivate",
        entity_type="user",
        entity_id="u-1",
        result="success",
        reason="synthetic policy reason",
    )

    event.result = "tampered"
    with transaction.atomic():
        with pytest.raises(DatabaseError, match="append-only"):
            event.save()
    with transaction.atomic():
        with pytest.raises(DatabaseError, match="append-only"):
            AuditEvent.objects.filter(id=event.id).update(result="tampered")
    with transaction.atomic():
        with pytest.raises(DatabaseError, match="append-only"):
            AuditEvent.objects.filter(id=event.id).delete()


@pytest.mark.django_db(transaction=True)
def test_two_writers_serialize_and_verifier_detects_tampering_removal_and_reordering() -> None:
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def append(index: int) -> None:
        try:
            barrier.wait()
            AuditService().append(
                action=f"collection.retry.{index}", entity_type="collection", result="success"
            )
        except BaseException as exc:  # pragma: no cover - asserted by caller
            errors.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=append, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    rows = list(AuditEvent.objects.all())
    assert [row.sequence for row in rows] == [1, 2]
    assert AuditVerifier().verify(rows).valid

    rows[0].result = "tampered"
    assert not AuditVerifier().verify(rows).valid
    rows[0].result = "success"
    assert not AuditVerifier().verify(rows[1:]).valid
    assert not AuditVerifier().verify(list(reversed(rows))).valid


@pytest.mark.django_db
def test_audit_api_is_admin_only_and_paginates() -> None:
    admin = User.objects.create(
        email="admin@example.test",
        name="Admin",
        role=Role.ADMINISTRATOR,
        password_hash=make_password("correct"),
    )
    User.objects.create(
        email="viewer@example.test",
        name="Viewer",
        role=Role.VIEWER,
        password_hash=make_password("correct"),
    )
    for index in range(3):
        AuditService().append(
            action=f"health.check.{index}",
            entity_type="health",
            result="success",
            actor_id=admin.id,
            actor_role=admin.role,
        )

    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/csrf")
    csrf = client.cookies["csrftoken"].value
    client.post(
        "/api/auth/login",
        data='{"email":"viewer@example.test","password":"correct"}',
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert client.get("/api/audit/events").status_code == 403

    client.post("/api/auth/logout", HTTP_X_CSRFTOKEN=csrf)
    client.post(
        "/api/auth/login",
        data='{"email":"admin@example.test","password":"correct"}',
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    response = client.get("/api/audit/events?limit=2&entity_type=health")
    assert response.status_code == 200
    assert len(response.json()["events"]) == 2
    assert response.json()["next_cursor"] is not None
