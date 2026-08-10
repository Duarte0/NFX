---
id: 0009
title: "Implement durable fiscal ingestion pipeline and cursor checkpoints"
type: feature
status: closed
priority: critical
phase: P4
created_at: 2026-08-09
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0003, 0006]
blocked_by: []
affects:
  - backend/nfx/collection/
  - backend/nfx/documents/
  - backend/nfx/artifacts/
  - backend/nfx/adapters/
  - backend/nfx/jobs/
  - backend/nfx/migrations/
  - tests/
  - docs/
---

## Description

Deliver the P4-02 durable ingestion boundary that turns a simulator page into durably tracked received units, immutable original-object references, document/event or explicit quarantine/conflict outcomes, and a checkpoint that is safe to resume. The cursor/NSU must advance only after every unit in the page has reached a durable terminal treatment; retries and restarts must converge without silently losing a unit or duplicating logical progress.

Verified gap: issue 0006 supplied the `nfx.documents` identity, event, competence, evidence, replay, and conflict foundation, but the repository has no received-unit/page/checkpoint model, cursor/NSU ownership, object-before-database orchestration, or reconciler. The existing P3 simulator exposes synthetic pages and continuation values, and P3-05 records collection executions, but neither currently persists fiscal units or advances a durable collection cursor. Existing closed issues 0001–0008 do not cover this outcome.

## Objective and Expected Outcome

Provide one reusable ingestion service for NF-e and ADN-shaped simulated pages. It records the page and each unit, writes the original through the established artifact boundary before durable database finalization, delegates identity/classification to the P4-01 document boundary, records checkpoint progress and safe outcome categories, and commits the next cursor/NSU only when the page is complete. A failure or restart leaves explicit pending evidence that can be retried and reconciled; no database/object-store failure is reported as successful progress.

## Implementation Plan

1. Define the P4-02 domain contract and additive schema for collection family/flow, execution/page, received unit, checkpoint, and safe unit outcome. Persist bounded synthetic/external references, cursor or NSU values, page identity, unit identity, artifact reference, digest/size metadata, processing state, attempt/reconciliation timestamps, and safe reason codes. Add constraints and indexes for one logical page/checkpoint per collection scope, one unit identity within its page, monotonic continuation, immutable finalized evidence, and safe retry lookups. Preserve the existing P4-01 models and P3 collection/job records.
2. Add an ingestion service that accepts an adapter page plus collection context and coordinates the required sequence: register execution/page, create pending unit references, write or finalize each original via `ArtifactStorageService`, verify digest and size, then call the document persistence port inside the appropriate transaction. Map persisted, replay, quarantine, and conflict results without copying payload bytes into database fields, logs, or audit context. Keep cursor/NSU advancement in this service; adapters must not own a second cursor or ingestion state.
3. Make each boundary restart-safe and idempotent. Replaying the same page or unit must reuse the existing durable record and must not duplicate document, event, evidence, artifact reference, checkpoint, or progress. A same-identity/different-hash result must preserve both artifact references and remain a conflict. Identity-insufficient or otherwise safe classification failures must remain explicit unit outcomes rather than being treated as a successful cursor advance unless the page contract says the unit is durably classified. A concurrent retry must resolve database uniqueness races to the same documented outcome.
4. Commit checkpoints transactionally with the unit’s durable terminal treatment and advance the page cursor/NSU only after all units are terminal and all required artifact references are finalized. Enforce monotonic cursor/NSU progression per company/family/flow, reject stale or repeated continuation values without regressing progress, and distinguish an empty complete page from a partial page, failed page, or page with pending units. Do not advance any cursor when object storage, database, transaction, or checkpoint persistence fails.
5. Integrate the existing collection job/handler seam with this pipeline using only the deterministic P3 simulator and synthetic fixtures. Preserve worker lease/idempotency behavior and make reconciliation safe if a worker stops before object persistence, after object persistence, before document transaction, after document transaction, before checkpoint, or after a cursor write. Do not add official fiscal endpoints, certificates, production CNPJs, or real network calls.
6. Add unit and PostgreSQL integration coverage for clean install/upgrade, page/unit state transitions, object-before-database ordering, replay, duplicate and concurrent units, divergent hashes, identity-insufficient classification, partial pages, empty pages, stale/repeated cursor or NSU, monotonic progression, restart recovery, and injected failures at every transaction boundary. Assert that pending object references are detectable and reconciled without deleting evidence or falsely advancing progress. Include safe audit/log/metric assertions using IDs and bounded hash prefixes only.
7. On completion, update the P4-02 evidence/status in `IMPLEMENTATION_PLAN.md`, the P4 spec and `specs/README.md` only according to their existing completion conventions, document the ingestion/checkpoint contract, refresh Graphify with `graphify update .`, update this issue’s Resolution, and close the complete work in one focused commit.

