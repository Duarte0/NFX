from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from nfx.audit.services import AuditService
from nfx.identity.models import IdentitySession, LoginThrottle, Role, User

logger = logging.getLogger(__name__)
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
BOOTSTRAP_ADMIN_EMAIL = "guilherme.duarte@inovssc.com.br"


@dataclass(frozen=True)
class SessionIdentity:
    user_id: str
    email: str
    name: str
    role: str


class UserAdministrationError(ValueError):
    pass


class UserVersionConflict(UserAdministrationError):
    pass


class DuplicateUserEmail(UserAdministrationError):
    pass


class LastAdministrator(UserAdministrationError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def _validated_email(email: str) -> str:
    if not isinstance(email, str):
        raise UserAdministrationError("Invalid email")
    normalized = normalize_email(email)
    try:
        validate_email(normalized)
    except ValidationError as exc:
        raise UserAdministrationError("Invalid email") from exc
    return normalized


def _require_administrator(actor: SessionIdentity) -> None:
    if actor.role != Role.ADMINISTRATOR:
        raise UserAdministrationError("Administrator access required")


def _validated_reason(reason: str) -> str:
    if not isinstance(reason, str) or not reason.strip():
        raise UserAdministrationError("A reason is required")
    return reason.strip()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _subject_hash(email: str, ip_address: str) -> str:
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(
        key, f"{normalize_email(email)}\x00{ip_address}".encode(), hashlib.sha256
    ).hexdigest()


def _event(
    event: str,
    *,
    result: str,
    actor_id: str | None = None,
    actor_role: str = "",
    ip_address: str | None = None,
) -> None:
    """Authentication success is only visible after its append-only evidence persists."""
    AuditService().append(
        action=f"auth.{event}",
        entity_type="identity",
        entity_id=actor_id or "anonymous",
        result=result,
        actor_id=actor_id,
        actor_role=actor_role,
        ip_address=ip_address,
    )
    logger.info(
        "identity_event",
        extra={"event": event, "result": result, "actor_id": actor_id, "ip": ip_address},
    )


def bootstrap_first_administrator(password: str) -> tuple[User, bool]:
    """Create exactly the installation account, only while the user table is empty."""
    with transaction.atomic():
        if User.objects.exists():
            existing = User.objects.filter(email=BOOTSTRAP_ADMIN_EMAIL).first()
            if existing is None:
                raise RuntimeError("Bootstrap is only permitted on an empty user base")
            return existing, False
        user = User.objects.create(
            email=BOOTSTRAP_ADMIN_EMAIL,
            name="Guilherme Duarte",
            role=Role.ADMINISTRATOR,
            password_hash=make_password(password),
        )
        return user, True


def authenticate(
    email: str, password: str, ip_address: str, user_agent: str
) -> tuple[str | None, SessionIdentity | None]:
    """Return a token only for valid active accounts; every failure is intentionally uniform."""
    with transaction.atomic():
        now = timezone.now()
        subject_hash = _subject_hash(email, ip_address)
        throttle, _ = LoginThrottle.objects.get_or_create(
            subject_hash=subject_hash,
            defaults={"next_allowed_at": now},
        )
        if throttle.next_allowed_at > now:
            _event("login_failure", result="rate_limited", ip_address=ip_address)
            return None, None

        user = User.objects.filter(email=normalize_email(email)).first()
        valid = user is not None and user.active and check_password(password, user.password_hash)
        if not valid:
            failures = throttle.failures + 1
            delay = min(2 ** min(failures - 1, 8), 300)
            LoginThrottle.objects.filter(subject_hash=subject_hash).update(
                failures=failures, next_allowed_at=now + timedelta(seconds=delay)
            )
            _event("login_failure", result="denied", ip_address=ip_address)
            return None, None

        assert user is not None
        LoginThrottle.objects.filter(subject_hash=subject_hash).update(
            failures=0, next_allowed_at=now
        )
        token = secrets.token_urlsafe(32)
        IdentitySession.objects.create(
            token_hash=_digest(token),
            user=user,
            revocation_version=user.revocation_version,
            last_activity_at=now,
            expires_at=now + SESSION_IDLE_TIMEOUT,
            ip_address=ip_address or None,
            user_agent_hash=_digest(user_agent) if user_agent else "",
        )
        identity = SessionIdentity(str(user.id), user.email, user.name, user.role)
        _event(
            "login_success",
            result="success",
            actor_id=str(user.id),
            actor_role=user.role,
            ip_address=ip_address,
        )
        return token, identity


def resolve_session(token: str | None, *, touch: bool = True) -> SessionIdentity | None:
    if not token:
        return None
    now = timezone.now()
    token_hash = _digest(token)
    session = IdentitySession.objects.select_related("user").filter(token_hash=token_hash).first()
    if session is None or session.revoked_at is not None or not session.user.active:
        return None
    if session.expires_at <= now or session.revocation_version != session.user.revocation_version:
        IdentitySession.objects.filter(id=session.id, revoked_at__isnull=True).update(
            revoked_at=now
        )
        _event(
            "session_expired",
            result="expired",
            actor_id=str(session.user.id),
            ip_address=session.ip_address,
        )
        return None
    if touch:
        # The conditional update prevents a concurrent request from reviving an expired session.
        updated = IdentitySession.objects.filter(
            id=session.id,
            revoked_at__isnull=True,
            expires_at__gt=now,
            user__active=True,
            user__revocation_version=session.revocation_version,
        ).update(last_activity_at=now, expires_at=now + SESSION_IDLE_TIMEOUT)
        if not updated:
            return None
    return SessionIdentity(
        str(session.user.id), session.user.email, session.user.name, session.user.role
    )


def revoke_session(token: str | None) -> None:
    if not token:
        return
    now = timezone.now()
    with transaction.atomic():
        session = (
            IdentitySession.objects.select_related("user").filter(token_hash=_digest(token)).first()
        )
        if session and session.revoked_at is None:
            IdentitySession.objects.filter(id=session.id, revoked_at__isnull=True).update(
                revoked_at=now
            )
            _event(
                "logout",
                result="success",
                actor_id=str(session.user.id),
                actor_role=session.user.role,
                ip_address=session.ip_address,
            )


def _user_context(user: User) -> dict[str, object]:
    return {"name": user.name, "email": user.email, "role": user.role, "active": user.active}


def _assert_version(user: User, version: int) -> None:
    if user.version != version:
        raise UserVersionConflict("The user was changed by another request")


def _assert_not_last_administrator(user: User, *, loses_administrator: bool) -> None:
    if not loses_administrator or user.role != Role.ADMINISTRATOR or not user.active:
        return
    active_admins = list(
        User.objects.select_for_update().filter(role=Role.ADMINISTRATOR, active=True).order_by("id")
    )
    if len(active_admins) == 1 and active_admins[0].id == user.id:
        raise LastAdministrator("At least one active Administrator is required")


def _admin_event(
    action: str,
    *,
    actor: SessionIdentity,
    target: User,
    ip_address: str,
    before: dict[str, object] | None = None,
    reason: str = "",
) -> None:
    context: dict[str, object] = {"after": _user_context(target)}
    if before is not None:
        context["before"] = before
    AuditService().append(
        action=action,
        entity_type="user",
        entity_id=str(target.id),
        result="success",
        actor_id=actor.user_id,
        actor_role=actor.role,
        ip_address=ip_address,
        reason=reason,
        context=context,
    )


def create_user(
    *, actor: SessionIdentity, name: str, email: str, role: str, password: str, ip_address: str
) -> User:
    _require_administrator(actor)
    normalized_email = _validated_email(email)
    if not name.strip() or not normalized_email or not password or role not in Role.values:
        raise UserAdministrationError("Invalid user data")
    try:
        with transaction.atomic():
            user = User.objects.create(
                name=name.strip(),
                email=normalized_email,
                role=role,
                password_hash=make_password(password),
            )
            _admin_event("user.create", actor=actor, target=user, ip_address=ip_address)
            return user
    except IntegrityError as exc:
        raise DuplicateUserEmail("An account with this email already exists") from exc


def update_user(
    *, actor: SessionIdentity, user_id: str, version: int, name: str, email: str, ip_address: str
) -> User:
    _require_administrator(actor)
    normalized_email = _validated_email(email)
    if not name.strip() or not normalized_email:
        raise UserAdministrationError("Invalid user data")
    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(id=user_id)
            _assert_version(user, version)
            before = _user_context(user)
            user.name, user.email, user.version = name.strip(), normalized_email, user.version + 1
            user.save(update_fields=["name", "email", "version", "updated_at"])
            _admin_event(
                "user.update", actor=actor, target=user, ip_address=ip_address, before=before
            )
            return user
    except User.DoesNotExist as exc:
        raise UserAdministrationError("User not found") from exc
    except IntegrityError as exc:
        raise DuplicateUserEmail("An account with this email already exists") from exc


def change_user_role(
    *, actor: SessionIdentity, user_id: str, version: int, role: str, reason: str, ip_address: str
) -> User:
    _require_administrator(actor)
    if role not in Role.values:
        raise UserAdministrationError("Invalid role")
    reason = _validated_reason(reason)
    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(id=user_id)
        except User.DoesNotExist as exc:
            raise UserAdministrationError("User not found") from exc
        _assert_version(user, version)
        _assert_not_last_administrator(user, loses_administrator=role != Role.ADMINISTRATOR)
        before = _user_context(user)
        user.role, user.version = role, user.version + 1
        user.save(update_fields=["role", "version", "updated_at"])
        _admin_event(
            "user.role_change",
            actor=actor,
            target=user,
            ip_address=ip_address,
            before=before,
            reason=reason,
        )
        return user


def reset_user_password(
    *,
    actor: SessionIdentity,
    user_id: str,
    version: int,
    password: str,
    reason: str,
    ip_address: str,
) -> User:
    _require_administrator(actor)
    if not password:
        raise UserAdministrationError("Invalid password")
    reason = _validated_reason(reason)
    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(id=user_id)
        except User.DoesNotExist as exc:
            raise UserAdministrationError("User not found") from exc
        _assert_version(user, version)
        before = _user_context(user)
        user.password_hash, user.revocation_version, user.version = (
            make_password(password),
            user.revocation_version + 1,
            user.version + 1,
        )
        user.save(update_fields=["password_hash", "revocation_version", "version", "updated_at"])
        _admin_event(
            "user.password_reset",
            actor=actor,
            target=user,
            ip_address=ip_address,
            before=before,
            reason=reason,
        )
        return user


def change_own_password(
    *, actor: SessionIdentity, current_password: str, password: str, ip_address: str
) -> None:
    if not isinstance(current_password, str) or not isinstance(password, str) or not password:
        raise UserAdministrationError("Invalid password")
    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(id=actor.user_id, active=True)
        except User.DoesNotExist as exc:
            raise UserAdministrationError("User not found") from exc
        if not check_password(current_password, user.password_hash):
            raise UserAdministrationError("Invalid current password")
        before = _user_context(user)
        user.password_hash = make_password(password)
        user.revocation_version += 1
        user.version += 1
        user.save(update_fields=["password_hash", "revocation_version", "version", "updated_at"])
        _admin_event(
            "user.password_change", actor=actor, target=user, ip_address=ip_address, before=before
        )


def set_user_active(
    *,
    actor: SessionIdentity,
    user_id: str,
    version: int,
    active: bool,
    reason: str,
    ip_address: str,
) -> User:
    _require_administrator(actor)
    if not isinstance(active, bool):
        raise UserAdministrationError("Invalid state")
    if not active:
        reason = _validated_reason(reason)
    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(id=user_id)
        except User.DoesNotExist as exc:
            raise UserAdministrationError("User not found") from exc
        _assert_version(user, version)
        _assert_not_last_administrator(user, loses_administrator=not active)
        before = _user_context(user)
        user.active, user.version = active, user.version + 1
        if not active:
            user.revocation_version += 1
        user.save(update_fields=["active", "revocation_version", "version", "updated_at"])
        _admin_event(
            "user.activate" if active else "user.deactivate",
            actor=actor,
            target=user,
            ip_address=ip_address,
            before=before,
            reason=reason,
        )
        return user


def require_authorized(
    identity: SessionIdentity | None, action: str, owner_id: str | None = None
) -> bool:
    from nfx.identity.policy import Action, authorize

    try:
        requested = Action(action)
    except ValueError:
        return False
    return identity is not None and authorize(
        identity.role, requested, owner_id=owner_id, actor_id=identity.user_id
    )
