from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from nfx.audit.models import AuditChain, AuditEvent
from nfx.infrastructure.redaction import redact

GENESIS_HASH = "0" * 64
REQUIRES_REASON = frozenset(
    {
        "user.deactivate",
        "company.deactivate",
        "user.password_reset",
        "user.role_change",
        "document.delete",
    }
)


class AuditUnavailable(RuntimeError):
    """A critical operation must not report success when its audit event cannot persist."""


class MissingAuditReason(ValueError):
    pass


@dataclass(frozen=True)
class IntegrityReport:
    valid: bool
    checked: int
    issue: str | None = None
    sequence: int | None = None


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _event_payload(
    *,
    sequence: int,
    occurred_at: datetime,
    actor_id: UUID | None,
    actor_role: str,
    ip_address: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    result: str,
    reason: str,
    correlation_id: str,
    context: object,
    previous_hash: str,
) -> dict[str, object]:
    return {
        "v": 1,
        "sequence": sequence,
        "occurred_at": occurred_at.isoformat(),
        "actor_id": str(actor_id) if actor_id else None,
        "actor_role": actor_role,
        "ip_address": ip_address,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "result": result,
        "reason": reason,
        "correlation_id": correlation_id,
        "context": context,
        "previous_hash": previous_hash,
    }


def event_hash(**fields: object) -> str:
    """Stable audit-v1 vector: SHA-256 of canonical event fields including the previous hash."""
    return hashlib.sha256(_canonical(fields).encode("utf-8")).hexdigest()


class AuditService:
    def append(
        self,
        *,
        action: str,
        entity_type: str,
        result: str,
        actor_id: UUID | str | None = None,
        actor_role: str = "",
        ip_address: str | None = None,
        entity_id: str = "",
        reason: str = "",
        correlation_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> AuditEvent:
        if action in REQUIRES_REASON and not reason.strip():
            raise MissingAuditReason(f"A reason is required for {action}")
        safe_context = redact(context or {})
        parsed_actor_id = UUID(str(actor_id)) if actor_id else None
        try:
            with transaction.atomic():
                # Transactional test database flushes (and disaster recovery) may remove
                # migration seed data; recreate the singleton safely before locking it.
                AuditChain.objects.get_or_create(stream="global")
                chain = AuditChain.objects.select_for_update().get(stream="global")
                occurred_at = timezone.now()
                sequence = chain.last_sequence + 1
                payload = _event_payload(
                    sequence=sequence,
                    occurred_at=occurred_at,
                    actor_id=parsed_actor_id,
                    actor_role=actor_role,
                    ip_address=ip_address or None,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    result=result,
                    reason=reason.strip(),
                    correlation_id=correlation_id,
                    context=safe_context,
                    previous_hash=chain.last_hash,
                )
                digest = event_hash(**payload)
                event = AuditEvent.objects.create(
                    sequence=sequence,
                    occurred_at=occurred_at,
                    actor_id=parsed_actor_id,
                    actor_role=actor_role,
                    ip_address=ip_address or None,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    result=result,
                    reason=reason.strip(),
                    correlation_id=correlation_id,
                    context=safe_context,
                    previous_hash=chain.last_hash,
                    event_hash=digest,
                )
                AuditChain.objects.filter(
                    stream="global", last_sequence=chain.last_sequence
                ).update(last_sequence=sequence, last_hash=digest)
                return event
        except MissingAuditReason:
            raise
        except Exception as exc:
            raise AuditUnavailable("Audit trail is temporarily unavailable") from exc

    def list(
        self,
        *,
        cursor: int = 0,
        limit: int = 50,
        actor_id: str | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        result: str | None = None,
    ) -> tuple[list[AuditEvent], int | None]:
        limit = min(max(limit, 1), 100)
        events = AuditEvent.objects.filter(sequence__gt=cursor)
        if actor_id:
            events = events.filter(actor_id=actor_id)
        if action:
            events = events.filter(action=action)
        if entity_type:
            events = events.filter(entity_type=entity_type)
        if result:
            events = events.filter(result=result)
        rows = list(events[: limit + 1])
        next_cursor = rows[limit].sequence if len(rows) > limit else None
        return rows[:limit], next_cursor


class AuditVerifier:
    def verify(self, events: list[AuditEvent] | None = None) -> IntegrityReport:
        rows = events if events is not None else list(AuditEvent.objects.all())
        previous_hash = GENESIS_HASH
        expected_sequence = 1
        for row in rows:
            if row.sequence != expected_sequence:
                return IntegrityReport(False, expected_sequence - 1, "sequence", row.sequence)
            payload = _event_payload(
                sequence=row.sequence,
                occurred_at=row.occurred_at,
                actor_id=row.actor_id,
                actor_role=row.actor_role,
                ip_address=row.ip_address,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                result=row.result,
                reason=row.reason,
                correlation_id=row.correlation_id,
                context=row.context,
                previous_hash=previous_hash,
            )
            if row.previous_hash != previous_hash or row.event_hash != event_hash(**payload):
                return IntegrityReport(False, expected_sequence - 1, "hash", row.sequence)
            previous_hash = row.event_hash
            expected_sequence += 1
        return IntegrityReport(True, len(rows))
