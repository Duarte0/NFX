from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from nfx.audit.services import AuditService, AuditVerifier
from nfx.identity.policy import Action
from nfx.identity.views import protected


def _integer(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


@require_GET
@protected(Action.ADMINISTER_SYSTEM)
def events(request: HttpRequest) -> JsonResponse:
    service = AuditService()
    rows, next_cursor = service.list(
        cursor=max(_integer(request.GET.get("cursor"), 0), 0),
        limit=_integer(request.GET.get("limit"), 50),
        actor_id=request.GET.get("actor_id") or None,
        action=request.GET.get("action") or None,
        entity_type=request.GET.get("entity_type") or None,
        result=request.GET.get("result") or None,
    )
    return JsonResponse(
        {
            "events": [
                {
                    "id": str(row.id),
                    "sequence": row.sequence,
                    "occurred_at": row.occurred_at.isoformat(),
                    "actor_id": str(row.actor_id) if row.actor_id else None,
                    "actor_role": row.actor_role,
                    "ip_address": row.ip_address,
                    "action": row.action,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "result": row.result,
                    "reason": row.reason,
                    "correlation_id": row.correlation_id,
                    "context": row.context,
                    "hash": row.event_hash,
                }
                for row in rows
            ],
            "next_cursor": next_cursor,
            "integrity": AuditVerifier().verify().valid,
        }
    )
