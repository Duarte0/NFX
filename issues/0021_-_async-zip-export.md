---
id: 0021
title: "Implement resumable asynchronous ZIP export"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-10
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0001, 0004, 0006, 0010, 0015]
blocked_by: []
affects:
  - backend/nfx/exports/
  - backend/nfx/jobs/
  - backend/nfx/documents/
  - backend/nfx/artifacts/
  - backend/nfx/identity/
  - backend/nfx/audit/
  - backend/nfx/urls.py
  - frontend/src/
  - tests/
  - docs/
---

## Description

Implement the independently valuable P8-01 asynchronous ZIP export contract. The current
repository supports bounded document consultation and integrity-checked individual downloads,
but has no export request, frozen selection, resumable composition job, temporary ZIP artifact,
or ownership-aware export download. The implementation must compose only the existing P7
selection and artifact boundaries and must not alter the fiscal archive.

## Objective and Expected Outcome

An authenticated user can request a ZIP from the approved document filters, receive a durable
export record and idempotent job, observe progress or a safe partial/failure state, and download
the result only while it is available and unexpired. The worker uses the selection captured at
request time, verifies each source artifact before inclusion, resumes after lease loss without
duplicate entries, and never presents an incomplete archive as complete. Administrators may
inspect and download other users' exports; Operators and Visualizers may access only their own
permitted exports according to the canonical authorization contract. Temporary ZIP bytes expire
after 24 hours and cleanup never removes fiscal source artifacts.

The verified gap is the P8-01 row in `IMPLEMENTATION_PLAN.md` and the unchecked P8-01 contract
in `specs/p8-zip-export.md`; issue 0015 explicitly left ZIP/export outside its P7-01/P7-02
delivery. `Action.CREATE_ZIP`, `Action.DOWNLOAD_OWN_ZIP`, and `Action.DOWNLOAD_ANY_ZIP` already
exist as policy vocabulary, but no export owner or route implements them.

## In Scope

- An export-owned durable request/selection/item contract with the state model from the spec:
  `pending`, `processing`, `complete`, `partial`, `failed`, `available`, `expired`, and
  `excluded`, including frozen filter/snapshot data, expected/produced counts, byte totals,
  safe result/error, expiry, job, and ZIP artifact references.
- Request validation using exactly the existing P7 bounded filters and server-side role policy;
  persist the canonical selection before enqueueing work and make repeated requests idempotent
  only for the chosen request key, without preventing intentional new requests.
- A resumable job handler that reads the frozen selection, verifies source artifact state,
  digest, and size through the artifact owner, writes a deterministic safe ZIP structure using
  sanitized non-colliding paths, and records item-level completeness/failure without exposing
  fiscal content in relational records, jobs, logs, metrics, or audit context.
- Safe partial, failed, missing-source, object-divergence, worker-restart, lease-reclaim, and
  cleanup behavior. A ZIP is downloadable as complete only after all selected artifacts are
  confirmed; absent or failed items are explicitly represented as partial/unavailable.
- Ownership/admin list, detail/progress, download, and idempotent expiration cleanup contracts;
  server-side revalidation of session, ownership/admin access, availability, and expiry on every
  read. Add the corresponding frontend export states using the existing feature/shared HTTP
  boundaries.
- Bounded audit and metrics for request, denial, job completion/partial/failure, download, and
  expiry/cleanup, plus contributor/operator documentation for the ownership and temporary-data
  lifecycle.

## Implementation Plan

1. Map `specs/p8-zip-export.md` to a new `nfx.exports` boundary while reusing the P7 document
   consultation/filter parser, P3 `JobEngine`/lease handler registry, existing identity policy,
   `ArtifactStorageService`, audit service, redaction, and bounded metrics patterns. Preserve
   P7 filter semantics and choose only local Proposed details needed for the API, snapshot, and
   idempotency representation; do not invent new search filters or a second authorization path.
2. Define additive export persistence and constraints for request ownership, frozen selection,
   item/document-artifact identity, state transitions, expected/produced counts, expiry, and
   active idempotency. Ensure a clean migration and upgrade/rerun behavior, no destructive
   rewrite, and no raw XML/PDF/object bytes or object-store keys in database fields intended for
   public/job/audit use. Keep original fiscal artifacts outside export cleanup ownership.
3. Implement the request flow as an atomic record-plus-selection operation followed by durable
   job enqueue. Validate authenticated role, bounded limits, date/competence/search values,
   selected-document visibility, and storage/export quotas before persisting. A concurrent or
   retried request with the same idempotency key returns the existing export/job; a different
   explicit request remains distinct. The worker must revalidate the captured references and
   never expand the scope when new documents arrive.
