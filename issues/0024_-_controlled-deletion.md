---
id: 0024
title: "Implement controlled fiscal document deletion with recovery"
type: feature
status: closed
priority: high
phase: P9
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0006, 0017, 0019, 0023]
blocked_by: []
affects:
  - backend/nfx/retention/
  - backend/nfx/documents/
  - backend/nfx/artifacts/
  - backend/nfx/audit/
  - backend/nfx/jobs/
  - backend/nfx/identity/
  - backend/nfx/urls.py
  - backend/nfx/migrations/
  - frontend/src/
  - tests/
  - docs/
---

## Description

Deliver P9-03 from the approved controlled-deletion contract. Retention currently calculates
eligibility and exposes a deterministic Administrator-only preview, but `retention_preview()`
explicitly reports that the preview does not authorize deletion. There is no deletion request,
confirmation, durable saga/checkpoint state, execution boundary, recovery flow, UI control, or
fault-injection evidence. Artifact storage currently permits deletion only for explicitly
temporary export artifacts, and existing document/evidence relationships are protected rather
than safely handled as a fiscal deletion set.

## Objective and Expected Outcome

An Administrator can request deletion only for a currently eligible document after seeing the
exact current scope, confirming that scope explicitly, and supplying a bounded reason. The server
revalidates the session, role, eligibility, and preview scope before creating one active durable
operation. A resumable, idempotent saga treats the document, events, original/XML evidence, and
all related derived artifacts as one coherent set; it never reports success while any required
step is unknown, partially completed, orphaned, or inconsistent. Partial failure becomes an
explicit recovery-required state with a safe resume/reconciliation path and the existing backup
verification and manual recovery procedure as the operational fallback. The audit chain retains
the administrative decision and outcome without fiscal content.

The verified gap is the pending P9-03 row in `IMPLEMENTATION_PLAN.md` and the unchecked DoD in
`specs/p9-controlled-deletion.md`. P8-03 and P9-02 are complete prerequisites. P7-03 issue 0023
is a separate open issue; this work must handle any derived PDFs present without taking ownership
of PDF rendering.

## In Scope

- An additive deletion-request, step/item, and safe state contract for
  `pendente|em_execução|recuperação_necessária|falha|concluída`, including the preview
  scope hash/version, reason, actor, timestamps, correlation, bounded failure code, and
  checkpoint data required to resume safely.
- Administrator-only request, status, recovery/resume, and completion boundaries using the
  existing session, RBAC, CSRF, audit, and retention-preview contracts.
- Eligibility and scope revalidation at request and execution time, active-operation
  concurrency protection, explicit confirmation that cannot be reused as a generic token, and
  safe handling of retained, non-executable, stale, changed, missing, or conflicting scopes.
- Coherent treatment of the document, events/substitutions, original/XML evidence, PDF and
  other derived artifacts, their object-store bytes, and their relational references, with no
  orphaned object or misleading surviving record.
- A durable, restartable saga integrated with the existing job/lease boundary where execution
  is asynchronous; no new queue or broker. The backup set, integrity validation, and manual
  recovery runbook remain available; automated PostgreSQL/MinIO restore is not required.
- Bounded deletion/recovery metrics, append-only audit evidence, safe logs, synthetic fixtures,
  fault injection, focused UI states, and contributor/operator documentation.

## Implementation Plan

1. Map the P9-03 contract to the existing `retention` calculate-on-read decision and
   `scope_hash`, `Document`/`DocumentEvent`/evidence relationships, `Artifact` metadata,
   `ArtifactStorageService` object-store boundary, `AuditService` reason enforcement, identity
   policy, `JobEngine` lease/retry semantics, and the P9-02 backup/restore runbook. Define the
   operation and checkpoint state machine from the canonical spec, including which physical
   deletion order is safe when PostgreSQL and MinIO cannot commit atomically. Record that
   implementation choice and its recovery invariants; do not alter the retention dates or
   invent automatic deletion.
2. Add an additive migration and model/service contract for one deletion operation and its
   bounded steps/items. Store only IDs, digest/hash prefixes or full scope hashes, sizes,
   versions, safe reason/result codes, and timestamps needed for recovery. Add a database
   constraint that prevents more than one active decision for a document and indexes for
   document/state/date lookup. Preserve audit rows, backups, companies, users, certificates,
   unrelated documents, and retained/non-executable documents. Prove clean install, upgrade,
   and migration rerun behavior.
3. Implement the request transaction at the retention boundary. Require an Administrator,
   explicit current preview confirmation, a non-empty bounded reason, and the submitted scope
   hash/version; lock or otherwise serialize the document and active operation lookup; recompute
   eligibility and the complete scope; and refuse stale or changed data with a fresh-preview
   response. Enqueue or reuse one idempotent execution with a safe target and no fiscal payload.
   Return only bounded operation state and IDs, never object keys or content. Operators,
   viewers, unauthenticated callers, retained items, and non-executable items must be rejected
   server-side.
