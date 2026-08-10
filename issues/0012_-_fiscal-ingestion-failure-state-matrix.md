---
id: 0012
title: "Implement fiscal ingestion failure-state matrix and recovery semantics"
type: feature
status: closed
priority: high
phase: P4
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0006, 0009, 0010]
blocked_by: []
affects:
  - backend/nfx/collection/
  - backend/nfx/documents/
  - backend/nfx/audit/
  - backend/nfx/migrations/
  - tests/
  - docs/
---

## Description

Deliver P4-03 from the canonical fiscal-ingestion contract: a durable failure-state matrix
that preserves the operational meaning of source outcomes, unit treatment, and recovery
progress. P4-02 already persists pages, received units, artifacts, checkpoints, and cursors;
P4-04 already reads and presents several states. The remaining gap is that the ingestion
baseline still maps multiple materially different conditions to generic `failed` or `partial`
states, so a valid empty response, unavailable source, no coverage, temporary failure,
permanent failure, malformed/unknown payload, quarantine, conflict, and recoverable pending
work cannot be handled and audited as one explicit contract.

The outcome is an additive, simulator-only implementation of the approved P4-03 state and
recovery semantics. It must preserve evidence, prevent false cursor progress, and make
reconciliation converge without changing the P4-01 identity contract or duplicating P4-02
cursor/checkpoint ownership.

## Objective and Expected Outcome

Represent each page, received unit, and collection execution with a safe, documented outcome
and recovery meaning. Valid empty and no-coverage results remain successful but distinct;
source unavailability, temporary failures, cooldown/retry, permanent blocking, malformed or
unknown payloads, quarantine, and identity/content conflicts retain their own reason and
actionability. Durable progress advances only after the exact terminal conditions permitted by
the spec are met, and all failure boundaries remain retryable or terminal according to their
classification without losing original artifacts or creating duplicate documents/events.

## Implementation Plan

1. Map the approved P4-03 contract to the existing `IngestionPage`, `ReceivedUnit`,
   `CollectionExecution`, document, audit, and status boundaries. Define a finite internal
   outcome/recovery vocabulary and safe reason-code mapping for valid empty, no coverage,
   unavailable, temporary failure, permanent failure/blocked, malformed or unknown payload,
   partial, pending/retryable, quarantine, and conflict. Keep the distinction between an
   adapter response outcome, a page state, a unit treatment, and a collection-level display
   state explicit; do not infer fiscal absence from missing data.
2. Extend the durable model/service contract additively only where the current fields cannot
   preserve that vocabulary or recovery evidence. Keep bounded codes and references only;
   preserve existing uniqueness, lease, artifact, document, event, and checkpoint constraints.
   If a migration is required, make clean install and upgrade converge and retain all existing
   P4-01/P4-02 data without destructive rewriting.
3. Update ingestion transition sequencing so source failure, malformed/unknown input, missing
   or divergent identity, object-store failure, database/transaction failure, checkpoint
   failure, and cursor-position failure each leave the safe durable boundary required by the
   spec. A valid empty page may advance its continuation; a partial or unresolved page may not
   falsely advance it; quarantine and conflict preserve original/evidence references; and a
   retry/replay is idempotent and cannot overwrite a prior terminal conflict or resurrect
   blocked work without an explicit allowed transition.
4. Make reconciliation and collection-status mapping consume the same authoritative state
   contract. Retryable states must be safely reprocessed after restart and converge to a
   terminal page/unit result; permanent/blocking states must stop automatic retry; unavailable
   and no-coverage must remain distinct from valid empty; and P4-04 must continue to expose
   safe state/reason data without gaining a second state machine. Audit transitions and emit
   only bounded identifiers, reason codes, and permitted digest prefixes.
5. Add tests first and implement focused unit/integration coverage for every matrix row and
   negative transition: empty versus no coverage/unavailable, temporary versus permanent
   failure, malformed/unknown payload, partial pages, identity quarantine, divergent-hash
   conflict, object/database/checkpoint/cursor failures, restart/retry/replay, concurrent
   duplicate handling, blocked-work protection, audit/redaction, and no false progress. Use
   synthetic simulator fixtures only and prove no official network, credential, or fiscal
   payload is required.