4. Implement resumable composition with a deterministic item order and sanitized path builder.
   For each item, read through verified artifact storage, enforce configured input/output and
   entry limits, stream or stage safely into the temporary ZIP, and checkpoint progress so a
   reclaimed lease resumes without duplicate entries or false completion. Handle Unicode,
   traversal markers, empty/colliding names, missing or divergent objects, absent optional PDF,
   storage interruption, and archive-size/item-count limits using safe bounded reason codes.
   Finalize the ZIP artifact only after integrity verification; otherwise retain a safe partial
   or failed result for reconciliation and retry according to the captured job policy.
5. Add HTTP/UI boundaries for create, list/detail/progress, download, and expiration/cleanup
   operations. Enforce that only the requester or Administrator can list/download an export,
   recheck session/ownership/admin role and `available` plus expiry at download time, return
   uniform safe errors, and never expose object keys, source payloads, provider errors, or
   another user's export existence. Cleanup must be idempotent, remove only temporary ZIPs and
   export records/artifacts allowed by the export lifecycle, and preserve every source document,
   evidence artifact, cursor, and collection state.
6. Add audit and metrics with bounded labels (state, outcome, counts, sizes, duration, reason,
   role, and safe correlation) and redact all request/filter context before persistence. Add
   unit and integration tests before implementation for authorization, frozen selection,
   idempotency/concurrency, path safety, integrity, limits, partial-vs-complete behavior,
   restart/lease recovery, expiration boundaries, cleanup, audit/redaction, no source mutation,
   and PDF-unavailable behavior. Run focused export tests plus `make lint`, `make test-unit`,
   `make test-integration`, `make build`, and `make smoke`.
7. Document the P8-01 API, state machine, temporary retention, limits, and ownership boundary;
   run `graphify update .`; synchronize the P8-01 evidence in `IMPLEMENTATION_PLAN.md`, the
   owning spec/index, and this issue's Resolution, then close in one focused implementation
   commit. Do not mark P7-03 rendering, P9-03 deletion, or any source/transport work complete.

## Out of Scope

- PDF/DANFE/DANFSe rendering or renderer selection. PDF is included only when a selected,
  already-finalized artifact exists; its absence must remain explicit and must not block XML or
  original export unless the selected item requires it under the spec.
- New document filters, CSV/Excel/reports, public APIs, presigned/direct object-store URLs,
  fiscal transport, manifestation, ingestion/cursor changes, retention decisions, or controlled
  deletion of source documents.
- Automatic widening of a frozen selection, silent omission of selected items, treating partial
  output as complete, or cleanup of source fiscal artifacts.
- A new queue/broker, alternative archive, unapproved quota/threshold policy, or unrelated
  frontend refactor. Proposed local limits must be configurable, bounded, documented, and tested.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-01 asynchronous ZIP export; P8-02 initial dashboard
  and P8-03 retention are separate slices. P7-01/P7-02 are complete in issue 0015.
- Canonical spec: `specs/p8-zip-export.md`, current repository revision, including its metadata,
  selection/state contracts, authorization, security, observability, recovery, and acceptance
  sections. Product references are FR-ZIP-001..003, BR-ZIP-001..004, NFR-006, AUD-006, AC-012,
  and AC-014; architecture reference is ADR-011 and its cited sections.
- Direct implementation boundaries: issue 0001 owns durable jobs/leases; issue 0006 owns
  document identity/evidence; issue 0010 owns the minimum document contract; issue 0015 owns
  bounded consultation and individual download; `nfx.artifacts` owns object bytes and integrity;
  `nfx.identity` owns server-side authorization.
- Data/migration: prefer additive export tables and indexes keyed by requester/state/expiry and
  document/item references. Any migration must prove clean install, forward upgrade, rerun, and
  rollback-safe non-destructive behavior. The ZIP artifact must use a distinct temporary logical
  class and expiry lifecycle so retention/deletion cannot mistake it for fiscal evidence.
- Compatibility: retain existing `/api/documents` filters and response semantics; export request
  payloads may reuse their validation but must not expose database IDs or object-store keys as
  archive paths or public storage references.
- Security/rollout: simulator/synthetic fixtures only; enforce traversal, Unicode/collision,
  entry-size, total-size, count, compression, and expiration limits; do not log/archive XML,
  PDF, credentials, tokens, raw filters, or provider errors.

## Tests

- **Unit:** filter/snapshot canonicalization, role/ownership decisions, idempotency keys and
  concurrent request resolution, path sanitization/collision handling, ZIP limits, state
  transitions, safe filenames/errors, expiry boundaries, cleanup selection, redaction, and
  bounded metrics.
