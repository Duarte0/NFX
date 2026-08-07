---
id: 0004
title: "Implement job observability and initial health"
type: feature
status: closed
priority: high
phase: P3
created_at: 2026-08-07
updated_at: 2026-08-07
closed_at: 2026-08-07
related_issues: [0001, 0002, 0003]
blocked_by: []
affects:
  - backend/nfx/jobs/
  - backend/nfx/infrastructure/
  - backend/nfx/management/commands/
  - backend/nfx/urls.py
  - tests/unit/
  - tests/integration/
  - docs/
---

## Description

Deliver P3-04: safe operational signals for the completed durable-job engine. The P3-01/P3-02 baseline persists queue, lease, retry, cooldown, and blocked state, and the worker/scheduler currently emit only start/stop and failure warnings. Existing `/health/live` is intentionally dependency-free and `/health/ready` reports only PostgreSQL/MinIO readiness. There is no reliable way to determine worker/scheduler freshness, distinguish an overdue queue from an unavailable dependency, or inspect the required job-state signals without exposing job payloads or errors.

The outcome is a read-only operational contract that supplies structured, redacted job logs; metrics for queue state, age, claims, retries, expired leases, blocks, and handlers; and initial health that distinguishes web liveness, dependency readiness, worker/scheduler heartbeat freshness, and delayed backlog. It must report degraded components explicitly while preserving the existing liveness/readiness guarantees and never treating a missing heartbeat as proof that durable work was lost.

Dependencies: P3-01/P3-02/P3-03 are closed in issues 0001–0003; P1-01 persistence/migrations and P1-05 redaction/audit foundations are implemented. This slice may use an additive migration only for durable, safe process-heartbeat/operational state required to assess freshness. It must not require production fiscal endpoints, credentials, or a monitoring service. Thresholds and physical metric/health schemas are Proposed details owned by this implementation, but must be validated, documented, and use no fiscal constants.

## Implementation Plan

1. Define a small jobs/operations read-model contract over the existing durable state. It must calculate queue counts by state, age of the oldest due item, claim/attempt/retry activity, expired-lease recovery, cooldown, terminal blocking, and handler/outcome activity without reading or returning raw payloads, results, exception text, certificates, XML, tokens, or endpoint data. Keep metric labels bounded to safe categories already represented by the job contract; do not introduce unbounded job IDs, correlation IDs, company identifiers, or error content as metric labels.
2. Add structured lifecycle logging at the job-engine and worker/scheduler boundaries. Each relevant claim, renewal/reclaim, finalization/retry/cooldown/block, handler failure, and loop/component transition must include only the safe job identifier/reference, correlation when available, type, attempt, duration, outcome/error class, and process identity required by the P3 spec. Route every field through the established redaction boundary, preserve JSON logging compatibility, and ensure logging failure cannot alter a durable job transition.
3. Establish durable worker and scheduler freshness signals and a deterministic health evaluation. A component must record a safe heartbeat only after its loop has reached the durable-service boundary; a stale/missing heartbeat, database/object-store unavailability, or overdue backlog must be represented as the applicable degraded/unavailable condition rather than as a false-ready result. Preserve `/health/live` as dependency-independent, preserve the existing `/health/ready` dependency semantics, and extend the operational response/route surface only with safe, documented status detail. Use an injected clock and validated operational thresholds so freshness and backlog delay tests are deterministic; do not make health polling perform fiscal work or mutate jobs.
4. Make the metrics and health evaluation read-only with respect to jobs, leases, policies, cursors, and adapters. If an additive heartbeat migration is needed, enforce a stable component identity/uniqueness and forward-compatible timestamps/status fields, retain existing P3 job constraints, and cover clean installation and upgrade. A process restart may replace its own heartbeat but must not erase another component's evidence or revive/alter jobs.
5. Expose only the initial P3 operational scope needed by later dashboard/runtime/backup work: jobs and process/dependency health. Clearly mark unavailable future capabilities (fiscal-source coverage, disk capacity, backup, document/quarantine/rendering status) as unavailable/degraded rather than synthesizing healthy values. Do not add the P8 administrative dashboard, alerts, external metrics infrastructure, runtime TLS/proxy work, or business collection UI.
6. During the build pass, update P3-04 evidence/status in `IMPLEMENTATION_PLAN.md`, `specs/p3-durable-jobs-leases-and-policy-engine.md`, and `specs/README.md` according to their conventions; document the operational contract and thresholds; refresh Graphify with `graphify update .`; update this issue’s Resolution; and commit the completed work as one focused commit.

## Out of Scope

- P3-05 manual collection routes, RBAC/audit commands, UI, and initial-collection consumption.
- P4 ingestion, cursor checkpointing, quarantine/conflict signals, or document persistence.
- P8 dashboard/drill-down, P9 runtime HTTPS, backup/restore health, alerting, external telemetry collectors, or capacity/load tuning.
- Fiscal transport calls, official endpoint/service health, real credentials, PFX/XML content, and production monitoring configuration.
- Changing P3-01 lease/idempotency or P3-02 retry/cooldown/blocking semantics beyond emitting observational signals about their existing transitions.

## Tests

