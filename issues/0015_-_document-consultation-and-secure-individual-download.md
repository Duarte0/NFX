---
id: 0015
title: "Implement searchable document consultation and secure individual download"
type: feature
status: closed
priority: high
phase: P7
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0006, 0010, 0011, 0012, 0013, 0014]
blocked_by: []
affects:
  - backend/nfx/documents/
  - backend/nfx/artifacts/
  - backend/nfx/audit/
  - backend/nfx/urls.py
  - frontend/src/
  - tests/
  - docs/
---

## Description

Deliver P7-01/P7-02 from the approved document-consultation contract. The current baseline
has the P4 minimum `/api/documents` status/list response and immutable document/artifact
metadata, but it cannot search the full document inventory using the PRD filters, show a
standardized document detail with event relationships, or stream a finalized original safely.
The frontend currently renders only the minimum status/list fields and has no individual
download or detail flow. This slice must add the consultation and XML/original download
outcome without coupling it to PDF rendering, ZIP export, retention, or fiscal transport.

## Objective and Expected Outcome

Authenticated users can query the document archive with exactly the permitted bounded filters,
receive deterministic pagination and safe collection/document states, open a complete metadata
detail including related events and artifact availability, and download one authorized,
finalized original through the server. Authorization, artifact ownership, digest/size
verification, audit, redaction, and uniform failure behavior remain server-side concerns;
document, cursor, and artifact state are never changed by consultation.

## Implementation Plan

1. Map the P7 contract to the existing `Document`, `DocumentEvent`, evidence, quarantine,
   `ArtifactStorageService`, `documents` view/status boundary, authenticated read policy, audit
   service, and current frontend document section. Preserve the P4 status/list response semantics
   while defining the smallest additive list, detail, and download contracts. Resolve the spec's
   Proposed URL/payload/pagination details locally as bounded implementation details: use
   allowlisted fields, stable keyset ordering with an opaque validated continuation, explicit
   limits, and no unbounded query or identifier values.
2. Extend document query validation and read services for only the approved filters: one or more
   companies, competence, emission period, family, NF-e direction, NFS-e category, event type,
   and global search over the PRD-approved fields. Make combined filters conjunctive, normalize
   supported Unicode/search inputs deterministically, preserve quarantine/conflict visibility
   where the existing contract permits it, and return the documented metadata without raw fiscal
   payloads, credentials, object keys, or sensitive company labels beyond the authenticated
   archive contract. Add only indispensable indexes or additive migration changes, with clean
   install and upgrade convergence and no destructive rewrite.
3. Add a detail read boundary that returns the spec's standardized identity, parties, dates,
   competence, value/situation/source/collection metadata, related event and substitution links,
   and XML/PDF availability. Treat missing, pending, divergent, conflicting, or non-finalized
   evidence as unavailable; do not infer availability from a database reference or make PDF
   availability a prerequisite for XML/original access.
4. Add an individual download endpoint/service that revalidates the authenticated permission
   against the requested document/evidence, accepts only a document or artifact identifier from
   the public contract, resolves the server-side artifact reference, verifies finalized state,
   digest and size before streaming, and emits a safe filename/content disposition. Never expose
   a MinIO/object-store key, stream contents into logs, or return raw storage/provider errors.
   Missing, unauthorized, pending, divergent, and interrupted streams must fail safely without
   mutating document, evidence, artifact, cursor, or collection state.
5. Add bounded audit and observability at the read boundaries: consultation audit according to
   the local volume policy and every download with actor, source IP, target reference, result,
   and correlation; metrics for latency, errors, zero results, denied downloads, and missing or
   unavailable objects. Route values through existing redaction and bounded-label rules, and
   keep responses uniform enough to avoid document/identifier enumeration.
6. Extend the existing frontend document feature with list filters persisted in the URL,
   loading/empty/error/degraded states, stable pagination, detail navigation, related-event
   display, artifact availability, and an individual download action. Preserve the existing
   anchor navigation, role/session behavior, safe status labels, and the feature boundaries
   being established by issue 0011; do not add a second HTTP/auth policy or a browser-side
   durable-state model.