4. Implement the saga as explicit checkpoints over the complete deletion set. Before removing
   anything, persist intent and the enumerated safe items. At every step re-check ownership,
   state, and expected digest/size/version; use the artifact service’s object-store abstraction
   rather than direct storage calls; make already-completed steps harmless on retry; and resolve
   protected document/event/artifact references in dependency order rather than bypassing
   constraints. A missing, divergent, or storage/database failure must stop at a resumable
   recovery-required or failed checkpoint, never become success, and must not delete unrelated
   data or source records silently.
5. Register the execution with the existing worker/lease and retry contract when asynchronous.
   Handle duplicate requests, two Administrators, worker death, lease loss, restart, retry
   exhaustion, and replay deterministically. Completion is allowed only after every scoped
   relational record and object-store byte has an idempotent terminal outcome and reconciliation
   proves there is no orphan or misleading document/evidence/artifact reference. Provide the
   safe resume/reconcile operation and document when the P9-02 backup/manual recovery procedure
   is required; do not implement automatic restore or delete backup data.
6. Add Administrator-only status and recovery UI around the existing retention view: display
   the exact preview scope, rule/date, artifacts, confirmation, reason, pending/executing,
   failed/recovery-required, and completed states. Reuse the existing document and session
   boundaries; return 403 without deletion metadata to other roles and do not expose raw
   exceptions, fiscal bytes, object keys, or a reusable confirmation credential.
7. Add deletion request, denial, stale-scope, execution, failure, recovery, completion, and
   orphan signals through `AuditService` and bounded metrics. `document.delete` must retain its
   required reason, audit-chain failures must prevent a critical operation from claiming
   success, and logs/audit/metrics/responses must redact fiscal content, object keys,
   credentials, tokens, and unbounded identifiers.
8. Add unit, integration, UI-contract, migration, and fault-injection coverage before
   implementation. Use only synthetic/anonymized fixtures and exercise retention boundaries,
   exact preview confirmation, every saga checkpoint, object/database failure, missing and
   divergent objects, retries/restarts/lease loss, concurrency, protected references,
   authorization, redaction, audit integrity, and no false success. Run the focused suites and
   the repository validation commands listed below.
9. On completion, update the retention/deletion operator and contributor documentation, run
   `graphify update .`, synchronize only the P9-03 evidence in `IMPLEMENTATION_PLAN.md`,
   `specs/p9-controlled-deletion.md`, and `specs/README.md`, fill this issue’s Resolution, and
   close the work in one focused commit. Do not claim P7-03 rendering, P8-02 expansion, backup
   automation, hardening, pilot/homologation, or real fiscal transport complete.

## Out of Scope

- Changing NF-e/NFS-e retention periods, eligibility ownership, preview semantics, or the
  requirement that deletion is never automatic.
- Deleting or rewriting companies, users, certificates, backups, audit history, unrelated
  documents, retained documents, collection jobs, cursors, or fiscal transport state.
- Automatic PostgreSQL/MinIO restore, physically separate backup placement, a new queue/broker,
  or a new object-store implementation.
- PDF renderer implementation, renderer conformance, document consultation/download redesign,
  ZIP behavior, dashboard expansion, P9-04 hardening, P9-05 pilot/homologation, or official
  fiscal network access.
- Bypassing foreign-key protection, exposing object-store URLs, accepting generic confirmation
  flags/tokens, logging fiscal contents, or unrelated frontend/application cleanup.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P9-03 Exclusão controlada, priority 2 in the current
  pending-work sequence.
- Canonical spec: `specs/p9-controlled-deletion.md` — P9-03, current repository revision
  2026-08-11. Its RET-005/RET-006/RET-008, AUD-006/AUD-008/AUD-009, AC-014/AC-015, state
  contract, and proposed saga/checkpoint design are authoritative.
- Direct prerequisites are P8-03 and P9-02, completed by issues 0019 and 0017. Issue 0006
  owns document identity/evidence; issue 0023 owns future PDF rendering and is related but does
  not block this deletion owner. P9-02’s verified backup and manual recovery procedure must
  remain intact.
- Data/migration: changes are additive and upgrade-safe. The operation owns deletion intent and
  checkpoints; retention owns eligibility, documents own identity/relationships, artifacts own
  bytes/metadata, and audit owns the permanent event chain.
- Compatibility/security: preserve current retention list/detail/preview behavior and existing
  role semantics; protect every mutating endpoint with server-side authorization and CSRF;
  revalidate state at execution and recovery; use only bounded safe payloads and synthetic test
  data.
- Observability/rollout: expose safe requested/blocked/failure/recovery/completed/orphan
  outcomes and make recovery-required visible to Administrators. A partial object/database
  operation is not a successful deletion and must remain actionable after restart.

## Tests

- **Unit:** eligibility and scope revalidation, reason/confirmation validation, operation state
  transitions, active-operation uniqueness, checkpoint idempotency, dependency ordering, safe
  error mapping, bounded payloads, authorization, redaction, audit reason enforcement, and
  recovery decisions.
- **Integration:** additive migration install/upgrade/rerun; Administrator versus operator,
  viewer, and unauthenticated request paths; exact stale-preview rejection; document/event/
  evidence/artifact cleanup; concurrent requests; object-store and database failures at every
  checkpoint; worker lease expiry/restart/retry; orphan detection; audit-chain integrity; and
  preservation of backups and unrelated data.
