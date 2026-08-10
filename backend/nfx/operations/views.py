from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from nfx.identity.policy import Action
from nfx.identity.services import resolve_session
from nfx.identity.views import SESSION_COOKIE_NAME, protected
from nfx.operations.dashboard import InvalidDashboardParams, build_dashboard, normalize_period


@require_GET
@protected(Action.READ_DOCUMENTS)
def dashboard(request: HttpRequest) -> JsonResponse:
    try:
        period = normalize_period(request.GET)
    except InvalidDashboardParams:
        return JsonResponse({"detail": "Parâmetros de período inválidos."}, status=400)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if identity is None:
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    response = JsonResponse(build_dashboard(period=period, role=identity.role))
    response["Cache-Control"] = "no-store"
    return response
