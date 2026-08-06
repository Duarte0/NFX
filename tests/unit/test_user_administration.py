from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.test import Client
from django.utils import timezone
from nfx.audit.models import AuditEvent
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import (
    DuplicateUserEmail,
    LastAdministrator,
    SessionIdentity,
    UserAdministrationError,
    UserVersionConflict,
    authenticate,
    change_own_password,
    change_user_role,
    create_user,
    reset_user_password,
    resolve_session,
    set_user_active,
    update_user,
)


def _admin() -> User:
    return User.objects.create(
        email="admin@example.test",
        name="Admin",
        role=Role.ADMINISTRATOR,
        password_hash=make_password("correct"),
    )


def _identity(user: User) -> SessionIdentity:
    return SessionIdentity(str(user.id), user.email, user.name, user.role)


@pytest.mark.django_db
def test_admin_crud_redacts_password_and_records_required_audit_fields() -> None:
    admin = _admin()
    created = create_user(
        actor=_identity(admin),
        name="Viewer",
        email=" VIEWER@EXAMPLE.TEST ",
        role=Role.VIEWER,
        password="synthetic-initial-password",
        ip_address="127.0.0.1",
    )
    reset_user_password(
        actor=_identity(admin),
        user_id=str(created.id),
        version=created.version,
        password="synthetic-reset-password",
        reason="Synthetic support request",
        ip_address="127.0.0.1",
    )
    created.refresh_from_db()

    assert created.email == "viewer@example.test"
    assert check_password("synthetic-reset-password", created.password_hash)
    event = AuditEvent.objects.filter(action="user.password_reset").get()
    assert event.actor_id == admin.id and event.entity_id == str(created.id)
    assert event.reason == "Synthetic support request"
    assert "password" not in str(event.context).lower()


@pytest.mark.django_db
def test_admin_can_edit_role_and_lifecycle_with_audited_before_after() -> None:
    admin = _admin()
    target = User.objects.create(
        email="target@example.test",
        name="Target",
        role=Role.VIEWER,
        password_hash=make_password("correct"),
    )

    target = update_user(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        name="Renamed Target",
        email=" TARGET@EXAMPLE.TEST ",
        ip_address="127.0.0.1",
    )
    target = change_user_role(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        role=Role.OPERATOR,
        reason="Role change",
        ip_address="127.0.0.1",
    )
    target = set_user_active(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        active=False,
        reason="Temporary leave",
        ip_address="127.0.0.1",
    )
    target = set_user_active(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        active=True,
        reason="Return from leave",
        ip_address="127.0.0.1",
    )

    assert (target.name, target.email, target.role, target.active) == (
        "Renamed Target",
        "target@example.test",
        Role.OPERATOR,
        True,
    )
    assert [
        event.action
        for event in AuditEvent.objects.filter(entity_id=str(target.id)).order_by("sequence")
    ] == ["user.update", "user.role_change", "user.deactivate", "user.activate"]
    assert all(
        "password" not in str(event.context).lower()
        for event in AuditEvent.objects.filter(entity_id=str(target.id))
    )


@pytest.mark.django_db
def test_deactivation_invalidates_a_real_session_on_next_resolution() -> None:
    admin = _admin()
    target = User.objects.create(
        email="target@example.test",
        name="Target",
        role=Role.VIEWER,
        password_hash=make_password("correct"),
    )
    token, identity = authenticate(target.email, "correct", "127.0.0.1", "test-agent")
    assert token and identity is not None

    set_user_active(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        active=False,
        reason="Offboarding",
        ip_address="127.0.0.1",
    )

    assert resolve_session(token) is None
    assert AuditEvent.objects.filter(action="user.deactivate", entity_id=str(target.id)).exists()


@pytest.mark.django_db
def test_user_can_change_own_password_with_current_secret_and_revoke_sessions() -> None:
    user = _admin()
    change_own_password(
        actor=_identity(user),
        current_password="correct",
        password="synthetic-new-password",
        ip_address="127.0.0.1",
    )
    user.refresh_from_db()
    assert check_password("synthetic-new-password", user.password_hash)
    assert user.revocation_version == 2
    event = AuditEvent.objects.get(action="user.password_change")
    assert "password" not in str(event.context).lower()
    with pytest.raises(UserAdministrationError):
        change_own_password(
            actor=_identity(user),
            current_password="wrong",
            password="another-password",
            ip_address="127.0.0.1",
        )


