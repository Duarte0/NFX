---
id: 0002
title: "Implement policy-driven job retry and blocking"
type: feature
status: closed
priority: high
phase: P3
created_at: 2026-08-06
updated_at: 2026-08-07
closed_at: 2026-08-07
related_issues: [0001]
blocked_by: []
affects:
  - backend/nfx/jobs/
  - backend/nfx/migrations/
  - backend/nfx/management/commands/
  - tests/unit/
  - tests/integration/
---

## Description

Deliver P3-02: versioned external-collection policies and policy-driven job failure handling. The completed P3-01 engine can requeue a failed handler at an arbitrary time, but it has no persisted policy, result classification, bounded progressive retry, deterministic jitter, cooldown precedence, or terminal blocked state. This prevents later collection commands and fiscal adapters from safely deciding whether a failed operation may run again.

The outcome is a generic jobs-layer contract: a handler reports `success`, `temporary`, `cooldown`, `permanent`, or `partial`; the engine applies the immutable effective policy version to schedule a retry, defer for an official cooldown, or block durable work without a retry loop. It must remain independent of manual collection, fiscal transports, ingestion, and official endpoint values.

## Implementation Plan

1. Extend the `nfx.jobs` domain and add an additive migration for a versioned policy record and the durable job state/data needed to retain the effective policy reference, terminal blocking, and safe classified outcome. The policy contract must cover source/flow scope, validity, retry limit, progressive backoff cap, jitter configuration, and cooldown. Preserve the existing active-idempotency, lease, payload-safety, and compatibility constraints; jobs already in progress must remain processable by a compatible version.
2. Define a validated internal policy-selection and failure-classification API. Resolve the policy when work is scheduled or finalized according to the spec’s effective-policy invariant, reject malformed/ambiguous policy definitions, and persist only stable identifiers and safe error/result codes. Do not encode fiscal values as Python constants or place certificates, XML, tokens, raw errors, or response content in policy/job data.
3. Update the job-engine transition contract so handler outcomes drive state safely: successful work completes; temporary and partial outcomes requeue at a policy-derived due time while attempts remain; an official cooldown overrides the local retry schedule; and permanent certificate/authorization failures become an explicit blocked state with no automatic loop. Lease ownership and expiry checks must still guard every transition, including policy-driven retry or blocking.
4. Make backoff progressive, capped, and reproducible under an injected clock/randomness seam so tests can assert jitter without flakiness. Ensure concurrent finalization, retry exhaustion, scheduler/worker restart, and policy changes cannot produce duplicate logical work, bypass a cooldown, or resurrect a blocked job without an explicit future workflow.
5. Adjust worker/scheduler integration only as needed to consume the classified handler result and recover due work. Keep scheduler non-fiscal and worker handlers transport-free; retain redacted structured logging and emit only safe policy/job identifiers and outcome categories. P3-04 metrics and health-state implementation remain separate.
6. During the build pass, update P3-02 completion evidence in `IMPLEMENTATION_PLAN.md`, this spec and `specs/README.md` only as their documented completion conventions require, refresh Graphify with `graphify update .`, update this issue’s Resolution, and commit the completed implementation as one focused commit.

## Out of Scope

- P3-03 fiscal simulator ports, scenarios, or fixtures.
- P3-04 job metrics, detailed operational health, dashboard, runtime HTTPS, or alerting.
- P3-05 manual collection models, HTTP/UI commands, RBAC/audit flows, and consumption of initial collection requests.
- Fiscal transports, official endpoints, official retry/cooldown values, document ingestion, cursors/NSU, and any production fiscal network call.
- Changing the P3-01 claim/lease concurrency design except where a policy transition must preserve its invariants.

## Tests

