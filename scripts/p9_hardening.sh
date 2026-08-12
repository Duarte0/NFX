#!/usr/bin/env bash
set -euo pipefail

# This is an ephemeral P9 evidence run. It never reads the runtime compose file,
# production environment, or a persistent volume.
run_id="p9-hardening-$(date +%s)-$$"
project="nfx-p9-hardening-${run_id}"
bucket="nfx-p9-hardening-${run_id}"
compose=(docker compose -p "$project" -f docker-compose.test.yml)

cleanup() {
  "${compose[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

wait_for_live() {
  for _ in $(seq 1 30); do
    if "${compose[@]}" exec -T web python -c \
      'from urllib.request import urlopen; assert urlopen("http://127.0.0.1:8000/health/live").status == 200' \
      >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done
  return 1
}

MINIO_BUCKET="$bucket" "${compose[@]}" up -d --wait postgres minio
MINIO_BUCKET="$bucket" "${compose[@]}" run --rm minio-init
MINIO_BUCKET="$bucket" TEST_RUN_ID="$run_id" "${compose[@]}" run --no-deps --rm test-runner \
  python backend/manage.py nfx_migrate
MINIO_BUCKET="$bucket" TEST_RUN_ID="$run_id" "${compose[@]}" run --no-deps --rm \
  -e DJANGO_SETTINGS_MODULE=nfx.settings test-runner \
  python -m pytest -q -s tests/integration/test_p9_hardening.py

MINIO_BUCKET="$bucket" "${compose[@]}" up -d web worker scheduler
wait_for_live
"${compose[@]}" exec -T web python -c \
  'from urllib.request import urlopen; assert urlopen("http://127.0.0.1:8000/health/ready").status == 200'

"${compose[@]}" restart web worker scheduler
wait_for_live
"${compose[@]}" logs worker | grep -q 'worker_started'
"${compose[@]}" logs scheduler | grep -q 'scheduler_started'

printf '%s\n' 'P9 hardening ephemeral evidence completed.'
