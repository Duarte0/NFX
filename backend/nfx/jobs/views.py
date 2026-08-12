from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from nfx.identity.policy import Action
from nfx.identity.views import protected
from nfx.jobs.observability import (
    InvalidJobObservabilityQuery,
    list_job_observability_summaries,
    normalize_job_observability_query,
)


@require_GET
@protected(Action.READ_DOCUMENTS)
def observability(request: HttpRequest) -> JsonResponse:
    try:
        selected = normalize_job_observability_query(request.GET)
    except InvalidJobObservabilityQuery:
        return JsonResponse({"detail": "Parâmetros de jobs inválidos."}, status=400)
    try:
        payload = list_job_observability_summaries(selected)
    except Exception:
        return JsonResponse(
            {"detail": "Não foi possível consultar os jobs de processamento."}, status=503
        )
    response = JsonResponse(payload)
    response["Cache-Control"] = "no-store"
    return response
