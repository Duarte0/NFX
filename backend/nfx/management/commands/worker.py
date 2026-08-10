from __future__ import annotations

import logging
import signal
from argparse import ArgumentParser
from datetime import timedelta
from typing import cast
from uuid import uuid4

from django.core.management.base import BaseCommand

from nfx.collection.services import ensure_collection_handler
from nfx.infrastructure.http import configure_logging, safe_log
from nfx.jobs.observability import HeartbeatService
from nfx.jobs.services import JobEngine, run_worker_loop


class Command(BaseCommand):
    help = "Runs the durable job worker without fiscal transport access."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--poll-interval", type=float, default=0.2)
        parser.add_argument("--lease-seconds", type=int, default=30)

    def handle(self, *args: object, **options: object) -> None:
        configure_logging()
        ensure_collection_handler()
        running = True

        def stop(*_: object) -> None:
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        owner = f"worker-{uuid4()}"
        heartbeat = HeartbeatService(component="worker", process_id=owner)
        safe_log(logging.getLogger(__name__), "info", "worker_started", process_id=owner)
        try:
            run_worker_loop(
                JobEngine(lease_duration=timedelta(seconds=cast(int, options["lease_seconds"]))),
                owner=owner,
                poll_interval=cast(float, options["poll_interval"]),
                should_continue=lambda: running,
                heartbeat=heartbeat,
            )
        finally:
            try:
                heartbeat.stop()
            except Exception:
                safe_log(logging.getLogger(__name__), "warning", "worker_stop_unavailable")
        safe_log(logging.getLogger(__name__), "info", "worker_stopped", process_id=owner)
