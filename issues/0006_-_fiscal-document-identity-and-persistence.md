---
id: 0006
title: "Implement fiscal document identity and persistence foundation"
type: feature
status: closed
priority: critical
phase: P4
created_at: 2026-08-09
updated_at: 2026-08-09
closed_at: 2026-08-09
related_issues: [0003]
blocked_by: []
affects:
  - backend/nfx/documents/
  - backend/nfx/artifacts/
  - backend/nfx/companies/
  - backend/nfx/audit/
  - backend/nfx/migrations/
  - tests/unit/
  - tests/integration/
  - docs/
---

## Description

Deliver P4-01 from the canonical fiscal-ingestion contract: a durable relational identity model for fiscal documents, events, and their safe relationships, backed by the existing company and artifact boundaries. The current `backend/nfx/documents/` package is only an empty boundary; no document/event records, fiscal identity normalization, conflict-preserving uniqueness, competence derivation, or service-level persistence contract exists. The P3 simulators intentionally stop before P4 persistence, so no document result is currently durable or queryable.

The implementation must establish the data foundation that P4-02 can use without inventing fiscal identity from internal UUIDs. It must use only synthetic fixtures and simulator-shaped inputs, preserve immutable originals through artifact references, and keep raw XML, credentials, certificate material, and unredacted external errors out of relational job/document metadata.

## Objective and Expected Outcome

Provide validated document and event persistence services that classify a unit by its strongest available official identity and context, derive competence from emission, link events/substitutions without changing the parent document’s competence, and expose deterministic outcomes for persisted, replayed, quarantined, and conflicting identity attempts. PostgreSQL constraints and indexes must enforce the core invariants under concurrent requests, while the existing artifact service remains the owner of bytes, hashes, versions, and object-storage reconciliation.

This issue creates the P4-01 foundation only. P4-02 will own page/unit/checkpoint/cursor transaction sequencing; P4-03 will own the complete failure-state surface; P4-04 will own the list/status API and UI.

## Implementation Plan

1. Translate the `p4-fiscal-document-ingestion-and-integrity.md` Proposed schema into document-owned relational contracts for company, fiscal family, role/category, source/flow context, normalized external identity, emission/authorization timestamps, derived competence, situation, and origin execution reference. Add event/substitution records with explicit parent linkage and a safe relationship type. Keep physical names local to the implementation, but make ownership boundaries and stable service contracts explicit; do not use an internal UUID, object key, filename, or arrival time as fiscal identity.
2. Define the input/context and result types for the document boundary. Require enough identity/context to select the strongest official identity available; route insufficient identity to a quarantine result rather than manufacturing a key. Normalize identifiers and canonical comparable fields before uniqueness checks, validate timezone-aware dates and derive competence only from emission, and reject unsupported or malformed values with safe domain errors.
3. Implement transactional persistence for a document/event and its artifact reference. Enforce that the original artifact is immutable and referenced by internal artifact identity, that an event cannot silently become a document or attach to a missing/incompatible parent, and that a substitution records its relationship without rewriting the parent. Preserve source execution/correlation references as bounded safe identifiers only.
4. Add database constraints and indexes for the strongest identity plus required context, document/event relationship integrity, competence/emission/identifier/situation/direction/category lookups, and immutable or append-only evidence where applicable. The same normalized identity with the same content hash must return a replay without a duplicate; the same identity with a different hash must retain both evidence references and return a conflict outcome without overwriting either record. Handle concurrent insertion by relying on the database constraint and translating the resulting race into the same deterministic outcome.
5. Integrate the service with existing company, artifact, audit, redaction, and model-registration boundaries without adding fiscal transport calls or changing P3 simulator semantics. Audit document persistence, replay, quarantine, and conflict with safe IDs/codes and partial hashes only; logs and error responses must never contain payload bytes, XML/PDF, certificates, tokens, credentials, object contents, or raw external exceptions.
6. Add migration-upgrade/install coverage and focused unit/integration tests using reserved synthetic companies, identifiers, dates, hashes, and artifact records. Keep this issue independent of cursor advancement and page completion: tests may call the document persistence contract directly and must prove it is safe to retry and race, but must not imply that a collection cursor advanced.
7. On completion, update the P4-01 evidence/status in `IMPLEMENTATION_PLAN.md`, the P4 spec and `specs/README.md` only according to their existing completion conventions, add the focused persistence contract to the relevant development documentation, refresh Graphify with `graphify update .`, update this issue’s Resolution, and commit the complete change as one focused commit.

