from __future__ import annotations

import logging
import signal
from argparse import ArgumentParser
from typing import cast

from django.core.management.base import BaseCommand

from nfx.infrastructure.http import configure_logging
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
        logging.info("scheduler_started")
        run_scheduler_loop(
            JobEngine(),
            poll_interval=cast(float, options["poll_interval"]),
            should_continue=lambda: running,
        )
        logging.info("scheduler_stopped")