@pytest.mark.django_db
def test_disable_and_reset_revoke_all_existing_sessions_and_preserve_history() -> None:
    admin, target = (
        _admin(),
        User.objects.create(
            email="target@example.test",
            name="Target",
            role=Role.VIEWER,
            password_hash=make_password("correct"),
        ),
    )
    IdentitySession.objects.create(
        token_hash="a" * 64,
        user=target,
        revocation_version=target.revocation_version,
        last_activity_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    reset_user_password(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        password="new",
        reason="reset",
        ip_address="127.0.0.1",
    )
    target.refresh_from_db()
    assert IdentitySession.objects.get().revocation_version != target.revocation_version
    set_user_active(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        active=False,
        reason="offboarding",
        ip_address="127.0.0.1",
    )
    target.refresh_from_db()
    assert not target.active
    assert AuditEvent.objects.filter(entity_id=str(target.id)).count() == 2


@pytest.mark.django_db
def test_reasons_versions_and_last_administrator_are_enforced() -> None:
    admin = _admin()
    with pytest.raises(LastAdministrator):
        set_user_active(
            actor=_identity(admin),
            user_id=str(admin.id),
            version=admin.version,
            active=False,
            reason="leave",
            ip_address="127.0.0.1",
        )
    target = User.objects.create(
        email="target@example.test",
        name="Target",
        role=Role.VIEWER,
        password_hash=make_password("x"),
    )
    with pytest.raises(Exception):
        change_user_role(
            actor=_identity(admin),
            user_id=str(target.id),
            version=target.version,
            role=Role.OPERATOR,
            reason="",
            ip_address="127.0.0.1",
        )
    with pytest.raises(UserVersionConflict):
        set_user_active(
            actor=_identity(admin),
            user_id=str(target.id),
            version=target.version + 1,
            active=False,
            reason="offboarding",
            ip_address="127.0.0.1",
        )


@pytest.mark.django_db
def test_service_boundary_rejects_non_admin_and_duplicate_or_invalid_email() -> None:
    admin = _admin()
    viewer = User.objects.create(
        email="viewer@example.test",
        name="Viewer",
        role=Role.VIEWER,
        password_hash=make_password("x"),
    )
    with pytest.raises(UserAdministrationError):
        create_user(
            actor=_identity(viewer),
            name="Denied",
            email="denied@example.test",
            role=Role.VIEWER,
            password="synthetic-password",
            ip_address="127.0.0.1",
        )
    with pytest.raises(UserAdministrationError):
        create_user(
            actor=_identity(admin),
            name="Invalid",
            email="not-an-email",
            role=Role.VIEWER,
            password="synthetic-password",
            ip_address="127.0.0.1",
        )
    with pytest.raises(DuplicateUserEmail):
        create_user(
            actor=_identity(admin),
            name="Duplicate",
            email=" VIEWER@EXAMPLE.TEST ",
            role=Role.VIEWER,
            password="synthetic-password",
            ip_address="127.0.0.1",
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_stale_admin_mutation_cannot_reverse_deactivation() -> None:
    admin, target = (
        _admin(),
        User.objects.create(
            email="target@example.test",
            name="Target",
            role=Role.VIEWER,
            password_hash=make_password("x"),
        ),
    )
    set_user_active(
        actor=_identity(admin),
        user_id=str(target.id),
        version=target.version,
        active=False,
        reason="offboarding",
        ip_address="127.0.0.1",
    )
    with pytest.raises(UserVersionConflict):
        change_user_role(
            actor=_identity(admin),
            user_id=str(target.id),
            version=target.version,
            role=Role.OPERATOR,
            reason="stale",
            ip_address="127.0.0.1",
        )


@pytest.mark.django_db
def test_user_http_routes_are_admin_only_and_never_return_passwords() -> None:
    _admin()
    target = User.objects.create(
        email="viewer@example.test",
        name="Viewer",
        role=Role.VIEWER,
        password_hash=make_password("correct"),
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
    assert client.get("/api/users").status_code == 403
    target_id = str(target.id)
    assert (
        client.post(
            "/api/users/create",
            data='{"name":"New","email":"new@example.test","role":"visualizador","password":"synthetic-password"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/users/{target_id}",
            data='{"name":"Changed","email":"changed@example.test","version":1}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/users/{target_id}/role",
            data='{"role":"operador","version":1,"reason":"change"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/users/{target_id}/password-reset",
            data='{"password":"synthetic-reset","version":1,"reason":"reset"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/users/{target_id}/active",
            data='{"active":false,"version":1,"reason":"offboarding"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/users/password",
            data='{"current_password":"correct","password":"synthetic-own-password"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 200
    )
    client.post("/api/auth/logout", HTTP_X_CSRFTOKEN=csrf)
    client.post(
        "/api/auth/login",
        data='{"email":"admin@example.test","password":"correct"}',
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    response = client.post(
        "/api/users/create",
        data='{"name":"New","email":"new@example.test","role":"visualizador","password":"synthetic-password"}',
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 201
    assert "password" not in str(response.json()).lower()
    assert "password" not in str(client.get("/api/users").json()).lower()


@pytest.mark.django_db
def test_user_http_rejects_invalid_filters_reasons_and_duplicate_email() -> None:
    _admin()
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/csrf")
    csrf = client.cookies["csrftoken"].value
    client.post(
        "/api/auth/login",
        data='{"email":"admin@example.test","password":"correct"}',
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert client.get("/api/users?active=maybe").status_code == 400
    assert client.get("/api/users?cursor=not-a-uuid").status_code == 400
    created = client.post(
        "/api/users/create",
        data='{"name":"Target","email":"target@example.test","role":"visualizador","password":"synthetic-password"}',
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    ).json()["user"]
    target_id = created["id"]
    assert (
        client.post(
            f"/api/users/{target_id}/role",
            data=f'{{"version":{created["version"]},"role":"operador"}}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 400
    )
    assert client.post(
        "/api/users/create",
        data=(
            '{"name":"Duplicate","email":" ADMIN@EXAMPLE.TEST ",'
            '"role":"visualizador","password":"synthetic-password"}'
        ),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    ).json() == {"detail": "E-mail já cadastrado."}
