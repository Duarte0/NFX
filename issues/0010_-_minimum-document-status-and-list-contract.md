---
id: 0010
title: "Implement minimum document status and list contract"
type: feature
status: closed
priority: high
phase: P4
created_at: 2026-08-09
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0006, 0009]
blocked_by: []
affects:
  - backend/nfx/documents/
  - backend/nfx/urls.py
  - backend/nfx/collection/
  - frontend/src/
  - tests/
  - docs/
---

## Description

Deliver the P4-04 minimum read-only document status/list contract so authenticated users can see document metadata and explicit operational states without the UI inferring durable state from an empty response. The contract must remain compatible with the P4-02 ingestion pipeline and must not implement P7's searchable archive, detail, or download behavior.

Verified gap: issue 0006 delivered the `nfx.documents` models and persistence boundary, and issue 0005 already exposes collection execution states, but the repository has no document API route, document-list service/serializer, or rendered `#documentos` UI section. The frontend navigation currently links to `#documentos` and `#exportacoes` without a document section. Existing issue 0009 owns durable received-unit, checkpoint, and cursor progression; it does not cover P4-04 status/list presentation.

## Objective and Expected Outcome

Provide a bounded, authenticated, read-only endpoint and UI section that list the available document metadata for the permitted company/flow scope and represent loading, valid-empty, unavailable, no-coverage, unknown, partial, retry, blocked, persisted, quarantine, and conflict states explicitly. The UI must distinguish a valid empty result from unavailable or not-yet-covered collection data and must never manufacture a successful document state from missing data.

## Implementation Plan

1. Define the P4-04 response contract over the existing P4-01 `Document`, `DocumentEvent`, `DocumentEvidence`, company, and collection-flow boundaries. Return only bounded metadata and safe state/reason fields; keep artifact bytes, object keys, credentials, raw XML/PDF, and unredacted external errors out of responses. Preserve the eventual P4-02 page/unit/checkpoint state vocabulary through a documented adapter rather than duplicating durable state in the frontend.
2. Add a read-only document-list service and authenticated HTTP route using the repository's existing session/RBAC decorators and pagination conventions. Apply an explicit company/flow scope, deterministic bounded ordering, and safe parameter validation. Define response semantics for a valid query with zero documents, unavailable dependencies, no coverage, unknown state, partial/retry/blocked collection state, and document-level persisted/quarantine/conflict state; malformed or unauthorized requests must fail without leaking document existence.
3. Add the minimum React document section to consume the endpoint and show loading, valid-empty, unavailable, no-coverage, unknown, partial, retry, blocked, persisted, quarantine, and conflict states. Keep filters and behavior limited to this P4-04 slice; do not add P7 search, advanced filters, detail views, artifact download, exports, or client-side assumptions about cursor/checkpoint durability. Ensure the existing navigation anchor resolves to the section and the UI remains safe when the endpoint is empty or unavailable.
4. Integrate the response mapping with the collection status already exposed by P3-05 and leave an explicit compatibility seam for issue 0009's received-unit/checkpoint outcomes. Do not create a second cursor, checkpoint, ingestion state, retry policy, or document identity implementation. Keep all document and collection reads side-effect free; no document, artifact, job, or cursor mutation may occur during listing.
5. Add backend unit/integration tests for authentication and all roles, unauthorized access, invalid bounds/parameters, deterministic pagination, valid-empty versus unavailable/no-coverage/unknown states, document persisted/quarantine/conflict rendering, partial/retry/blocked collection states, safe field redaction, and no-write behavior. Add frontend validation coverage available in the repository for the rendered section, state labels, loading/error/empty branches, and the existing build/lint contract; use synthetic records only.
6. On completion, update the P4-04 evidence/status in `IMPLEMENTATION_PLAN.md`, the owning P4 spec and `specs/README.md` only according to their existing completion conventions, document the HTTP/UI state contract, refresh Graphify with `graphify update .`, update this issue's Resolution, and close the work in one focused commit.

## In Scope

- A read-only authenticated API and service for the minimum P4-04 document/status list.
- Explicit safe state mapping for document and collection outcomes required by the P4 spec.
- Bounded metadata serialization, deterministic pagination, authorization, redaction, and no-write guarantees.
- The minimum React document section, including loading, empty, unavailable, no-coverage, degraded, and explicit document outcome states.
- Unit/integration/API and available frontend build/lint validation with synthetic fixtures.

## Out of Scope