## In Scope

- Durable page, received-unit, checkpoint, cursor/NSU, and reconciliation contracts for the common P4 ingestion boundary.
- Additive migrations, constraints, indexes, artifact-reference sequencing, and integration with P4-01 document persistence and P3 jobs/simulators.
- Idempotent replay, concurrent duplicate handling, monotonic progress, partial/empty/pending outcomes, restart recovery, and fault-injection evidence.
- Safe audit/log/metric context and focused development documentation for this pipeline.

## Out of Scope

- P4-03’s complete failure-state matrix, user-facing quarantine/conflict resolution, or new retry policy.
- P4-04 document status/list API, browser UI, advanced search, or download.
- Official NF-e/ADN transports, endpoint/certificate/homologation decisions, production fiscal calls, or real credentials/data.
- PDF/DANFE/DANFSe, ZIP export, retention, backup, deletion, or unrelated job/collection refactoring.
- Changing the P4-01 identity contract, duplicating cursor state in adapters, or storing raw XML/PDF/payload content in PostgreSQL logs, audit records, or issue fixtures.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P4-02, critical-path durable pipeline and cursor; P4-03/P4-04 and P5/P6 follow it.
- Canonical spec: `specs/p4-fiscal-document-ingestion-and-integrity.md` — P4-02, current repository version; especially “Pipeline e invariantes”, “Falhas, recovery e testes”, and the cursor/NSU DoD.
- Completed dependencies: issue 0003 provides deterministic simulator pages and continuation values; issue 0006 provides the `nfx.documents` persistence/replay/conflict port; P3-01/P3-02/P3-04 job infrastructure and P3-05 execution control are already closed.
- Data/migration: use an additive migration and preserve existing `Artifact`, document/event, collection execution, job, audit, and policy constraints. Clean install and upgrade from the current head must converge to the same schema.
- Compatibility: callers that only enqueue or inspect synthetic collection executions retain their existing safe behavior; the new pipeline is the sole owner of received-unit/checkpoint/cursor progression and must not change adapter response semantics.
- Security: all external page/unit fields are untrusted and bounded; store only safe references, metadata, reason codes, and partial digests. Never persist or emit raw XML/PDF/payload bytes, certificates, tokens, credentials, object keys that expose secrets, or unredacted external exceptions.
- Observability/rollout: expose bounded counts and age/state signals for pending, persisted, replayed, quarantined, conflicted, and divergent-object units; rollout requires migration install/upgrade evidence and synthetic no-network validation before any future official transport work.

## Tests

- **Unit:** page/unit contract, state transitions, cursor/NSU monotonicity, empty versus partial versus failed classification, safe reason mapping, replay/idempotency, and redaction.
- **Integration:** additive migration clean install/upgrade; artifact-before-database sequencing; document/event integration; duplicate and concurrent unit races; checkpoint and cursor progression; pending-reference reconciliation; worker restart and lease recovery.
- **Fault injection:** object-store failure, database failure, transaction rollback, process interruption before/after document persistence, checkpoint failure, and cursor-write failure; verify no false progress and eventual safe retry.
- **Validation commands:** run focused P4 tests plus the repository’s configured `make lint`, `make test-unit`, `make test-integration`, `make smoke`, and applicable schema/build checks.

## Acceptance Criteria