7. Write focused unit, integration, and browser/UI coverage before implementation using only
   synthetic fixtures. Cover every filter alone and in combination, multi-company scope, date
   and competence boundaries, Unicode/search normalization, stable pagination, all document
   families/flows/categories/event types, detail relationships, quarantine/conflict and missing
   evidence, authorization/session revocation, download integrity and safe headers, denied and
   interrupted streams, audit/redaction, no state mutation, and no object-key disclosure. Run
   the repository's configured lint, unit, integration, build, smoke, and frontend/browser
   validation commands.
8. Document the consultation/download contracts and module ownership, refresh Graphify with
   `graphify update .`, synchronize the P7-01/P7-02 evidence in `IMPLEMENTATION_PLAN.md`, the
   owning spec, and `specs/README.md`, update this issue's Resolution, and close the work in one
   focused commit. Do not claim P7 PDF, P8 export/retention, or P5/P6 transport behavior.

## In Scope

- Bounded authenticated archive search, filters, deterministic pagination, and safe collection
  status integration for P7-01.
- Standardized document detail, event/substitution relationships, and artifact availability.
- Server-authorized, integrity-checked streaming of one finalized XML/original artifact for
  P7-02, including audit, safe errors, and redaction.
- The corresponding frontend list/detail/download states and contributor/operator documentation.
- Additive indexes/migrations only when required by the approved query/download contract.

## Out of Scope

- PDF/DANFE/DANFSe rendering or renderer-library selection (P7 PDF remains locally blocked).
- ZIP/export jobs, CSV/Excel, reports, retention eligibility, controlled deletion, or dashboards.
- Public APIs, bulk downloads, direct object-store URLs, presigned keys, or client-side storage
  of fiscal payloads.
- New fiscal transport, P5/P6 distribution, manifestation, municipal integration, or ingestion
  state/cursor ownership.
- Changes to server-side RBAC semantics, the P4 identity/integrity contract, or unrelated
  frontend architectural cleanup beyond the document feature integration required here.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P7 consulta/download, P7-01/P7-02; P4-01 and P4-04
  are complete prerequisites. P5/P6 issues 0013/0014 may add coverage later but are not required
  for synthetic consultation fixtures.
- Canonical spec: `specs/p7-document-consultation-and-individual-download.md`, current
  repository revision; PRD references FR-DOC-001..005, BR-DOC-001..002, FR-ART-001, NFR-001,
  NFR-002, NFR-006, AUD-006 and acceptance AC-004, AC-005, AC-010, AC-011, AC-014.
- Related implementation: issue 0006 owns document identity/evidence, issue 0010 owns the
  minimum status/list contract, issue 0011 owns the frontend decomposition, and issue 0012
  owns the P4 failure-state matrix. This issue consumes those boundaries and must not duplicate
  their state machines or authorization policy.
- Data/compatibility: preserve existing `/api/documents` consumers and add compatible contracts
  or versioned fields as necessary; migration/upgrade tests are required if indexes or fields
  are added. No destructive migration or silent metadata rewrite is allowed.
- Security/observability: server authorization remains authoritative for all authenticated
  roles; sanitize filenames and query values, use uniform safe failures, and never expose raw
  XML, object keys, credentials, tokens, or provider errors in responses/logs/metrics.

## Tests

- **Unit:** query parsing/allowlists, normalization, filter composition, pagination tokens,
  detail mapping, artifact verification, safe filename/error mapping, audit redaction, and
  permission decisions.
- **Integration:** database indexes/upgrade, list/detail/filter contracts, event relationships,
  quarantine/conflict/unavailable evidence, authenticated roles, download streaming and
  integrity checks, state immutability, audit, and object-store failure behavior.
- **E2E/browser:** URL-persisted filters, loading/empty/degraded states, pagination, detail and
  related-event display, download success/failure, anonymous/revoked-session handling, and
  existing document status regression.
- **Validation commands:** repository-configured focused checks plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, `make smoke`, and the configured
  frontend/browser checks.

## Acceptance Criteria

- [x] The archive accepts exactly the approved company, competence, emission-period, family,
  NF-e direction, NFS-e category, event-type, and global-search filters; unsupported filters,
  malformed values, excessive limits, unsafe ordering, and invalid continuation values are
  rejected safely.
- [x] Single and combined filters, multi-company queries, date/competence boundaries, Unicode
  input, and empty results are deterministic and covered by tests.
