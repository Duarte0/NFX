---
id: 0037
title: "Modernize document search, detail, and XML/PDF actions"
type: feature
status: closed
priority: high
phase: P10
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0011, 0015, 0023, 0034, 0035, 0036]
blocked_by: [0034, 0035]
affects:
  - frontend/src/features/documents/
  - frontend/src/shared/ui/
  - frontend/scripts/
  - frontend/browser-tests/
  - tests/
  - docs/
---

## Description

Deliver the pending P10-04 Documents UX slice on top of the completed visual foundation and
authenticated shell. The P7 consultation, individual download, and PDF-render contracts are
already implemented by issues 0015 and 0023, but the current `DocumentsSection` is still a
plain form/table/detail composition that exposes technical reason values, does not present
server pagination or all deep-link behavior clearly, drops the last response on refresh failure,
and does not consistently bind XML/PDF actions to the owner-provided availability state.

## Objective and Expected Outcome

Authenticated users can search and inspect documents with visible active filters, bounded
pagination context, accessible fiscal/operational states, and an explicit association between a
selected document and its XML/PDF actions. The UI preserves the P7/P8 response, URL, cursor,
download, PDF lifecycle, RBAC, audit, and integrity contracts. Quarantine, conflict, no
coverage, source failure, pending PDF, failed PDF, unsupported PDF, and valid empty results stay
distinct and never become a fabricated zero, success, or raw technical error.

## In Scope

- Presentation of the existing `GET /api/documents` filters, search, result count, bounded
  pagination/cursor, ordering context, active-filter summary, and `[from,to)` period semantics.
- URL/deep-link hydration and navigation for the allowlisted document filters without silently
  normalizing invalid parameters or introducing client-side filter rules.
- Accessible document list rows, status/outcome labels, valid-empty/source/degradation states,
  and safe user-facing messages for server reason codes and PDF errors.
- Selected-document detail presentation, event/substitution relationships, XML/original
  availability, and server-authorized PDF request, status, regeneration, and download actions.
- Stale-last-read, loading, retry, request-error, reload, and repeated/concurrent interaction
  behavior using the P10-01 primitives and existing feature ownership.
- Synthetic UI contract and applicable browser coverage for all authenticated roles, anonymous or
  expired sessions, keyboard/focus behavior, deep links, pagination, action states, and redaction.

## Out of Scope

- Changes to document models, ingestion, artifact storage, retention, identity/integrity,
  `/api/documents` or PDF endpoint payloads, filter allowlists, cursor signing, ordering,
  server-side authorization, audit behavior, or PDF generation.
- New fiscal filters, value filters, CSV/Excel export, reports, ZIP behavior, client-side search,
  client-side aggregation, or recalculation of totals, periods, eligibility, or domain state.
- Changes to document data, XML/PDF bytes, download headers, renderer version, retention policy,
  migrations, backend services, infrastructure, dependencies, telemetry, feature flags, or
  production rollout configuration.
- Mobile behavior below the approved desktop/notebook baseline, a router, global state store, or
  a second document route/feature.
- Dashboard redesign beyond preserving the existing dashboard-to-document drill-down URL and
  filter contract; P10-03 is owned by issue 0036.

## Dependencies and Notes

- **Plan item:** `IMPLEMENTATION_PLAN.md` — P10-04 “Documents UX — pending”, under “P10
  Frontend UX & Visual System”.
- **Canonical spec:** `specs/p10-documents-ux.md`, v1.0. It requires preservation of allowlisted
  filters, URL boundaries, pagination/deep links, safe distinct states, and XML/PDF owner
  contracts.
- **Prerequisites:** P10-01 is verified by issue 0034 and P10-02 by issue 0035. The P7-01/P7-02
  consultation/download contract is verified by issue 0015; P7-03 PDF rendering is verified by
  issue 0023. Issue 0036 is the neighboring P10-03 dashboard slice and explicitly excludes
  document redesign.
- **Verified gap:** `frontend/src/features/documents/DocumentsSection.tsx` renders raw
  `reason_code`/`pdf_error` values, shows only a limited total summary, does not expose the
  received `next_cursor` as bounded navigation, hydrates drill-down filters only for a narrow
  hash-change case, clears the last response after a failed refresh, has no explicit XML action
  in the detail view, and constructs a PDF download path from the document ID instead of treating
  the returned PDF availability/download contract as the sole source of an action. It also lacks
  focused document UI/browser coverage; existing tests cover the backend contracts, not this
  presentation slice.
- No persisted data or migration is expected. Keep the existing same-origin HTTP/CSRF client,
  `no-store` reads, pt-BR labels, server-produced download URLs, query strings, deep links, and
  role-independent authenticated read/download policy.

