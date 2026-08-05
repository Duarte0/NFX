from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from nfx.identity.models import IdentitySession, LoginThrottle, Role, User
from nfx.identity.policy import Action, authorize
from nfx.identity.services import (
    BOOTSTRAP_ADMIN_EMAIL,
    SESSION_IDLE_TIMEOUT,
    authenticate,
    bootstrap_first_administrator,
    resolve_session,
    revoke_session,
)


@pytest.mark.django_db
def test_bootstrap_is_idempotent_argon2_and_never_replaces_the_password() -> None:
    user, created = bootstrap_first_administrator("synthetic-bootstrap-password")
    unchanged, rerun_created = bootstrap_first_administrator("different-synthetic-password")

    assert created and not rerun_created
    assert user.id == unchanged.id
    assert user.email == BOOTSTRAP_ADMIN_EMAIL
    assert user.password_hash.startswith("argon2$")
    assert check_password("synthetic-bootstrap-password", user.password_hash)
    assert not check_password("different-synthetic-password", user.password_hash)


@pytest.mark.django_db
def test_bootstrap_refuses_to_add_itself_to_an_existing_user_base() -> None:
    User.objects.create(
        email="synthetic@example.test", name="Synthetic", role=Role.VIEWER, password_hash=make_password("x")
    )
    with pytest.raises(RuntimeError):
        bootstrap_first_administrator("synthetic-bootstrap-password")


@pytest.mark.django_db
def test_bootstrap_command_reads_external_secret_without_echoing_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "synthetic-command-password"
    monkeypatch.setenv("NFX_BOOTSTRAP_ADMIN_PASSWORD", secret)
    call_command("bootstrap_admin")
    first_output = capsys.readouterr().out
    call_command("bootstrap_admin")
    second_output = capsys.readouterr().out

    assert secret not in first_output + second_output
    assert "created" in first_output.lower()
    assert "unchanged" in second_output.lower()


@pytest.mark.django_db
def test_invalid_and_unknown_login_have_the_same_response_and_throttle() -> None:
    User.objects.create(
        email="active@example.test", name="Active", role=Role.VIEWER, password_hash=make_password("correct")
    )
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/csrf")
    csrf = client.cookies["csrftoken"].value
    known = client.post("/api/auth/login", data='{"email":"active@example.test","password":"wrong"}', content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    unknown = client.post("/api/auth/login", data='{"email":"missing@example.test","password":"wrong"}', content_type="application/json", HTTP_X_CSRFTOKEN=csrf)

    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json()) == (401, {"detail": "Credenciais inválidas."})
    assert LoginThrottle.objects.count() == 2


@pytest.mark.django_db
def test_login_requires_csrf_and_sets_only_a_secure_opaque_cookie() -> None:
    User.objects.create(
        email="active@example.test", name="Active", role=Role.OPERATOR, password_hash=make_password("correct")
    )
    client = Client(enforce_csrf_checks=True)
    rejected = client.post("/api/auth/login", data='{}', content_type="application/json")
    client.get("/api/auth/csrf")
    accepted = client.post("/api/auth/login", data='{"email":"active@example.test","password":"correct"}', content_type="application/json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)

    assert rejected.status_code == 403
    cookie = accepted.cookies["nfx_session"]
    assert cookie["secure"] and cookie["httponly"] and cookie["samesite"] == "Lax" and cookie["path"] == "/api/"
    assert IdentitySession.objects.get().token_hash != cookie.value


@pytest.mark.django_db
def test_session_timeout_boundary_revocation_and_no_expiry_resurrection(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User.objects.create(
        email="active@example.test", name="Active", role=Role.VIEWER, password_hash=make_password("correct")
    )
    start = timezone.now()
    monkeypatch.setattr("nfx.identity.services.timezone.now", lambda: start)
    token, _ = authenticate(user.email, "correct", "127.0.0.1", "test")
    assert token
    monkeypatch.setattr("nfx.identity.services.timezone.now", lambda: start + SESSION_IDLE_TIMEOUT - timedelta(seconds=1))
    assert resolve_session(token) is not None
    session = IdentitySession.objects.get()
    expiry = session.expires_at
    monkeypatch.setattr("nfx.identity.services.timezone.now", lambda: expiry)
    assert resolve_session(token) is None
    session.refresh_from_db()
    assert session.revoked_at == expiry
    assert session.expires_at == expiry
    revoke_session(token)
    assert resolve_session(token) is None


@pytest.mark.django_db
def test_only_active_users_authenticate_and_revoked_version_invalidates_sessions() -> None:
    user = User.objects.create(
        email="inactive@example.test", name="Inactive", role=Role.VIEWER, password_hash=make_password("correct"), active=False
    )
    token, identity = authenticate(user.email, "correct", "127.0.0.1", "test")
    assert token is identity is None
    user.active = True
    user.save()
    LoginThrottle.objects.all().update(next_allowed_at=timezone.now())
    token, _ = authenticate(user.email, "correct", "127.0.0.1", "test")
    assert token
    user.revocation_version += 1
    user.save(update_fields=["revocation_version"])
    assert resolve_session(token) is None


@pytest.mark.parametrize(
    ("role", "action", "allowed"),
    [
        (Role.ADMINISTRATOR, Action.ADMINISTER_SYSTEM, True),
        (Role.OPERATOR, Action.ADMINISTER_COMPANIES, True),
        (Role.OPERATOR, Action.ADMINISTER_USERS, False),
        (Role.VIEWER, Action.READ_DOCUMENTS, True),
        (Role.VIEWER, Action.ADMINISTER_CERTIFICATES, False),
        (Role.VIEWER, Action.DOWNLOAD_OWN_ZIP, True),
    ],
)
def test_rbac_matrix_is_central_and_fails_closed(role: str, action: Action, allowed: bool) -> None:
    assert authorize(role, action, owner_id="owner", actor_id="owner") is allowed
    if role != Role.ADMINISTRATOR:
        assert not authorize(role, Action.DOWNLOAD_OWN_ZIP, owner_id="another", actor_id="owner")
