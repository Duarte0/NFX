#!/usr/bin/env bash
set -euo pipefail

run_id="smoke-$(date +%s)-$$"
project="nfx-p0-test-${run_id}"
bucket="nfx-p0-test-${run_id}"
compose=(docker compose -p "$project" -f docker-compose.test.yml)
cleanup() {
  kill "${web_pid:-}" "${worker_pid:-}" "${scheduler_pid:-}" 2>/dev/null || true
  wait "${web_pid:-}" "${worker_pid:-}" "${scheduler_pid:-}" 2>/dev/null || true
  "${compose[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
"${compose[@]}" up -d --wait postgres minio
MINIO_BUCKET="$bucket" "${compose[@]}" run --rm minio-init
MINIO_BUCKET="$bucket" TEST_RUN_ID="$run_id" "${compose[@]}" run --no-deps --rm test-runner python backend/manage.py nfx_migrate
MINIO_BUCKET="$bucket" "${compose[@]}" up -d web worker scheduler
for _ in $(seq 1 30); do
  if "${compose[@]}" exec -T web python -c 'from urllib.request import urlopen; assert urlopen("http://127.0.0.1:8000/health/live").status == 200' >/dev/null 2>&1; then break; fi
  sleep 0.2
done
"${compose[@]}" exec -T web python - <<'PY'
from http.client import HTTPConnection
from mimetypes import guess_type
from pathlib import Path
import re


def request(path: str) -> tuple[int, str, bytes]:
    connection = HTTPConnection("127.0.0.1", 8000, timeout=2)
    connection.request("GET", path)
    response = connection.getresponse()
    body = response.read()
    content_type = response.headers.get_content_type()
    connection.close()
    return response.status, content_type, body


status, content_type, index = request("/")
assert status == 200 and content_type == "text/html"
assert index == Path("/app/frontend/dist/index.html").read_bytes()
assert b"NFX INOV foundation" not in index

asset_urls = re.findall(rb'(?:src|href)="(/assets/[^"]+)"', index)
assert asset_urls
for raw_url in asset_urls:
    asset_url = raw_url.decode("ascii")
    status, content_type, body = request(asset_url)
    artifact = Path("/app/frontend/dist") / asset_url.removeprefix("/")
    expected_type, _ = guess_type(artifact.name)
    assert status == 200 and artifact.is_file()
    assert body == artifact.read_bytes()
    assert content_type == expected_type

assert request("/assets/missing.js")[0] == 404
assert request("/assets/../index.html")[0] == 404
PY
"${compose[@]}" exec -T web python -c 'from urllib.request import urlopen; assert urlopen("http://127.0.0.1:8000/health/ready").status == 200'
"${compose[@]}" ps --status running --services | rg -x 'web|worker|scheduler' | sort | diff -u <(printf '%s\n' scheduler web worker) -
"${compose[@]}" logs worker | grep -q 'worker_started'
"${compose[@]}" logs scheduler | grep -q 'scheduler_started'
