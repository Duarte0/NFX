from __future__ import annotations

from datetime import timedelta

from django.db import OperationalError
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from nfx.identity.policy import Action
from nfx.identity.views import protected
from nfx.infrastructure.configuration import load_settings
from nfx.infrastructure.dependencies import dependencies_from_environment
from nfx.jobs.observability import HeartbeatService, JobObservability, OperationalHealth


@require_GET
@protected(Action.ADMINISTER_SYSTEM)
def operational(request: HttpRequest) -> JsonResponse:
    del request
    settings = load_settings()
    dependencies = dependencies_from_environment().check()
    metrics = None
    components = None
    if not {"postgres", "schema"}.intersection(dependencies.unavailable):
        try:
            metrics = JobObservability().snapshot()
            components = HeartbeatService.inspect(
                now=timezone.now(),
                timeouts={
                    "worker": timedelta(
                        seconds=settings.operational.worker_heartbeat_timeout_seconds
                    ),
                    "scheduler": timedelta(
                        seconds=settings.operational.scheduler_heartbeat_timeout_seconds
                    ),
                },
            )
        except OperationalError:
            dependencies = type(dependencies)(False, (*dependencies.unavailable, "postgres"))
    health = OperationalHealth(
        worker_timeout=timedelta(
            seconds=settings.operational.worker_heartbeat_timeout_seconds
        ),
        scheduler_timeout=timedelta(
            seconds=settings.operational.scheduler_heartbeat_timeout_seconds
        ),
        backlog_delay=timedelta(
            seconds=settings.operational.job_backlog_delay_seconds
        ),
    )
    now = timezone.now()
    result = health.evaluate(dependencies, metrics, components, now=now)
    return JsonResponse(result, status=200 if result["status"] == "ready" else 503)
