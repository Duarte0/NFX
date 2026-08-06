from __future__ import annotations

import time
from urllib.request import urlopen


def request(path: str) -> tuple[int, str]:
    with urlopen(f"http://web:8000{path}", timeout=2) as response:  # noqa: S310 - internal Compose host
        return response.status, response.read().decode("utf-8")


for _ in range(30):
    try:
        status, body = request("/health/live")
        if status == 200 and '"live"' in body:
            break
    except OSError:
        time.sleep(0.2)
else:
    raise SystemExit("web liveness did not become available")

status, body = request("/health/ready")
if status != 200 or '"ready"' not in body:
    raise SystemExit("web readiness did not become available")
