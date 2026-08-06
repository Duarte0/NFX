---
id: 0001
title: "Implement durable PostgreSQL job queue and leases"
type: feature
status: closed
priority: high
phase: P3
created_at: 2026-08-06
updated_at: 2026-08-06
closed_at: 2026-08-06
related_issues: []
blocked_by: []
affects:
  - backend/nfx/collection/
  - backend/nfx/management/commands/worker.py
  - backend/nfx/management/commands/scheduler.py
  - backend/nfx/migrations/
  - tests/
---

## Description

Deliver the P3-01 prerequisite: a generic, durable PostgreSQL job engine with atomic claiming, owner-bound leases, renewal, safe completion, and recovery of expired work. This replaces the current deliberately empty P0 worker and scheduler loops so later policy, simulator, ingestion, and manual-collection work can use a recoverable queue without embedding durable state in the UI or adapters.

Verified gap: the repository has no job/lease model, migration, service, or job-engine tests; `worker` and `scheduler` currently only log that they run with no jobs. The certificate lifecycle already persists an idempotent `InitialCollectionRequest` handoff, but consuming that request is outside this issue.

## Implementation Plan

1. Add an isolated job-engine domain module and migration, registered with the existing NFX model registry. Persist the generic job fields required by P3-01: type, logical target, safe referential payload, priority, active idempotency key, schedule timestamp, attempt metadata, state, lease owner/issued/expires timestamps, safe result/error fields, and timestamps. Use PostgreSQL constraints and indexes for active idempotency, claim ordering, expired leases, and logical target lookup. Keep payload free of PFX, XML, tokens, or other secret/content material.
2. Implement a transactional internal service contract: idempotent enqueue; due-job claim using PostgreSQL `SKIP LOCKED` (or an equivalent that preserves the same concurrency guarantee); renewal only by the current lease owner; and completion/failure only while the caller still owns an unexpired lease. Model explicitly the state transitions needed for queued, running, completed, and reclaimable expired jobs; reject stale owners and invalid transitions without mutating durable state.
3. Add reclaim/recovery behavior for expired leases and overdue scheduled work. It must make work claimable again without asserting that an arbitrary handler effect is reversible. Define the handler boundary as idempotent and keep job infrastructure separate from fiscal collection state, transports, and document ingestion.
4. Replace the P0-only worker and scheduler command behavior with bounded polling loops that invoke the job-engine service. Scheduler may recover due/expired jobs but must not make fiscal calls; worker must claim, invoke a registered fake/test handler boundary, and finalize only through the valid lease contract. Preserve signal-driven graceful shutdown and redacted structured logging.
5. Add automated tests before implementation for idempotent enqueue, two-worker contention, renewal, expired lease reclaim, stale-owner completion rejection, worker death before and after an idempotent handler effect, scheduler restart recovery, controlled-clock scheduling, database failure without unsafe progress, and process shutdown. Use only synthetic IDs and fake handlers; do not add fiscal networking, adapters, manual endpoints/UI, retry/backoff policy, or production fixtures.
6. During the build pass, update the P3-01 evidence/status in `IMPLEMENTATION_PLAN.md`, the P3 spec/`specs/README.md` only as their completion conventions require, and refresh Graphify with `graphify update .`. Commit the completed implementation as one focused commit.

## Out of Scope

- P3-02 policy versions, retry classification, backoff, jitter, cooldown, and permanent blocking.
- P3-03 fiscal simulators and fixtures.
- P3-04 metrics, operational health states, and dashboard integration beyond minimal safe command logging needed to operate this engine.
- P3-05 manual collection routes, authorization UI, and `InitialCollectionRequest` consumption.
- Fiscal adapters, document ingestion, cursors/NSU, HTTP endpoints, and any production fiscal call.

## Tests

