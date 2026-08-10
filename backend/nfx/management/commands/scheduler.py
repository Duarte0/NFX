from __future__ import annotations

import logging
import signal
from argparse import ArgumentParser
from typing import cast
from uuid import uuid4

from django.core.management.base import BaseCommand

from nfx.collection.services import process_initial_collection_requests
from nfx.infrastructure.http import configure_logging, safe_log
from nfx.jobs.observability import HeartbeatService
from nfx.jobs.services import JobEngine, run_scheduler_loop


class Command(BaseCommand):
    help = "Runs durable job recovery without fiscal transport access."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--poll-interval", type=float, default=0.2)

    def handle(self, *args: object, **options: object) -> None:
        configure_logging()
        running = True

        def stop(*_: object) -> None:
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        process_id = f"scheduler-{uuid4()}"
        heartbeat = HeartbeatService(component="scheduler", process_id=process_id)
        safe_log(logging.getLogger(__name__), "info", "scheduler_started", process_id=process_id)
        try:
            run_scheduler_loop(
                JobEngine(),
                poll_interval=cast(float, options["poll_interval"]),
                should_continue=lambda: running,
                heartbeat=heartbeat,
                initial_processor=process_initial_collection_requests,
            )
        finally:
            try:
                heartbeat.stop()
            except Exception:
                safe_log(logging.getLogger(__name__), "warning", "scheduler_stop_unavailable")
        safe_log(logging.getLogger(__name__), "info", "scheduler_stopped", process_id=process_id)
