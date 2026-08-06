from __future__ import annotations

import logging
import signal
from argparse import ArgumentParser
from datetime import timedelta
from typing import cast

from django.core.management.base import BaseCommand

from nfx.infrastructure.http import configure_logging
from nfx.jobs.services import JobEngine, run_worker_loop


class Command(BaseCommand):
    help = "Runs the durable job worker without fiscal transport access."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--poll-interval", type=float, default=0.2)
        parser.add_argument("--lease-seconds", type=int, default=30)

    def handle(self, *args: object, **options: object) -> None:
        configure_logging()
        running = True

        def stop(*_: object) -> None:
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        logging.info("worker_started")
        run_worker_loop(
            JobEngine(lease_duration=timedelta(seconds=cast(int, options["lease_seconds"]))),
            poll_interval=cast(float, options["poll_interval"]),
            should_continue=lambda: running,
        )
        logging.info("worker_stopped")