- **Unit:** add `tests/unit/` coverage before implementation for policy validation/selection, every classified result, capped progressive backoff, deterministic jitter, cooldown precedence, retry exhaustion, permanent blocking, stale-owner rejection, policy change compatibility, and controlled-clock restart recovery.
- **Integration:** add PostgreSQL-backed `tests/integration/` coverage for the additive migration, concurrent finalization/retry behavior, persisted effective-policy references, and blocked jobs remaining unclaimable after worker/scheduler restart.
- **Commands:** verify worker and scheduler process only synthetic registered handlers, preserve graceful shutdown, and make no fiscal network call.
- **Validation:** run the focused tests plus `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A forward-compatible PostgreSQL migration persists versioned policies and the job information required to retain the effective policy, classified outcome, retry schedule, cooldown, and terminal blocked state without weakening P3-01 constraints.
- [x] A policy is selected and validated through an internal jobs contract using source/flow scope and validity; malformed or ambiguous policy data is rejected safely, and existing compatible jobs remain recoverable across an upgrade.
- [x] Handler results `success`, `temporary`, `cooldown`, `permanent`, and `partial` produce the specified durable completion, retry, cooldown, or blocked behavior while a valid owner lease is required for every transition.
- [x] Retry timing uses a policy-derived progressive backoff with configurable cap and deterministic testable jitter; retry limits stop automatic requeueing.
- [x] An official cooldown takes precedence over local retry timing and cannot be bypassed by a restart, a concurrent worker, or a policy update.
- [x] Permanent certificate or authorization failures are durably blocked and are not automatically claimed or retried in a loop.
- [x] Concurrent or stale lease owners cannot duplicate a policy transition, overwrite a safe outcome, or revive blocked work; restart recovery preserves due retries and blocked work correctly.
- [x] Job payloads, persisted safe outcomes, logs, and synthetic fixtures contain no PFX, XML, tokens, credentials, raw endpoint data, or unredacted error content.
- [x] Automated unit and PostgreSQL integration tests cover the policy, timing, classification, concurrency, failure, and recovery cases above with no fiscal network traffic.
- [x] `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke` complete successfully without regressions in P3-01 queue/lease behavior. `make lint`, `make test-unit`, and the test-profile `make build` passed; the isolated Docker PostgreSQL/MinIO workflow passed 22 integration tests, the full unit suite passed 108 tests, migration validation passed, and smoke passed with web/worker/scheduler running.
- [x] Completion updates P3-02 evidence in the plan/spec tracking files according to their documented conventions, refreshes Graphify, updates this issue’s Resolution, and is committed as one focused commit.

## References

- Implementation plan: `IMPLEMENTATION_PLAN.md` — P3-02, the high-priority policy prerequisite for P3-05 and P5/P6 collection flows.
- Spec: `specs/p3-durable-jobs-leases-and-policy-engine.md` — P3-01/P3-02 slices complete; P3-04 remains pending.
- Related issue: `issues/0001_-_durable-job-queue-and-leases.md` — closed P3-01; it explicitly excludes policies, retry, backoff, jitter, cooldown, and permanent blocking.
- Current baseline: `backend/nfx/jobs/models.py`, `backend/nfx/jobs/services.py`, `backend/nfx/jobs/handlers.py`, `backend/nfx/management/commands/worker.py`, and `backend/nfx/management/commands/scheduler.py`.
- Dependencies: P3-01 is complete in closed issue 0001; P1-01 persistence/migrations and P1-05 audit foundation are implemented. No open issue blocks this slice.

---

## Resolution
<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- Include: files modified, tests added, edge cases handled, tracking updates, Graphify update, and focused commit. -->

Implemented P3-02 in `nfx.jobs` with additive migration `0009_job_policies`. Added validated,
versioned source/flow policies with validity windows, retry limits, progressive capped backoff,
injected deterministic jitter, policy-scoped cooldown, effective-policy job references, safe
classified outcomes, and terminal blocked state. Worker finalization now requires the active
lease for success, retry, cooldown, partial, and permanent transitions; stale owners and
unregistered handlers cannot bypass the policy contract. Effective policy versions and each
job’s captured policy reference are immutable, configured cooldowns work when a handler supplies
no deadline, and existing P3-01 jobs without a policy remain processable with legacy mapping
results retaining success compatibility.

Added unit coverage for exact/wildcard selection and ambiguity, timing/jitter, retry exhaustion,
cooldown precedence and fallback, permanent blocking, immutable effective policies, and classified
worker handling. Added PostgreSQL integration coverage for migration/index/constraint shape and
effective-policy persistence. Validation completed with `make lint`, `make test-unit`, test-profile
`make build`, `make test-integration` (22 passed), the full unit suite (108 passed), Django check,
migration consistency, frontend lint/build, and `make smoke`. Tracking files and Graphify are
synchronized; no fiscal network or production data was used.