## In Scope

- Fiscal document identity, normalized identity context, competence/emission/situation metadata, and document-owned relationships.
- Event and substitution records with validated optional parent links and safe origin references.
- Additive PostgreSQL migration, constraints, indexes, model/service contracts, and artifact-reference integration.
- Deterministic persisted/replay/quarantine/conflict outcomes and concurrency-safe duplicate handling.
- Redacted audit/logging hooks and unit/integration/install-upgrade tests for this foundation.

## Out of Scope

- P3-05 collection controls, manual endpoints, execution creation, or UI.
- P4-02 received-unit/page/checkpoint models, object-before-database sequencing, cursor/NSU advancement, or reconciler orchestration.
- P4-03 complete partial/empty/degraded/quarantine workflow and recovery state machine beyond the identity-insufficient and identity-conflict outcomes needed by this service.
- P4-04 document listing/status API, browser UI, advanced search, download, PDF, ZIP, retention, or exports.
- Official fiscal adapters, network calls, production endpoints, real certificates/CNPJs/XML, parser hardening beyond input validation needed by this contract, and changes to P3 simulator scenarios.

## Data, Migration, Compatibility, Security, and Observability Notes

- Use an additive migration and preserve all existing P0–P3 tables and artifact semantics. A clean install and upgrade from the current migration head must produce the same constraints and indexes.
- Do not duplicate artifact bytes or make object storage transactional with PostgreSQL. Store only the internal artifact reference plus verified metadata needed by the document contract; leave pending/finalized/missing/divergent reconciliation to `ArtifactStorageService`.
- Treat all fiscal-unit fields as untrusted input. Apply bounded lengths, allowlisted enums, timezone-aware date handling, safe error codes, and the established redaction boundary. Never persist raw response content or secrets.
- Use bounded metric/log/audit labels and safe identifiers; document persistence failures must not be reported as successful persistence or conceal a conflict.
- Existing callers that do not use the new document boundary must retain their behavior; no cursor or job transition may be introduced as a side effect of this issue.

## Tests

- **Unit:** normalization and strongest-identity selection; competence derivation from emission; invalid/insufficient identity; event-parent and substitution rules; result classification; redaction of payload-like values.
- **Integration:** migration schema/constraints/indexes; persisted document and event with artifact reference; same identity and hash replay; same identity with different hash conflict preserving both records; concurrent duplicate creation; missing/incompatible parent rejection; immutable artifact/reference behavior; audit/log safety.
- **Upgrade/failure:** clean migration and upgrade from the current head; database constraint race translated deterministically; failed persistence leaves no partially committed document relation.
- **Validation commands:** `make lint`, `make test-unit`, `make test-integration`, and the repository’s configured synthetic `make smoke`/`make validate` checks.

## Acceptance Criteria