## Data, Migration, Compatibility, Security, and Observability Notes

- Treat response values as authoritative. Preserve every allowlisted query parameter, the
  server-provided `[from,to)` boundary, `total`, `limit`, `truncated`, `next_cursor`, statuses,
  outcomes, availability, and PDF state without deriving a replacement value in React.
- A cursor control must carry the opaque server cursor back through the existing URL/query
  contract and retain the active filters; it must not decode, edit, or synthesize cursors. Invalid
  parameters remain visible as a safe server error rather than being silently corrected.
- Use only server-authorized download URLs and the existing PDF request/status contract. Do not
  expose XML/PDF contents, object keys, digests beyond the existing safe prefixes, credentials,
  internal exceptions, or raw reason/error codes as the only user-facing explanation.
- Refresh and PDF-request guards are interaction idempotency only. They must not create duplicate
  requests/listeners, alter durable state in the browser, or hide a failed PDF behind a successful
  XML/PDF state. After reload, the durable server response remains authoritative.
- No new metrics, audit events, logging, cache, retry worker, or rollout setting is required.

## Implementation Plan

1. Inventory the current `DocumentResponse`, `DocumentItem`, `DocumentDetail`, `PdfMetadata`,
   `listDocuments`, `getDocument`, `requestPdf`, existing P7 filter/query semantics, and the
   P10-01 primitives. Define presentation-only labels and a small view model if needed; keep
   status, reason, availability, URLs, cursor, and PDF lifecycle owned by the response.
2. Recompose `#documentos` with the shared field, panel, table, badge, and feedback primitives.
   Keep the existing filter names and values, show active filters and the server-returned period
   and count/truncation context, and add next-page navigation only through the received opaque
   cursor while preserving every active query parameter and the published dashboard deep links.
3. Make location hydration and navigation deterministic for initial deep links, hash/popstate
   changes, filter submission, refresh, and pagination. Let the server reject invalid filters;
   do not create a second client validation or normalization policy. Prevent an older in-flight
   list/detail/PDF response from overwriting a newer selection or period.
4. Render distinct accessible states for loading, valid empty, available, persisted, quarantine,
   conflict, no coverage, unknown, partial, retry, blocked, unavailable, stale-last-read, and
   request error. During refresh retain prior safe rows only with an explicit stale/loading
   indication; on failure retain safe context with a retryable message and never map null/error
   data to zero or success.
5. Make the selected-document detail explicit and action-scoped: expose only the returned XML/
   original download contract when available, show event relationships and safe metadata, and
   request/regenerate/download PDF only for the returned state/URL. Disable duplicate PDF submits
   while a request is active, refresh the durable detail/list state afterward, and preserve XML
   availability when PDF generation fails or is unsupported.
6. Extend `frontend/scripts/ui-contract.mjs` and the existing browser fixture/matrix with
   synthetic responses for every list/detail/PDF state, each role and negative session context,
   valid/invalid filters, deep links, cursor preservation, stale/error/retry retention, action
   idempotency, keyboard/focus semantics, server URL use, and safe redaction. Run focused and
   repository validation using synthetic data only.
7. Update the document/development documentation and Graphify metadata through the repository
   workflow, synchronize P10-04 evidence in `specs/p10-documents-ux.md`, `specs/README.md`, and
   `IMPLEMENTATION_PLAN.md`, fill this issue's Resolution, and close only after the plan sync and
   one focused commit are recorded.

## Tests

- **Focused frontend contract:** `npm --prefix frontend run test:ui-contract`, extended with
  document filters/deep links, cursor preservation, semantic state labels, stale/error/retry
  behavior, selected-detail actions, PDF idempotency, and redaction assertions using synthetic
  payloads.
- **Browser validation:** `npm --prefix frontend run test:browser` or the existing Docker browser
  target, covering Chrome, Firefox, and Edge desktop at the approved widths where applicable;
  exercise all three authenticated roles, anonymous/expired sessions, keyboard/focus, deep links,
  paginated results, reload, failed refresh, XML download, and each PDF state.
