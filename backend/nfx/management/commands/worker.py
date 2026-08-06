from __future__ import annotations

import logging
import signal
import time

from django.core.management.base import BaseCommand

from nfx.infrastructure.http import configure_logging


class Command(BaseCommand):
    help = "Runs the empty P0 worker loop; it deliberately schedules no fiscal work."

    def handle(self, *args: object, **options: object) -> None:
        configure_logging()
        running = True

        def stop(*_: object) -> None:
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        logging.info("worker_started_no_jobs")
        while running:
            time.sleep(0.2)
        logging.info("worker_stopped")
