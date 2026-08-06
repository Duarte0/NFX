from __future__ import annotations

import json
from collections.abc import Callable
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from nfx.identity.policy import Action
from nfx.identity.services import (
    DuplicateUserEmail,
    LastAdministrator,
    UserAdministrationError,
    UserVersionConflict,
    authenticate,
    change_own_password,
    change_user_role,
    create_user,
    require_authorized,
    reset_user_password,
    resolve_session,
    revoke_session,
    set_user_active,
    update_user,
)

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


def _user_payload(user: object) -> dict[str, object]:
    from nfx.identity.models import User

    assert isinstance(user, User)
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "version": user.version,
    }


def _integer(body: dict[str, object], name: str) -> int | None:
    value = body.get(name)
    return value if isinstance(value, int) and value > 0 else None


def _admin_error(exc: Exception) -> JsonResponse:
    if isinstance(exc, DuplicateUserEmail):
        return JsonResponse({"detail": "E-mail já cadastrado."}, status=409)
    if isinstance(exc, UserVersionConflict):
        return JsonResponse({"detail": "Usuário alterado por outra solicitação."}, status=409)
    if isinstance(exc, LastAdministrator):
        return JsonResponse({"detail": "É necessário manter um Administrador ativo."}, status=409)
    return JsonResponse({"detail": "Não foi possível concluir a operação."}, status=400)


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
    token, identity = authenticate(
        email, password, _request_ip(request), request.headers.get("User-Agent", "")
    )
    if token is None or identity is None:
        return JsonResponse(INVALID_CREDENTIALS, status=401)
    response = JsonResponse(
        {"user": {"id": identity.user_id, "name": identity.name, "role": identity.role}}
    )
    response.set_cookie(
        SESSION_COOKIE_NAME, token, secure=True, httponly=True, samesite="Lax", path="/api/"
    )
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
    response = JsonResponse(
        {"user": {"id": identity.user_id, "name": identity.name, "role": identity.role}}
    )
    response["Cache-Control"] = "no-store"
    return response


def protected(
    action: Action, *, owner_id: Callable[[HttpRequest], str | None] | None = None
) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    def decorator(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
            identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME))
            if not require_authorized(
                identity, action.value, owner_id(request) if owner_id else None
            ):
                return JsonResponse({"detail": "Acesso negado."}, status=403)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


@require_GET
@protected(Action.ADMINISTER_USERS)
def users(request: HttpRequest) -> JsonResponse:
    from nfx.identity.models import Role, User

    active = request.GET.get("active")
    role = request.GET.get("role")
    try:
        limit = min(max(int(request.GET.get("limit", "50")), 1), 100)
        cursor = request.GET.get("cursor", "")
    except ValueError:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    queryset = User.objects.order_by("id")
    if active not in {None, "true", "false"}:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    if active in {"true", "false"}:
        queryset = queryset.filter(active=active == "true")
    if role:
        if role not in Role.values:
            return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
        queryset = queryset.filter(role=role)
    if cursor:
        try:
            cursor_id = UUID(cursor)
        except ValueError:
            return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
        queryset = queryset.filter(id__gt=cursor_id)
    rows = list(queryset[: limit + 1])
    return JsonResponse(
        {
            "users": [_user_payload(row) for row in rows[:limit]],
            "next_cursor": str(rows[limit].id) if len(rows) > limit else None,
        }
    )


@require_POST
@protected(Action.ADMINISTER_USERS)
def user_create(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    if body is None or identity is None:
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    required = ("name", "email", "role", "password")
    if any(not isinstance(body.get(field), str) for field in required):
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    try:
        user = create_user(
            actor=identity,
            name=str(body["name"]),
            email=str(body["email"]),
            role=str(body["role"]),
            password=str(body["password"]),
            ip_address=_request_ip(request),
        )
    except UserAdministrationError as exc:
        return _admin_error(exc)
    return JsonResponse({"user": _user_payload(user)}, status=201)


@require_http_methods(["PATCH"])
@protected(Action.ADMINISTER_USERS)
def user_update(request: HttpRequest, user_id: str) -> JsonResponse:
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    version = _integer(body or {}, "version")
    if (
        body is None
        or identity is None
        or version is None
        or not isinstance(body.get("name"), str)
        or not isinstance(body.get("email"), str)
    ):
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    try:
        user = update_user(
            actor=identity,
            user_id=user_id,
            version=version,
            name=str(body["name"]),
            email=str(body["email"]),
            ip_address=_request_ip(request),
        )
    except (UserAdministrationError, ValueError) as exc:
        return _admin_error(exc)
    return JsonResponse({"user": _user_payload(user)})


def _admin_action(request: HttpRequest, user_id: str, operation: str) -> JsonResponse:
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    version = _integer(body or {}, "version")
    reason = body.get("reason") if body else None
    reason_value = reason if isinstance(reason, str) else ""
    if body is None or identity is None or version is None:
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    try:
        if operation == "role":
            role = body.get("role")
            if not isinstance(role, str):
                raise UserAdministrationError("Invalid role")
            user = change_user_role(
                actor=identity,
                user_id=user_id,
                version=version,
                role=role,
                reason=reason_value,
                ip_address=_request_ip(request),
            )
        elif operation == "password":
            password = body.get("password")
            if not isinstance(password, str):
                raise UserAdministrationError("Invalid password")
            user = reset_user_password(
                actor=identity,
                user_id=user_id,
                version=version,
                password=password,
                reason=reason_value,
                ip_address=_request_ip(request),
            )
        else:
            active = body.get("active")
            if not isinstance(active, bool) or (not active and not isinstance(reason, str)):
                raise UserAdministrationError("Invalid state")
            user = set_user_active(
                actor=identity,
                user_id=user_id,
                version=version,
                active=active,
                reason=reason if isinstance(reason, str) else "",
                ip_address=_request_ip(request),
            )
    except (UserAdministrationError, ValueError) as exc:
        return _admin_error(exc)
    return JsonResponse({"user": _user_payload(user)})


@require_POST
@protected(Action.ADMINISTER_USERS)
def user_role(request: HttpRequest, user_id: str) -> JsonResponse:
    return _admin_action(request, user_id, "role")


@require_POST
@protected(Action.ADMINISTER_USERS)
def user_password_reset(request: HttpRequest, user_id: str) -> JsonResponse:
    return _admin_action(request, user_id, "password")


@require_POST
@protected(Action.CHANGE_OWN_PASSWORD)
def user_password_change(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    identity = resolve_session(request.COOKIES.get(SESSION_COOKIE_NAME), touch=False)
    current_password = body.get("current_password") if body else None
    password = body.get("password") if body else None
    if identity is None or not isinstance(current_password, str) or not isinstance(password, str):
        return JsonResponse({"detail": "Dados inválidos."}, status=400)
    try:
        change_own_password(
            actor=identity,
            current_password=current_password,
            password=password,
            ip_address=_request_ip(request),
        )
    except UserAdministrationError:
        return JsonResponse({"detail": "Não foi possível alterar a senha."}, status=400)
    return JsonResponse({"detail": "Senha alterada."})


@require_POST
@protected(Action.ADMINISTER_USERS)
def user_active(request: HttpRequest, user_id: str) -> JsonResponse:
    return _admin_action(request, user_id, "active")