- **Frontend quality:** `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- **Repository regression:** `make lint`, `make test-unit`, `make build`, and `make smoke`; no
  real fiscal service, customer data, certificate, XML/PDF, or production credential is allowed.

## Acceptance Criteria

- [x] The document form preserves the P7 allowlisted filters, active values, temporal boundaries,
  deep-link query parameters, and server ordering/pagination contract without adding a filter or
  silently normalizing invalid input.
- [x] The result view uses the server-provided total, limit, truncation, and opaque next cursor;
  pagination retains active filters and does not invent totals, cursors, or client-side results.
- [x] Valid-empty, available, unavailable, no-coverage, unknown, partial, retry, blocked,
  persisted, quarantine, and conflict states remain distinct, labeled, keyboard-accessible, and
  never render missing/error data as zero or success.
- [x] Refresh, reload, and request failures retain prior safe rows only with explicit
  stale/loading/error context and a retry path; an older in-flight response cannot overwrite a
  newer filter, cursor, detail selection, or PDF state.
- [x] The selected-document detail keeps the document/action association, presents safe metadata
  and event relationships, and exposes XML/original download only when the authorized response
  says it is available.
- [x] PDF request, regeneration, pending, available, failed, unsupported, unavailable, and
  download states remain distinct; duplicate submits are prevented at the interaction boundary,
  reload observes durable server state, PDF failure never hides available XML, and downloads use
  only the existing server-provided/approved contract.
- [x] Administrator, Operador, and Visualizador retain the existing document read/download
  behavior; anonymous and expired sessions remain on the existing authentication flow, and no
  client presentation path bypasses server-side authorization.
- [x] No XML/PDF bytes, object keys, credentials, internal exceptions, raw technical reason/error
  values, or unapproved fiscal metadata are exposed in the UI or test fixtures.
- [x] Focused UI/browser tests cover positive and negative roles, every listed document/PDF state,
  valid and invalid filters, cursor/deep-link preservation, stale/error/retry behavior, detail
  actions, keyboard/focus semantics, request idempotency, and safe redaction with synthetic data.
- [x] `npm --prefix frontend run test:ui-contract`, the applicable browser matrix, frontend
  lint/build, `make lint`, `make test-unit`, `make build`, and `make smoke` pass without backend,
  migration, dependency, or contract changes.
- [x] Document/development documentation, P10-04 spec evidence, `specs/README.md`,
  `IMPLEMENTATION_PLAN.md`, and Graphify metadata are synchronized before closure.
- [x] The Resolution records implementation and validation evidence, the implementation-plan
  sync, and closure in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-04.
- Canonical spec: `specs/p10-documents-ux.md` — v1.1.
- P7 consultation/download contract: `specs/p7-document-consultation-and-individual-download.md`;
  implementation issue 0015.
- P7 PDF/rendering contract: `specs/p7-danfe-danfse-rendering.md`; implementation issue 0023.
- Product requirements: `PRD.md` — FR-DOC-001..006, NFR-004/006/008..012, AC-010/011/023/026.
- Architecture: `ARCHITECTURE.md` — `App → features → shared` and server-side authorization
  boundaries.
- Related UI baseline: issues 0034 and 0035; neighboring dashboard slice issue 0036.

---

## Resolution

Implemented P10-04 in `DocumentsSection` and the existing document API adapter. The slice now
preserves allowlisted filters, active query/deep-link parameters, server temporal boundaries,
totals, limits, truncation and opaque cursors; it renders safe, distinct consultation/document/
PDF states; retains stale last-read rows with retry context; and guards list/detail/PDF responses
against stale selections and duplicate interaction submits.

The selected-document detail explicitly binds XML/original and PDF actions to the selected
document and uses only owner-provided URLs. PDF pending, available, failed, unsupported and
unavailable states remain separate, durable state is re-read after a request, and XML remains
available when PDF rendering fails. No endpoint, backend contract, migration, dependency, router,
global state, fiscal data or production configuration changed.

Tests and validation completed:

- `npm --prefix frontend run test:ui-contract` — passed with document filters, cursor, state,
  stale/error/retry, action and redaction coverage.
- `npm --prefix frontend run lint` and `npm --prefix frontend run build` — passed.
- `make lint` — passed (Ruff, mypy and frontend lint).
- `make test-unit` — passed (`307 passed`, one pre-existing botocore deprecation warning).
- `make build` — passed.
- `make smoke` — passed against ephemeral PostgreSQL/MinIO services.
- `make test-browser` — passed (`135 passed`) in Chrome, Firefox and Edge at 1024, 1280 and
  1440 px; this includes Administrator, Operador, Visualizador, anonymous/expired sessions,
  keyboard/focus, deep-link, cursor and redaction fixtures.

Documentation synchronized in `specs/p10-documents-ux.md`, `specs/README.md`,
`IMPLEMENTATION_PLAN.md` and `docs/DEVELOPMENT.md`. The Graphify skill was read and used for
codebase navigation; the repository Graphify update workflow was run after implementation. No
frontend-specific design or browser skill/plugin was installed in this workspace, so no separate
concept-approval gate applied; browser evidence is recorded above.

Closed after all acceptance criteria were checked and the focused issue commit was prepared.