- **Unit:** jobs metrics/read-model, structured-log redaction and bounded labels, component heartbeat freshness, deterministic overdue-backlog classification, unavailable/degraded distinctions, and preservation of `/health/live` and existing readiness semantics.
- **Integration:** PostgreSQL-backed migration installation/upgrade, concurrent component heartbeat ownership/update behavior, job-state aggregates across claim/reclaim/retry/cooldown/block transitions, and database failure with safe degraded health and no job mutation.
- **Commands:** verify web, worker, and scheduler start and stop with safe component signals; retain the smoke proof that no fiscal network call occurs.
- **Validation:** run focused unit/integration tests plus `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A read-only, documented jobs operational contract reports queue counts by durable state; oldest due age; claim, retry, expired-lease, cooldown, and blocked indicators; and bounded safe handler/outcome categories without exposing payloads, raw results, raw errors, certificates, XML, tokens, credentials, endpoints, or unbounded labels.
- [x] Structured logs for job and process lifecycle contain timestamp, process, correlation when available, safe job reference, type, attempt, duration, result, and allowed error class; all fields pass through redaction, and logging failure cannot change durable job state.
- [x] Worker and scheduler heartbeats are durable, safe, and independently assessable after restart; concurrent process updates cannot overwrite another component identity or corrupt freshness evidence.
- [x] Health distinguishes dependency-free liveness, PostgreSQL/MinIO readiness, worker freshness, scheduler freshness, and overdue backlog. Missing/stale components and unavailable dependencies are explicit degraded/unavailable states, not false-ready or false-success states.
- [x] `/health/live` remains available without external services and `/health/ready` retains its current dependency-readiness contract; the added operational health detail is safe, documented, and performs neither fiscal work nor a job/lease/policy transition.
- [x] Threshold-based freshness and backlog delay handling use validated configuration and an injectable clock; boundary conditions, process restart, delayed polling, and unavailable database/object storage are deterministic and tested.
- [x] An additive migration, if used for process-heartbeat state, installs and upgrades cleanly, preserves existing P3 job constraints and data, and does not delete or rewrite job history.
- [x] Future unavailable operational capabilities are explicitly represented as unavailable/degraded where surfaced; this implementation does not claim fiscal-source, disk, backup, document, quarantine, or rendering health it cannot verify.
- [x] Unit and PostgreSQL integration tests cover positive, negative, redaction, retry/cooldown/block, lease-reclaim, concurrency, restart, and dependency-failure paths using only synthetic data and no fiscal network traffic.
- [x] `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke` complete successfully without regression to P3 queue/lease/retry behavior, configuration isolation, existing liveness/readiness, or audit/redaction guarantees.
- [x] Completion synchronizes P3-04 in `IMPLEMENTATION_PLAN.md`, the canonical P3 spec, and `specs/README.md`; updates the operational documentation and this issue’s Resolution; refreshes Graphify; and is committed as one focused commit.

## References

- Implementation plan: `IMPLEMENTATION_PLAN.md` — P3-04, “Logs, métricas de job e health inicial.”
- Spec: `specs/p3-durable-jobs-leases-and-policy-engine.md` — P3-04 pending slice; “Segurança, logs, métricas e health.”
- Product requirements: `PRD.md` — OPS-001 through OPS-006, especially OPS-002/OPS-004; NFR-004, NFR-005, and NFR-008.
- Architecture: `ARCHITECTURE.md` — sections 36 (Observabilidade e saúde), 37 (Estratégia de testes), and 39–41 operational/recovery constraints.
- Current baseline: `backend/nfx/jobs/`, `backend/nfx/infrastructure/http.py`, `backend/nfx/management/commands/{worker,scheduler}.py`, `backend/nfx/urls.py`, `tests/unit/test_health.py`, and `docs/DEVELOPMENT.md`.
- Related closed issues: `issues/0001_-_durable-job-queue-and-leases.md`, `issues/0002_-_policy-driven-job-retry-and-blocking.md`, and `issues/0003_-_deterministic-fiscal-simulators-and-fixtures.md`.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- Include files modified, tests added, edge cases handled, tracking updates, Graphify update, and focused commit. -->

Implemented P3-04 with the additive `0010_process_heartbeats` migration and registered
`ProcessHeartbeat` model. Worker and scheduler now persist independent process freshness evidence,
including explicit stopping state, without deleting another process's history. Added read-only
`JobObservability` aggregates and the administrator-only `/health/operational` contract covering
safe queue/outcome signals, backlog delay, dependency readiness, worker/scheduler freshness, and
explicitly unavailable future capabilities. Added validated heartbeat/backlog thresholds and
safe structured lifecycle logging whose failures cannot affect job transitions.

Added unit coverage for health boundaries, redacted JSON lifecycle fields, configuration thresholds,
loop heartbeat timing, and heartbeat identities, plus PostgreSQL integration coverage for durable
job aggregates and migration installation/upgrade. Existing liveness/readiness and fiscal-network
smoke behavior remain unchanged. Documentation was synchronized in `docs/OPERATIONS.md`,
`IMPLEMENTATION_PLAN.md`, the canonical P3 spec, and `specs/README.md`; Graphify was refreshed.

Validation: 115 unit tests, 23 PostgreSQL integration tests, `make test-unit`, `make lint`, configured `make build`,
and `make smoke` passed. `make build` without the required external test configuration still fails
at the repository's existing fail-closed boot guard; the configured command is the documented
build invocation. No production credentials, fiscal endpoints, or non-ephemeral data were used.