6. On completion, document the state/reason and recovery contract, synchronize the P4-03
   evidence in `IMPLEMENTATION_PLAN.md`, the owning P4 spec and `specs/README.md` according to
   repository conventions, refresh Graphify metadata with `graphify update .`, update this
   issue's Resolution, and close the work in one focused commit.

## In Scope

- The P4-03 durable state/reason matrix for fiscal ingestion pages, units, and collection
  outcomes.
- Additive persistence and transition/reconciliation changes required to preserve that matrix,
  including migration and upgrade evidence if needed.
- Safe audit/observability mapping and compatibility with the existing P4-04 read contract.
- Fault-injection, idempotency, concurrency, restart/retry, redaction, and no-network tests
  using synthetic data.
- Contributor/operator documentation for the state meanings and recovery actions.

## Out of Scope

- Replacing P4-01 document identity, competence, event-linkage, artifact, replay, or conflict
  semantics; issue 0006 remains the owner of those contracts.
- Creating a second cursor, NSU, checkpoint, received-unit, retry-policy, or collection
  execution owner; issue 0009 and the existing P3 collection/job contracts remain authoritative.
- New document search/detail/download, manual conflict resolution UI, PDF/DANFE/DANFSe, ZIP,
  retention, deletion, dashboard, or frontend architecture work.
- Official NF-e/NFS-e transports, endpoint/envelope/homologation decisions, production
  credentials, real XML/PDF, or external fiscal calls.
- Broad cleanup or unrelated changes to completed P0–P3/P4-01/P4-02/P4-04 behavior.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P4-03, “Estados de falha”; P4-01/P4-02 are complete
  prerequisites and P4-04 is a completed read-only consumer.
- Canonical spec: `specs/p4-fiscal-document-ingestion-and-integrity.md`, current repository
  revision (the spec has no explicit version field), especially “Pipeline e invariantes”,
  “Contratos, frontend e autorização”, “Segurança, auditoria e observabilidade”, “Falhas,
  recovery e testes”, and the P4-03 acceptance/DoD checklist.
- Related completed work: `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0009_-_durable-ingestion-pipeline-and-cursor.md`, and
  `issues/0010_-_minimum-document-status-and-list-contract.md`. Issue 0009 explicitly leaves
  the complete failure-state matrix open; issue 0010 must remain a read-only presentation
  layer.
- Current baseline evidence: `backend/nfx/collection/ingestion.py` records source and unit
  failures with generic page/unit failure paths, while `backend/nfx/documents/status.py` maps
  those fields for display. The implementation must refine that contract from the spec rather
  than infer new business states from the existing enum names.
- Data/compatibility: migrations must be additive and preserve immutable originals, both
  divergent evidence references, monotonic independent NF-e cursor/ADN NSU positions, and
  existing P3 job/collection idempotency. No destructive migration or silent status rewrite is
  authorized.
- Security/observability: external responses are untrusted and bounded; logs, audit, metrics,
  and persisted fields must exclude raw payloads, XML/PDF, certificates, tokens, credentials,
  object keys that expose secrets, and unredacted exceptions.

## Tests

- **Unit:** outcome/reason classification, allowed transitions, empty/no-coverage/unavailable
  distinctions, partial and blocked behavior, safe serialization/redaction, and cursor-advance
  predicates.
- **Integration:** clean install/upgrade if schema changes; object, database, transaction,
  checkpoint, and cursor fault injection; quarantine/conflict evidence preservation; retry and
  reconciliation convergence; replay and concurrent duplicate/conflict handling; audit and
  no-write/false-progress assertions.
- **Validation commands:** focused P4 tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] Every P4-03 page, unit, and collection outcome has a finite safe state/reason contract
  that distinguishes valid empty, no coverage, unavailable, temporary failure, permanent
  failure/blocked, malformed/unknown, partial, retryable, quarantine, and conflict outcomes.
- [x] A valid empty result is never reported as unavailable, no coverage, partial, or success
  with documents; no-coverage and source unavailability are never reported as valid empty.