- [x] P4-01 document and event persistence contracts are implemented behind the `nfx.documents` boundary and are registered in the application model/migration graph.
- [x] A document’s normalized identity uses the strongest available official identifiers plus the required company/family/role/source/flow context; internal UUIDs, object keys, filenames, and collection time are never used as fiscal identity.
- [x] Competence is derived from the validated emission timestamp, is stored/queryable with timezone-safe semantics, and is never changed by an event or later collection attempt.
- [x] Events and substitutions require a valid compatible parent when the contract requires one, preserve relationship type and origin evidence, and cannot silently overwrite or convert the parent document.
- [x] The same normalized identity and content hash is an idempotent replay with no duplicate document/event/evidence relation.
- [x] The same normalized identity with a different content hash returns a conflict and preserves both evidence references without overwriting either record.
- [x] Insufficient identity, malformed values, missing/incompatible parents, and unsupported classifications return safe deterministic outcomes and do not create a falsely identified document.
- [x] Database constraints and concurrent integration tests prevent duplicate logical identity and translate uniqueness races into the documented replay/conflict behavior.
- [x] The migration is additive, passes clean-install and upgrade checks, and leaves P0–P3 behavior and artifact lifecycle constraints intact.
- [x] No persisted model, log, audit context, metric label, or error response contains raw XML/PDF/payload bytes, certificates, tokens, credentials, object contents, or unredacted external exception text.
- [x] The implementation does not advance a cursor, checkpoint, job, or collection execution as a side effect; P4-02 remains the owner of that sequencing.
- [x] Focused unit, integration, migration, concurrency, and redaction tests pass, and the configured `make lint`, `make test-unit`, `make test-integration`, and synthetic smoke/validation commands pass.
- [x] Relevant documentation, `IMPLEMENTATION_PLAN.md`, the P4 spec/`specs/README.md`, and Graphify are synchronized according to repository conventions.
- [x] The issue is closed only after its Resolution records the implementation/evidence, `IMPLEMENTATION_PLAN.md` is synced, and all changes are committed in one focused commit.

## References

- Spec: `specs/p4-fiscal-document-ingestion-and-integrity.md` (current repository version; no explicit version field)
- Plan item: `IMPLEMENTATION_PLAN.md` — P4-01 Identidade fiscal e persistência
- Architecture: `ARCHITECTURE.md` — sections 15–19; ADR-003/004/007
- Product requirements: `PRD.md` — BR-INT-001..008, FR-DOC-001/005, AC-005..009 and AC-017 as mapped by the canonical spec
- Dependencies: completed P3 simulator contract in issue 0003; existing company, certificate, artifact, audit, and migration foundations
- Follow-up dependencies: P4-02, P4-03, and P4-04 consume this foundation

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
Implemented P4-01 behind `nfx.documents` with the additive migration
`0011_document_documentevent_documenteventevidence_and_more`. Added relational models for
documents, immutable artifact evidence, events and substitutions; normalized strongest-identity
selection; timezone-aware emission/competence derivation; safe bounded origin references; and
transactional services returning persisted, replay, quarantine, or conflict outcomes. Conflicting
hashes retain both artifact references, while event parents are required and checked for company
and family compatibility. No cursor, checkpoint, execution, job, transport, or artifact bytes are
changed by this boundary.

Added focused unit, integration, migration-install, constraint/index, audit-safety, replay/conflict,
parent-validation, and concurrent-identity tests using synthetic values only. Updated the P4 spec
evidence, implementation plan, development contract, specs index, and Graphify metadata.

Validation performed:

- `python -m pytest tests/unit/test_document_identity.py tests/integration/test_documents.py tests/integration/test_migrations.py` — 15 passed.
- Targeted Ruff and mypy checks — passed.

Repository validation completed:

- `make lint` — Ruff, mypy, TypeScript, and ESLint passed.
- `make test-unit` — 126 passed.
- `make test-integration` — isolated PostgreSQL/MinIO run, 29 passed.
- `make build` with the repository's documented synthetic test profile — Django check and frontend build passed.
- `make smoke` — isolated service startup, migration, and web/worker/scheduler liveness passed.
- `graphify update .` — code graph rebuilt and the new document boundary is queryable.

The plain `make build` invocation still fails closed when `NFX_PROFILE` is absent; this is the
separate reproducible-build contract tracked by issue 0008. The configured synthetic build path
passes and no production credentials, fiscal endpoints, or non-ephemeral data were used.