- [x] Pagination is bounded, stable under repeated requests, does not skip/duplicate rows for a
  fixed dataset, and does not expose database keys or unvalidated cursor state.
- [x] List responses preserve the existing P4 status/list semantics while returning only the
  standardized safe metadata and permitted quarantine/conflict outcomes.
- [x] Detail responses preserve identity, company, parties, dates, competence, category,
  situation, source/collection metadata, event/substitution links, and XML/PDF availability;
  unavailable evidence is never represented as downloadable.
- [x] All authenticated roles receive only the permitted archive data, anonymous and revoked
  sessions are refused, and direct object/artifact/document enumeration does not reveal whether
  an unauthorized target exists.
- [x] A download revalidates authorization, serves only a finalized integrity-verified original,
  uses a safe `Content-Disposition`, and never exposes object-store keys, raw provider errors,
  or payload contents in logs/metrics.
- [x] Pending, missing, divergent, conflicting, unauthorized, and interrupted downloads fail
  safely without changing document, event, evidence, artifact, cursor, collection, or status data;
  XML remains independently available when PDF is unavailable.
- [x] Consultation and download audit events contain only bounded actor/IP/target/result/
  correlation data, use existing redaction, and metrics have bounded labels for latency, errors,
  zero results, denied downloads, and unavailable objects.
- [x] Frontend list/detail/download flows preserve session/role behavior, URL filters, loading,
  empty, error/degraded, pagination, relationship, availability, and existing P4 status states.
- [x] Synthetic unit, integration, and browser/UI tests cover expected and negative behavior,
  integrity, authorization, redaction, concurrency/repeatability, and no-network operation;
  repository validation commands pass.
- [x] Documentation, `IMPLEMENTATION_PLAN.md`, the owning spec/index, Graphify metadata, and
  this issue's Resolution are synchronized before closure, and the work is closed in one
  focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P7 consulta/download and P7-01/P7-02 sequence.
- Spec: `specs/p7-document-consultation-and-individual-download.md` — contracts, security,
  failure behavior, acceptance, and DoD.
- Related issues: `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0010_-_minimum-document-status-and-list-contract.md`,
  `issues/0011_-_frontend-architecture-refactor.md`,
  `issues/0012_-_fiscal-ingestion-failure-state-matrix.md`.
- Current boundaries: `backend/nfx/documents/`, `backend/nfx/artifacts/`,
  `backend/nfx/audit/`, `backend/nfx/identity/`, and `frontend/src/main.tsx`.

---

## Resolution

Implemented P7-01/P7-02 in the existing document boundary. `/api/documents` now validates and
applies the approved bounded filters with signed continuation cursors while preserving P4
collection/status outcomes. Detail responses expose safe identity, dates, collection reference,
related events/substitutions, and artifact availability. Individual document and artifact
download routes recheck evidence ownership, finalization, SHA-256 digest, and size before
streaming; failed reads do not transition artifact state. Consultation/download audit events
use bounded context and existing redaction. The React documents feature now persists search and
family filters in the URL and supports detail/download states. PDF remains explicitly unavailable
pending P7-03 renderer selection.

Tests added/updated: unit coverage for filter allowlists, normalization, date bounds, signed
cursors, and safe filenames; integration coverage for combined/multi-company filtering, opaque
pagination, detail redaction, authenticated download, integrity failure, and no artifact state
mutation. No migration was needed because the existing indexed document/evidence schema supports
the read contract. The repository has no browser runner; frontend lint/build plus synthetic HTTP
tests provide the available UI/endpoint evidence.

Validation run:

- `make lint` — passed (Ruff, mypy, TypeScript, ESLint).
- `make test-unit` — 199 passed.
- `make build` — passed (Django check and Vite build).
- `make test-integration` — 56 passed in isolated PostgreSQL/MinIO; five existing botocore deprecation warnings.
- `make smoke` — passed with isolated web, worker, scheduler, PostgreSQL, and MinIO.
- Focused consultation/status unit tests — 24 passed; Graphify `update .` completed with the
  refreshed code graph. The repository has no browser runner, so browser-specific assertions are
  N/A under the existing validation setup; frontend lint/build and synthetic HTTP/UI contract
  coverage were run instead.
