from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path

from nfx.audit import views as audit_views
from nfx.identity import views as identity_views
from nfx.infrastructure.dependencies import dependencies_from_environment


def index(_: HttpRequest) -> HttpResponse:
    return HttpResponse("NFX INOV foundation", content_type="text/plain; charset=utf-8")


def live(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "live"})


def ready(_: HttpRequest) -> JsonResponse:
    result = dependencies_from_environment().check()
    status = 200 if result.ready else 503
    return JsonResponse({"status": "ready" if result.ready else "unavailable"}, status=status)


urlpatterns = [
    path("", index),
    path("health/live", live),
    path("health/ready", ready),
    path("api/auth/csrf", identity_views.csrf),
    path("api/auth/login", identity_views.login),
    path("api/auth/logout", identity_views.logout),
    path("api/auth/session", identity_views.session),
    path("api/audit/events", audit_views.events),
]
