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
"${compose[@]}" exec -T web python -c 'from urllib.request import urlopen; assert urlopen("http://127.0.0.1:8000/health/ready").status == 200'
"${compose[@]}" ps --status running --services | rg -x 'web|worker|scheduler' | sort | diff -u <(printf '%s\n' scheduler web worker) -
"${compose[@]}" logs worker | grep -q 'worker_started_no_jobs'
"${compose[@]}" logs scheduler | grep -q 'scheduler_started_no_jobs'
