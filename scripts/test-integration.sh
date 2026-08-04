#!/usr/bin/env bash
set -euo pipefail

run_id="${TEST_RUN_ID:-$(date +%s)-$$}"
project="nfx-p0-test-${run_id}"
bucket="nfx-p0-test-${run_id}"
compose=(docker compose -p "$project" -f docker-compose.test.yml)

cleanup() {
  "${compose[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

"${compose[@]}" up -d --wait postgres minio
MINIO_BUCKET="$bucket" "${compose[@]}" run --rm minio-init
MINIO_BUCKET="$bucket" TEST_RUN_ID="$run_id" "${compose[@]}" run --no-deps --rm test-runner python backend/manage.py nfx_migrate
MINIO_BUCKET="$bucket" TEST_RUN_ID="$run_id" "${compose[@]}" run --no-deps --rm test-runner python backend/manage.py schema_status
MINIO_BUCKET="$bucket" TEST_RUN_ID="$run_id" "${compose[@]}" run --no-deps --rm -e DJANGO_SETTINGS_MODULE=nfx.settings test-runner python -m pytest -rs tests/integration