- **Frontend:** exact-scope confirmation, required reason, loading/pending, failed,
  recovery-required, completed, stale, forbidden, and safe-error states using the existing
  TypeScript/ESLint/build contract; do not add browser-test infrastructure.
- **Validation commands:** focused controlled-deletion/retention tests plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] An additive schema persists the deletion operation and resumable step/item checkpoints
  with the specified bounded states, preview scope hash/version, reason, actor, timestamps,
  and safe result/error data; clean install, upgrade, and migration rerun pass.
- [x] Only an authenticated Administrator with a current eligible decision, exact preview
  confirmation, and a non-empty bounded reason can create an operation; retained,
  non-executable, stale-scope, changed-scope, malformed, operator, viewer, and unauthenticated
  requests are rejected without mutation or deletion metadata leakage.
- [x] Confirmation is bound to one preview scope and cannot be reused generically; concurrent
  Administrators and retries resolve to one active decision per document without duplicate
  operations.
- [x] The operation treats the document, events/substitutions, original/XML evidence, PDFs,
  derived artifacts, relational links, and object-store bytes as one explicit deletion set, and
  completion leaves no orphan or misleading surviving record while preserving backups, audit
  history, unrelated documents, and retained data.
- [x] Saga checkpoints are durable and idempotent; worker death, lease loss, restart, duplicate
  delivery, retry exhaustion, and database/object-store failure never report success before all
  required steps are verified and never repeat a completed destructive step unsafely.
- [x] Missing, divergent, inaccessible, or partially removed objects produce a visible
  failed/recovery-required state with bounded reason codes and a safe resume/reconciliation path;
  the P9-02 verified backup and manual recovery runbook remain usable, and no automatic restore
  or backup deletion is introduced.
- [x] Every mutating path revalidates session, Administrator role, eligibility, scope, item
  state, and expected digest/size/version; CSRF and existing fail-closed policy boundaries are
  enforced, and no endpoint exposes fiscal content, object keys, credentials, tokens, or raw
  storage/provider exceptions.
- [x] Requests, denials, stale scopes, execution, failures, recovery, completion, and orphan
  outcomes are recorded in the append-only audit chain with the required reason and safe
  bounded context; audit failure prevents a critical deletion from claiming success, and
  metrics/logs contain no fiscal content or secrets.
- [x] Administrator UI shows the exact scope and all pending, executing, failed,
  recovery-required, completed, stale, and error states; non-Administrators receive no deletion
  controls or metadata.
- [x] Synthetic unit/integration/frontend-contract/fault-injection coverage passes for expected
  and negative behavior, data integrity, concurrency/idempotency, recovery, authorization, and
  redaction, along with `make lint`, `make test-unit`, `make test-integration`, `make build`,
  and `make smoke`.
- [x] Documentation, `IMPLEMENTATION_PLAN.md`, the P9-03 spec/index, Graphify metadata, and
  this issue’s Resolution are synchronized, and the issue is closed in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P9-03 Exclusão controlada.
- Spec: `specs/p9-controlled-deletion.md` — canonical eligibility handoff, deletion set,
  Administrator confirmation, saga/recovery states, audit requirements, and DoD.
- PRD: `PRD.md` — RET-005, RET-006, RET-008, AUD-006, AUD-008, AUD-009, AC-014, AC-015.
- Architecture: `ARCHITECTURE.md` — ownership/persistence, audit, XML/payload, retention,
  security, testing, failure recovery, and upgrade sections 14, 16, 17, 27, 28, 31, 33, 37,
  40, and 41.
- Related issues: `issues/0017_-_verifiable-backup-and-isolated-restore.md`,
  `issues/0019_-_retention-eligibility-and-preview.md`,
  `issues/0023_-_danfe-danfse-rendering.md`.

---

## Resolution

Implemented P9-03 in the canonical retention owner. Added migration `0020` and durable
`DeletionOperation`/`DeletionItem` checkpoints with an active-operation constraint; Admin-only
request/status/resume routes bound to the current `scope-v1` preview; verified artifact deletion
through `ArtifactStorageService`; and transactional cleanup of documents, events, evidence,
derived renders, export/collection/manifestation references, and artifact metadata. The worker
uses the existing lease/idempotency engine and reports recovery/failed outcomes without false
success. Audit contexts and metrics remain bounded and content-free, and the existing P9-02
backup/manual recovery boundary is unchanged.

Validation completed:

- `make lint` — Ruff, mypy, TypeScript, and ESLint passed.
- `make build` and `python backend/manage.py makemigrations nfx --check` — passed.
- `make test-unit` — 236 passed.
- `make test-integration` — 75 passed in isolated PostgreSQL/MinIO containers.
- `make smoke` — isolated web/worker/scheduler topology and health checks passed.

Documentation synchronized in `docs/OPERATIONS.md`, `docs/DEVELOPMENT.md`,
`IMPLEMENTATION_PLAN.md`, `specs/p9-controlled-deletion.md`, `specs/README.md`, and Graphify
outputs. The focused commit is titled `feat(retention): implement controlled fiscal document deletion (#0024)`.
