from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
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


def normalize_email(email: str) -> str:
    return email.strip().casefold()


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
