from mimetypes import guess_type
from pathlib import Path

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path

from nfx.audit import views as audit_views
from nfx.backup import views as backup_views
from nfx.certificates import views as certificate_views
from nfx.collection import views as collection_views
from nfx.companies import views as company_views
from nfx.documents import views as document_views
from nfx.exports import views as export_views
from nfx.identity import views as identity_views
from nfx.infrastructure.dependencies import dependencies_from_environment
from nfx.infrastructure.health import operational
from nfx.jobs import views as job_views
from nfx.operations.views import dashboard
from nfx.retention import views as retention_views

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _fixed_distribution_root() -> Path | None:
    try:
        resolved = FRONTEND_DIST.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if resolved != FRONTEND_DIST or not resolved.is_dir():
        return None
    return resolved


def _resolved_regular_file(root: Path, candidate: Path) -> Path | None:
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if root not in resolved.parents or not resolved.is_file():
        return None
    return resolved


def _read_file(root: Path, candidate: Path) -> tuple[Path, bytes] | None:
    resolved = _resolved_regular_file(root, candidate)
    if resolved is None:
        return None
    try:
        return resolved, resolved.read_bytes()
    except OSError:
        return None


def index(_: HttpRequest) -> HttpResponse:
    distribution = _fixed_distribution_root()
    build = _read_file(distribution, distribution / "index.html") if distribution else None

    if build is None:
        return HttpResponse(
            "Frontend build não encontrado.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    return HttpResponse(
        build[1],
        content_type="text/html; charset=utf-8",
    )


def frontend_asset(_request: HttpRequest, asset_path: str) -> HttpResponse:
    path_parts = asset_path.split("/")
    if (
        not asset_path
        or "\\" in asset_path
        or "\x00" in asset_path
        or any(part in {"", ".", ".."} for part in path_parts)
        or path_parts[0] == "assets"
    ):
        return HttpResponse(status=404)

    distribution = _fixed_distribution_root()
    if distribution is None:
        return HttpResponse(status=404)

    assets_root = distribution / "assets"
    try:
        resolved_assets_root = assets_root.resolve(strict=True)
    except (OSError, RuntimeError):
        return HttpResponse(status=404)
    if resolved_assets_root != assets_root or not resolved_assets_root.is_dir():
        return HttpResponse(status=404)

    asset = _read_file(assets_root, assets_root / asset_path)
    if asset is None:
        return HttpResponse(status=404)

    content_type, _ = guess_type(asset[0].name)

    return HttpResponse(
        asset[1],
        content_type=content_type or "application/octet-stream",
    )


def live(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "live"})


def ready(_: HttpRequest) -> JsonResponse:
    result = dependencies_from_environment().check()
    status = 200 if result.ready else 503
    return JsonResponse({"status": "ready" if result.ready else "unavailable"}, status=status)


urlpatterns = [
    path("", index),
    path("assets/<path:asset_path>", frontend_asset),
    path("health/live", live),
    path("health/ready", ready),
    path("health/operational", operational),
    path("api/dashboard", dashboard),
    path("api/jobs/observability", job_views.observability),
    path("api/backups/status", backup_views.status),
    path("api/backups", backup_views.backups),
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
    path("api/collections/executions", collection_views.execution_list),
    path("api/collections", collection_views.collections),
    path("api/documents", document_views.documents),
    path("api/documents/<uuid:document_id>", document_views.detail),
    path("api/documents/<uuid:document_id>/download", document_views.download_document),
    path("api/documents/<uuid:document_id>/pdf/render", document_views.request_pdf),
    path("api/documents/<uuid:document_id>/pdf", document_views.download_pdf),
    path("api/artifacts/<uuid:artifact_id>/download", document_views.download_artifact),
    path("api/exports", export_views.exports),
    path("api/exports/<uuid:export_id>", export_views.detail),
    path("api/exports/<uuid:export_id>/download", export_views.download),
    path("api/exports/cleanup", export_views.cleanup),
    path("api/retention/documents", retention_views.documents),
    path("api/retention/documents/<uuid:document_id>", retention_views.detail),
    path("api/retention/documents/<uuid:document_id>/preview", retention_views.preview),
    path("api/retention/documents/<uuid:document_id>/deletion", retention_views.request),
    path("api/retention/deletions/<uuid:operation_id>", retention_views.deletion_status),
    path("api/retention/deletions/<uuid:operation_id>/resume", retention_views.resume),
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
    path("api/certificates/inventory", certificate_views.certificate_inventory),
    path(
        "api/companies/<uuid:company_id>/certificate/upload", certificate_views.certificate_upload
    ),
]
