from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from nfx.backup.models import BackupSet
from nfx.backup.services import BackupService
from nfx.identity.policy import Action
from nfx.identity.views import protected


@require_GET
@protected(Action.ADMINISTER_SYSTEM)
def status(request: HttpRequest) -> JsonResponse:
    del request
    return JsonResponse(BackupService().status())


@require_GET
@protected(Action.ADMINISTER_SYSTEM)
def backups(request: HttpRequest) -> JsonResponse:
    del request
    rows = BackupSet.objects.exclude(state="expired").order_by("-started_at", "-id")[:100]
    return JsonResponse(
        {
            "backups": [
                {
                    "id": str(row.id),
                    "kind": row.kind,
                    "state": row.state,
                    "version": row.version,
                    "started_at": row.started_at.isoformat(),
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "size_bytes": row.size_bytes,
                    "manifest_hash": row.manifest_hash,
                    "safe_error": row.safe_error,
                }
                for row in rows
            ],
            "status": BackupService().status(),
        }
    )