- [x] Additive migrations and registered models persist pages, received units, checkpoints, artifact references, safe outcomes, and cursor/NSU state with constraints and indexes that prevent duplicate logical progress.
- [x] Every received unit has an explicit durable state and safe outcome; pending, persisted, replay, quarantine, conflict, empty, partial, and failed conditions are not silently collapsed into success.
- [x] Original object data is written/finalized and its digest/size verified before the corresponding database record is marked durably treated; object/database failures leave detectable retryable state.
- [x] The pipeline delegates identity, event linkage, competence, replay, and divergent-hash conflict semantics to the P4-01 document boundary without duplicating or weakening that contract.
- [x] Replaying the same page or unit is idempotent and does not duplicate documents, events, evidence, artifacts, checkpoints, or cursor/NSU progress.
- [x] Concurrent processing of the same logical unit or page resolves deterministically through constraints/transactions; conflicting hashes preserve both evidence references and do not overwrite the original.
- [x] Cursor/NSU advances only after every unit in the page has durable terminal treatment and the checkpoint is committed; any failure before that point leaves progress unchanged or explicitly pending.
- [x] Cursor/NSU progression is monotonic per company/family/flow; stale or repeated continuation values cannot regress or falsely advance the checkpoint, and NF-e and ADN continuation fields remain independent.
- [x] Restart/retry converges after failures before and after object persistence, document transaction, checkpoint, and cursor write, without asserting success for work whose durability is unknown.
- [x] Worker/job integration remains lease-safe and simulator-only: tests demonstrate no official fiscal network call, no production endpoint, and no requirement for real credentials or fiscal fixtures.
- [x] Logs, audit context, metrics, persisted fields, and errors contain only bounded safe identifiers/reason codes and permitted digest prefixes; raw payloads, secrets, and unredacted external exceptions never appear.
- [x] Focused unit, integration, migration, concurrency, recovery, and redaction tests pass, along with the configured repository validation commands and no regressions in P0–P3 suites.
- [x] Completion synchronizes `IMPLEMENTATION_PLAN.md`, the owning P4 spec/index evidence, relevant documentation, Graphify, this issue’s Resolution, and one focused commit; no P4-03/P4-04 behavior is claimed as complete.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P4-02 and the P4 critical path.
- Spec: `specs/p4-fiscal-document-ingestion-and-integrity.md` — P4-02 pipeline, checkpoint/cursor invariants, recovery, and DoD.
- Related completed work: `issues/0003_-_deterministic-fiscal-simulators-and-fixtures.md`, `issues/0006_-_fiscal-document-identity-and-persistence.md`.
- Current boundaries: `backend/nfx/adapters/simulation.py`, `backend/nfx/jobs/`, `backend/nfx/collection/`, `backend/nfx/artifacts/storage.py`, and `backend/nfx/documents/`.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- What was done, decisions made, and why. -->

- Implemented collection-owned `IngestionCheckpoint`, `IngestionPage`, and `ReceivedUnit` models with additive migration `0013`, safe constraints, indexes, terminal outcomes, artifact/document/event references, and independent NF-e cursor and ADN NSU scopes.
- Added `FiscalIngestionService`, `ingest_page`, `ingest_collection_response`, and `reconcile_ingestion`. Originals are finalized and verified through `ArtifactStorageService` before document persistence; P4-01 owns identity, competence, event linkage, replay, quarantine, and divergent-hash conflict behavior. Page progress is committed only after terminal unit treatment, with stale/repeated continuation rejection and uniqueness-race recovery.
- Updated synthetic fixture materialization so simulator hashes correspond to the deterministic in-memory original marker; no official transport or raw fiscal payload was added.
- Added PostgreSQL/MinIO integration coverage for migration upgrade/install, replay, object failure/recovery, quarantine, conflict evidence, stale/repeated cursor, empty pages, and independent ADN NSU progression. Updated the migration baseline assertions.
- Synchronized `IMPLEMENTATION_PLAN.md`, `specs/p4-fiscal-document-ingestion-and-integrity.md`, `specs/README.md`, `docs/DEVELOPMENT.md`, and Graphify metadata. P4-03 and P4-04 remain explicitly pending.

Validation completed:

- `make build` — passed.
- `make lint` — passed (Ruff, mypy, frontend TypeScript/ESLint).
- `make test-unit` — 133 passed.
- `make test-integration` — 33 passed.
- `make smoke` — passed with isolated PostgreSQL, MinIO, web, worker, and scheduler.
- `graphify update .` — completed.