- P4-02 received units, page/checkpoint/cursor persistence, reconciliation, or ingestion orchestration; those remain in issue 0009.
- P4-03 user-facing failure resolution or a new failure-state matrix beyond the presentation contract required here.
- P7 search, advanced filters, detail/event navigation, individual artifact download, or archive behavior.
- ZIP/export, PDF/DANFE/DANFSe, retention, deletion, official fiscal transports, and real credentials or fiscal data.
- Client-side durable state, duplicate cursor/checkpoint ownership, writes triggered by a read, or unrelated frontend cleanup.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P4-04, minimum status/list contract; P4-01 is complete and P4-02/P4-03 remain separate work.
- Canonical spec: `specs/p4-fiscal-document-ingestion-and-integrity.md` — P4-04, current repository version (the spec has no explicit version field), especially “Contratos, frontend e autorização”, “Segurança, auditoria e observabilidade”, and the P4-04 portion of the DoD.
- Completed dependency: issue 0006 provides the document identity, metadata, evidence, replay, quarantine, and conflict persistence boundary. Related open work: issue 0009 provides the future durable ingestion/checkpoint state and must remain the sole owner of that progression.
- Data/migration: prefer existing P4-01/P3-05 fields and indexes; add only an additive migration if the approved P4-04 contract proves a required persisted status/index gap. Clean install and upgrade must converge.
- Compatibility: all three authenticated roles may read the permitted global document scope under the existing policy; anonymous and revoked sessions are rejected. The endpoint must tolerate no ingested documents and later consume P4-02 states without changing its public meaning.
- Security/observability: validate and bound all query inputs; return safe reason codes and bounded IDs/digest prefixes only; audit the read if required by the existing audit contract without storing payload content; expose no object-store key or raw external error.

## Tests

- **Unit:** serialization/state mapping, parameter bounds, deterministic ordering/cursor behavior, redaction, valid-empty versus unavailable/no-coverage/unknown semantics, and no-write guarantees.
- **Integration:** authenticated API access for all roles, anonymous/revoked rejection, document persisted/quarantine/conflict data, collection partial/retry/blocked states, pagination, migration/index coverage if schema changes, and audit/read failure behavior.
- **Frontend:** exercise the document section's loading, valid-empty, unavailable, no-coverage, unknown, degraded, and document outcome branches using the repository's available TypeScript lint/build checks and synthetic API responses.
- **Validation commands:** run focused tests plus `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] An authenticated, read-only document/status endpoint returns the documented bounded metadata and explicit state contract; it performs no document, artifact, job, collection, or cursor writes.
- [x] Anonymous users and revoked/invalid sessions are rejected consistently, and all allowed authenticated roles receive only the permitted scope without document-existence leakage on unauthorized requests.
- [x] Query parameters, limits, cursors, ordering, and identifiers are validated and bounded; invalid input produces a safe client error and cannot trigger unbounded queries.
- [x] The response distinguishes valid-empty, unavailable, no-coverage, unknown, partial, retry, and blocked collection states from persisted, quarantine, and conflict document outcomes.
- [x] Existing P4-01 persisted metadata, competence, family/flow, situation, source, and safe evidence availability are represented without exposing raw payload bytes, object keys, secrets, or unredacted errors.
- [x] Pagination/order is deterministic, replaying a read does not mutate durable state, and concurrent reads do not alter document, artifact, job, or collection records.
- [x] The UI renders the existing `#documentos` navigation target and all required loading, empty, unavailable, no-coverage, unknown, degraded, persisted, quarantine, conflict, partial, retry, and blocked states without inferring success from an empty payload.
- [x] The implementation has a documented compatibility mapping for issue 0009's future received-unit/checkpoint outcomes and does not duplicate ingestion, identity, retry, or cursor ownership.
- [x] Tests cover expected, negative, authorization, redaction, pagination, no-write, and state-mapping behavior with synthetic fixtures; configured backend and frontend validation commands pass without regressions.
- [x] Completion synchronizes `IMPLEMENTATION_PLAN.md`, the owning P4 spec/index evidence, relevant documentation, Graphify, this issue's Resolution, and one focused commit; P4-02/P4-03/P7 behavior is not claimed complete.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P4-04 minimum document status/list contract.
- Spec: `specs/p4-fiscal-document-ingestion-and-integrity.md` — P4-04 API/UI authorization, explicit states, redaction, and DoD; current repository version.
- Related completed work: `issues/0006_-_fiscal-document-identity-and-persistence.md` and `issues/0005_-_manual-collection-control.md`.
- Related open work: `issues/0009_-_durable-ingestion-pipeline-and-cursor.md` — P4-02 owner; no duplicate cursor/checkpoint/ingestion behavior here.
- Current boundaries: `backend/nfx/documents/`, `backend/nfx/collection/`, `backend/nfx/urls.py`, and `frontend/src/main.tsx`.

---

## Resolution

Implemented P4-04 with `GET /api/documents` and the React `#documentos` section. The bounded,
authenticated read maps the existing company-flow and ingestion-page states to explicit
`valid_empty`, `unavailable`, `no_coverage`, `unknown`, `partial`, `retry`, and `blocked` values;
lists safe document metadata and quarantined units; and serializes persisted/conflict outcomes
without artifact keys, bytes, secrets, or raw errors. UUID pagination is deterministic and the
read path has no writes or duplicate ingestion/cursor ownership.

Added unit coverage for state mapping and parameter validation plus PostgreSQL integration coverage
for authentication, all roles, invalid bounds, empty state, metadata redaction, quarantine/conflict,
pagination, blocked state, and no-write behavior. Updated the P4 spec/index, implementation plan,
development documentation, and Graphify metadata. Validation: `make lint`, `make test-unit` (142
passed), `make test-integration` (40 passed after the final test additions), `make build`, and
`make smoke` all passed. No migration was required. This resolution does not claim P4-03 or P7.