- **Integration:** migration clean install/upgrade/rerun, request/list/detail/download routes,
  frozen selection despite new documents, requester/Admin/Operator/Viewer access, verified
  artifact composition, missing/divergent source, partial/failed output, duplicate/concurrent
  requests, worker crash/lease reclaim/restart, object cleanup, source immutability, audit
  chain, and no object-key/content disclosure.
- **Frontend:** export request, list/detail/progress, complete/partial/failed/expired states,
  safe download, loading/error/degraded states, and existing document consultation regression;
  use the repository's configured TypeScript/ESLint/build checks because no browser runner is
  currently configured.
- **Validation commands:** focused export/job/document/artifact tests plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A valid authenticated request accepts only the approved P7 filters, freezes and persists
  its selection before enqueueing a durable job, and rejects malformed, excessive, unauthorized,
  or unsupported input without a fiscal side effect.
- [x] Repeating the same request idempotency key, including concurrent requests, resolves to one
  export/job; intentionally different requests remain independent and no duplicate export items
  or ZIP entries are created.
- [x] The worker uses only the frozen selection, resumes after interruption/lease reclaim, and
  never advances or mutates document, evidence, artifact, cursor, checkpoint, or collection
  state.
- [x] Source artifacts are verified for finalized state, digest, and size before inclusion;
  missing, divergent, unavailable, or optional-PDF-absent inputs become explicit safe item
  outcomes rather than silently disappearing.
- [x] Archive paths are deterministic, sanitized against traversal, bounded for Unicode and
  collisions, and obey configured item, entry, output-size, and compression/resource limits.
- [x] An export is marked complete/downloadable only when every selected required artifact is
  confirmed; partial, failed, processing, and expired exports are never served as complete ZIPs.
- [x] Only the requester or Administrator can inspect/download an export, every download
  revalidates session, ownership/admin access, availability, and expiry, and unauthorized or
  expired requests do not disclose export existence or object-store keys.
- [x] Expiration at the defined 24-hour boundary and repeated cleanup remove only temporary ZIP
  output/export lifecycle data, preserve all fiscal source artifacts, and are safe to retry.
- [x] Jobs, logs, audit events, metrics, HTTP responses, and frontend state contain no XML/PDF,
  raw payload, credentials, tokens, provider exception text, or unbounded identifier/filter
  labels; audit and metrics remain bounded and redacted.
- [x] Synthetic unit/integration/frontend-contract tests cover expected and negative behavior,
  data integrity, retry/restart/idempotency/concurrency, security/config limits, and all listed
  validation commands pass.
- [x] Documentation, `IMPLEMENTATION_PLAN.md`, the P8 spec/index, Graphify metadata, and this
  issue's Resolution are synchronized, and the issue is closed in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-01 asynchronous ZIP export.
- Spec: `specs/p8-zip-export.md` — canonical contracts, limits, failures, security, and DoD.
- Related issues: `issues/0001_-_durable-job-queue-and-leases.md`,
  `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0010_-_minimum-document-status-and-list-contract.md`,
  `issues/0015_-_document-consultation-and-secure-individual-download.md`.
- Current boundaries: `backend/nfx/jobs/`, `backend/nfx/documents/`,
  `backend/nfx/artifacts/`, `backend/nfx/identity/`, `backend/nfx/audit/`, and
  `frontend/src/features/documents/`.

---

## Resolution

Implemented the P8-01 `nfx.exports` boundary with additive migration `0018`, frozen P7
selection/items, idempotent durable `export.zip` jobs, verified temporary ZIP composition,
safe partial/failure states, 24-hour expiry cleanup, ownership/Admin download checks, audit,
bounded metrics, API/UI states, and operator documentation. Source fiscal artifacts remain
outside the temporary export lifecycle.

The validation blocker was corrected in the existing document-consultation integration test:
the endpoint orders UUIDs deterministically, while the test had assumed creation order for random
UUIDs. The revised assertion follows the established ordering contract.

Validation passed on 2026-08-11:

- `python -m pytest tests/unit/test_exports.py tests/unit/test_export_metrics.py` — 3 passed.
- `make test-integration` — 72 passed, including migration install/schema checks.
- `make lint` — Ruff, mypy, TypeScript, and ESLint passed.
- `make test-unit` — 230 passed.
- `make build` — Django check and frontend production build passed.
- `make smoke` — isolated Docker runtime smoke passed.

Documentation synchronized: `docs/EXPORTS.md`, `specs/p8-zip-export.md`, `specs/README.md`,
`IMPLEMENTATION_PLAN.md`, and Graphify metadata.