- **Unit:** job state machine and service tests under `tests/unit/`, including frozen-clock and fake-handler coverage.
- **Integration:** PostgreSQL-backed claim/lease contention, migration installation/upgrade, restart/reclaim, and failure-path tests under `tests/integration/`.
- **Commands:** verify worker and scheduler can start, poll the engine, and shut down on signals without creating fiscal network traffic.
- **Validation:** run the relevant focused tests plus `make lint`, `make test-unit`, `make test-integration`, and the applicable smoke/build commands confirmed by the repository.

## Acceptance Criteria

- [x] A PostgreSQL migration and registered generic job model persist jobs, schedules, owner-bound leases, attempts, safe payload references, and results/errors with constraints and indexes appropriate to active idempotency, claims, expired leases, and targets.
- [x] Enqueue is idempotent for an active logical key and returns the existing job rather than creating a duplicate.
- [x] Concurrent workers cannot logically claim the same due job; the implementation uses PostgreSQL locking semantics that preserve this guarantee.
- [x] Only the current owner of an unexpired lease can renew, complete, or fail a running job; stale or expired owners are rejected without changing the job result or state.
- [x] Expired leases and overdue scheduled jobs are recovered after scheduler/worker restart and can be reclaimed safely; handler execution is required to be idempotent and the tests demonstrate no duplicate logical effect with the fake handler.
- [x] The worker and scheduler no longer advertise P0 empty-loop behavior, preserve graceful signal shutdown, and make no fiscal network call.
- [x] All job payloads, logs, and test fixtures exclude PFX, XML, tokens, credentials, and unredacted error content.
- [x] Automated unit and PostgreSQL integration tests cover contention, renewal delay, stale completion, recovery, restart, controlled time, handler interruption, and database unavailability.
- [x] Relevant repository validation commands complete successfully with no regressions in existing migrations, audit behavior, configuration isolation, or command smoke coverage.
- [x] Completion updates the P3-01 evidence/status in the implementation-plan/spec tracking files according to their documented conventions, refreshes Graphify, updates this issue’s Resolution, and is committed as one focused commit.

## References

- Implementation plan: `IMPLEMENTATION_PLAN.md` — P3-01 (critical-path prerequisite); P3-02/P3-03/P3-04/P3-05 follow this engine.
- Spec: `specs/p3-durable-jobs-leases-and-policy-engine.md` — P3-01 slice, version/current repository baseline.
- Related baseline: `backend/nfx/management/commands/worker.py`, `backend/nfx/management/commands/scheduler.py`, and `backend/nfx/collection/models.py`.
- Dependencies: P1-01 persistence/migrations and P1-05 audit foundation are implemented; no issue dependency is currently open. P3-02 policy and P3-04 full observability remain follow-up work.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- Include files modified, tests added, edge cases handled, tracking updates, Graphify update, and focused commit. -->

Implemented P3-01 as the `nfx.jobs` durable PostgreSQL engine. Added the registered `Job` model
and `0008_durable_jobs` migration with active-idempotency, claim-order, expired-lease, target,
and running-lease constraints/indexes. `JobEngine` now provides idempotent enqueue, transactional
`SKIP LOCKED` claim, owner/expiry-conditional renew/complete/fail, controlled-clock recovery,
and safe referential payload/result validation. A handler registry and bounded worker/scheduler
loops replace the P0 empty loops; handlers receive no fiscal transport and logs/errors are
redacted or fixed safe codes. Lease loss requeues work without pretending a handler effect is
reversible, leaving idempotency to the handler boundary as specified.

Added unit and PostgreSQL integration coverage for contention, migration shape, idempotency,
renewal, stale owners, expiry/restart recovery, controlled time, handler interruption and
idempotent effects, database failure, and graceful loop shutdown. Updated smoke and development
documentation, P3-01 status in the implementation plan/spec index, and refreshed Graphify with
`graphify update .`. Validation completed with 69 unit tests, 20 integration tests, Django check,
Ruff, targeted mypy, frontend lint/build, migration status, and smoke. The repository-wide mypy
invocation still reports pre-existing errors in audit/artifact code because the pinned mypy 1.13
does not consume the TOML configuration; no changed-surface errors remain.
