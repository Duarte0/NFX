from __future__ import annotations

import json
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from nfx.identity.policy import Action
from nfx.identity.services import authenticate, require_authorized, resolve_session, revoke_session

SESSION_COOKIE_NAME = "nfx_session"
INVALID_CREDENTIALS = {"detail": "Credenciais inválidas."}


def _json_body(request: HttpRequest) -> dict[str, object] | None:
    try:
        body = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return body if isinstance(body, dict) else None


def _request_ip(request: HttpRequest) -> str:
    return str(request.META.get("REMOTE_ADDR", ""))


@require_GET
@ensure_csrf_cookie
def csrf(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"detail": "CSRF pronto."})


@require_POST
def login(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    email = body.get("email") if body else None
    password = body.get("password") if body else None
    if not isinstance(email, str) or not isinstance(password, str):
        return JsonResponse(INVALID_CREDENTIALS, status=401)
    token, identity = authenticate(email, password, _request_ip(request), request.headers.get("User-Agent", ""))
    if token is None or identity is None:
        return JsonResponse(INVALID_CREDENTIALS, status=401)
    response = JsonResponse({"user": {"id": identity.user_id, "name": identity.name, "role": identity.role}})
    response.set_cookie(SESSION_COOKIE_NAME, token, secure=True, httponly=True, samesite="Lax", path="/api/")
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def logout(request: HttpRequest) -> JsonResponse:
    revoke_session(request.COOKIES.get(SESSION_COOKIE_NAME))
    response = JsonResponse({"detail": "Sessão encerrada."})
    response.delete_cookie(SESSION_COOKIE_NAME, path="/api/", samesite="Lax")
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def session(request: HttpRequest) -> JsonResponse:
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME))
    if identity is None:
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    response = JsonResponse({"user": {"id": identity.user_id, "name": identity.name, "role": identity.role}})
    response["Cache-Control"] = "no-store"
    return response


def protected(action: Action, *, owner_id: Callable[[HttpRequest], str | None] | None = None) -> Callable[[Callable[[HttpRequest], HttpResponse]], Callable[[HttpRequest], HttpResponse]]:
    def decorator(view: Callable[[HttpRequest], HttpResponse]) -> Callable[[HttpRequest], HttpResponse]:
        def wrapped(request: HttpRequest) -> HttpResponse:
            identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME))
            if not require_authorized(identity, action.value, owner_id(request) if owner_id else None):
                return JsonResponse({"detail": "Acesso negado."}, status=403)
            return view(request)

        return wrapped

    return decorator
