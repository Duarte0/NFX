from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path

from nfx.audit import views as audit_views
from nfx.certificates import views as certificate_views
from nfx.collection import views as collection_views
from nfx.companies import views as company_views
from nfx.identity import views as identity_views
from nfx.infrastructure.dependencies import dependencies_from_environment
from nfx.infrastructure.health import operational


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
    path("health/operational", operational),
    path("api/auth/csrf", identity_views.csrf),
    path("api/auth/login", identity_views.login),
    path("api/auth/logout", identity_views.logout),
    path("api/auth/session", identity_views.session),
    path("api/users", identity_views.users),
    path("api/users/create", identity_views.user_create),
    path("api/users/<uuid:user_id>", identity_views.user_update),
    path("api/users/<uuid:user_id>/role", identity_views.user_role),
    path("api/users/<uuid:user_id>/password-reset", identity_views.user_password_reset),
    path("api/users/password", identity_views.user_password_change),
    path("api/users/<uuid:user_id>/active", identity_views.user_active),
    path("api/audit/events", audit_views.events),
    path("api/collections", collection_views.collections),
    path("api/companies", company_views.companies),
    path("api/companies/create", company_views.company_create),
    path("api/companies/<uuid:company_id>", company_views.company_detail),
    path("api/companies/<uuid:company_id>/activate", company_views.company_activate),
    path("api/companies/<uuid:company_id>/deactivate", company_views.company_deactivate),
    path("api/companies/<uuid:company_id>/flows/<str:family>", company_views.company_flow),
    path("api/companies/<uuid:company_id>/enrichment", company_views.company_enrichment),
    path("api/companies/<uuid:company_id>/collection", collection_views.status),
    path("api/companies/<uuid:company_id>/collection/request", collection_views.request),
    path(
        "api/companies/<uuid:company_id>/collection/retry/<uuid:execution_id>",
        collection_views.retry,
    ),
    path("api/companies/<uuid:company_id>/certificate", certificate_views.certificate_detail),
    path(
        "api/companies/<uuid:company_id>/certificate/upload", certificate_views.certificate_upload
    ),
]