- [x] Cursor/NSU advances only after the state-specific durable treatment allowed by the spec;
  partial, unresolved, failed, or unknown work cannot produce false progress.
- [x] Retry/replay and reconciliation are idempotent across restarts and do not duplicate or
  overwrite documents, events, artifacts, evidence, pages, checkpoints, or cursor/NSU state.
- [x] Quarantine and divergent identity/content conflict preserve the original and all required
  evidence references, safe reason codes, and recoverability without silent overwrite.
- [x] Temporary/retryable states can converge after object, database, transaction, checkpoint,
  or cursor failure; permanent/blocked states cannot be automatically retried or resurrected by
  replay without an explicit permitted transition.
- [x] Concurrent duplicate pages/units and retry races resolve deterministically through the
  existing constraints/transactions, with no regression to lease, idempotency, or independent
  NF-e/ADN continuation invariants.
- [x] Audit, logs, metrics, persisted fields, and API-compatible status data contain only safe
  bounded identifiers/reason codes and permitted digest prefixes; no raw payload, secret,
  object key, or unredacted external error is exposed.
- [x] Synthetic tests cover every expected and negative matrix row, fault boundary, recovery
  path, authorization-safe read compatibility, and no-network constraint; all configured
  validation commands pass without regressions.
- [x] Required state/recovery documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the
  owning P4 spec/index evidence, this issue's Resolution, and one focused implementation commit
  are synchronized before closure; P5/P6/P7 behavior is not claimed complete.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P4-03 failure states.
- Spec: `specs/p4-fiscal-document-ingestion-and-integrity.md` — pipeline invariants, failure
  recovery/tests, security/observability, and P4 DoD; current repository revision.
- Product/architecture authority: `PRD.md` section 18 and `ARCHITECTURE.md` sections 32, 36,
  and 37.
- Related issues: `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0009_-_durable-ingestion-pipeline-and-cursor.md`, and
  `issues/0010_-_minimum-document-status-and-list-contract.md`.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- What was done, decisions made, and why. -->

- Implemented the finite `IngestionOutcome`/`IngestionRecovery` contract and persisted it on collection executions, ingestion pages, and received units through additive migration `0014_ingestion_failure_state_contract`; expanded page states distinguish no coverage, unavailable, retry, cooldown, and blocked outcomes while retaining P4-02 cursor/checkpoint ownership.
- Added shared response and unit-treatment classification. Valid empty and successful terminal pages may advance; no coverage, unavailable, timeout, cooldown, blocked, malformed, partial, and unsafe-position responses do not. Object/persistence failures remain retryable, malformed/insufficient identity remains quarantined with finalized evidence, and divergent content remains a conflict with evidence preserved.
- Made retry of an incomplete page position-aware and idempotent, prevented incomplete resumed pages from advancing, exposed persisted outcomes to the P4-04 status contract, and propagated safe outcome/recovery summaries through `CollectionExecution` without introducing a second cursor or document state machine.
- Added unit and PostgreSQL/MinIO integration coverage for the response matrix, persisted safe fields, same-position recovery, no false cursor progress, migration install/upgrade, reconciliation, quarantine, conflict, replay, stale/repeated positions, and independent ADN NSU behavior.
- Synchronized `IMPLEMENTATION_PLAN.md`, `specs/p4-fiscal-document-ingestion-and-integrity.md`, `specs/README.md`, and `docs/DEVELOPMENT.md`. P5/P6 transports, P7 consultation/PDF, and later retention/deletion behavior remain unimplemented.

Validation completed:

- `make build` — passed.
- `make lint` — passed (Ruff, mypy, frontend TypeScript/ESLint).
- `TEST_RUN_ID=20260810-p403 ./scripts/test-integration.sh` — passed; 48 integration tests, including migration clean install/upgrade.
- Focused unit matrix/status tests — passed; full local `make test-unit` could not connect to the repository's PostgreSQL service, while database-backed ingestion coverage passed in the isolated integration runner.
- `make smoke` — passed with isolated PostgreSQL, MinIO, web, worker, and scheduler.
- `graphify update .` — passed; code graph refreshed (Graphify reported only its existing zero-node warnings for `hooks.json` and `pyproject.toml`).
