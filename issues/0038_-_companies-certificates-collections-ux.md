---
id: 0038
title: "Modernize companies, certificates, and collections UX"
type: feature
status: closed
priority: high
phase: P10
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0005, 0013, 0014, 0020, 0022, 0028, 0029, 0034, 0035]
blocked_by: [0034, 0035]
affects:
  - frontend/src/features/companies/
  - frontend/src/features/certificates/
  - frontend/src/features/collections/
  - frontend/src/shared/ui/
  - frontend/scripts/
  - frontend/browser-tests/
  - tests/
  - docs/
---

## Description

Deliver the pending P10-05 companies, certificates, and collections UX slice on top of the
completed visual foundation and authenticated shell. The underlying company lifecycle, A1
certificate, ADN coverage, and collection-control contracts are implemented, but the current
screens still expose several technical state values directly, discard safe prior results on
refresh failures, and do not consistently preserve URL-addressable filters or guard repeated
mutations at the interaction boundary.

## Objective and Expected Outcome

Administrators and Operators can manage companies, certificates, and collections with clear,
accessible, role-appropriate presentation of active/inactive, certificate, coverage, collection,
execution, freshness, error, and blocked states. The UI preserves every owner-provided value,
filter, deep link, confirmation/reason, authorization boundary, durable result, and safe message
from the existing APIs. A missing certificate, absent ADN coverage, transient failure, policy
block, valid empty result, and successful operation remain distinct and are never presented as a
fabricated success or zero.

## In Scope

- Presentation of company lifecycle, public-enrichment status, flow state, certificate status and
  freshness, ADN coverage, collection state/progress, execution outcome, retry, and safe-error
  values using the shared P10-01 primitives.
- The existing company lifecycle filter, certificate inventory filters and opaque pagination
  cursor, collection execution filters, `#empresas`, `#certificados`, and `#coletas` deep links,
  including popstate/hash navigation and server-produced filter contracts.
- Accessible company list/detail editing, activation/deactivation confirmation and reason,
  enrichment, flow pause/habilitation, certificate upload/substitution, collection request, and
  retry presentation while keeping the current feature-owned API calls and server semantics.
- Loading, valid-empty, unavailable, degraded, invalid, stale-last-read, retryable-error,
  blocked, partial, running, failed, cooldown, and success presentation for each domain where the
  owner response provides the corresponding state.
- Interaction idempotency for refreshes and mutations, deterministic handling of concurrent reads,
  and synthetic UI/browser contract coverage for all existing roles and negative session contexts.

## Out of Scope

- Changes to company, certificate, collection, job, adapter, coverage, cursor, encryption,
  audit, metrics, or authorization behavior on the backend; changes to any existing HTTP payload,
  endpoint, filter allowlist, pagination contract, or durable state transition.
- New fiscal transports, coverage rules, cursor formats, client-side domain calculations,
  snapshots/cache/materialized reads, polling, notifications, reports, or a second route/feature.
- Changing confirmation/reason requirements, idempotency, retry eligibility, version handling,
  encryption, certificate validation, collection policy, cursor semantics, or server-side RBAC.
- Displaying certificate material, passwords, keys, adapter payloads, raw enrichment payloads,
  internal exceptions, object keys, production/customer data, or CNPJ-bearing real fixtures.
- Dashboard redesign beyond preserving the existing company/certificate drill-down URLs owned by
  issues 0028 and 0029; P10-03 and P10-04 remain owned by issues 0036 and 0037.
- Mobile behavior below the approved desktop/notebook baseline, a client router, global state,
  new UI/framework dependencies, migrations, infrastructure, telemetry, feature flags, or rollout
  configuration.

## Dependencies and Notes

- **Plan item:** `IMPLEMENTATION_PLAN.md` — P10-05 “Companies, Certificates & Collections UX —
  concluded in issue 0038”, under “P10 Frontend UX & Visual System”. P10-03 and P10-04 are already represented by
  open issues 0036 and 0037; P10-05 is the next uncovered slice in plan order.
- **Canonical spec:** `specs/p10-companies-certificates-collections-ux.md`, v1.1. It requires
  distinct state language, preserved owner contracts, interaction-only duplicate protection,
  URL-addressable filters, RBAC preservation, and safe redaction.
- **Prerequisites:** P10-01 is verified by issue 0034 and P10-02 by issue 0035. The functional
  owners are the completed P2 company/certificate contracts, issue 0005 collection control, issue
  0014 ADN coverage, and the simulator-backed P5/P6 flows in issues 0013, 0020, and 0022. Issues
  0028 and 0029 provide the completed dashboard drill-down contracts this UI must preserve.
- **Verified gap:** `CompaniesSection.tsx` presents raw flow states in table/detail text, uses a
  non-keyboard row click for selection, clears the company result on a failed reload, and only
  reacts to a narrow hash-change filter case. `CertificateInventoryPanel.tsx` collapses stale and
  unknown freshness into the same label, exposes raw status/filter values, drops the last result on
  errors, and does not carry the returned `next_cursor` through a bounded URL pagination control.
  `CollectionsSection.tsx` falls back to raw collection/execution states, has no stale-last-read
  presentation or URL event synchronization for execution filters, and leaves repeated request,
  retry, and refresh calls unguarded. Existing UI contract coverage checks shell/navigation
  structure but does not verify this P10-05 presentation and interaction matrix.
- **Data/migration/compatibility:** no persisted data or migration is expected. Keep same-origin
  HTTP/CSRF behavior, `no-store` reads, pt-BR labels, Brasília period semantics, server-provided
  totals/statuses/freshness/URLs, existing anchors and query parameters, and current role-based
  visibility. Treat the opaque certificate cursor as uninspectable and pass it back unchanged.
- **Security/observability/rollout:** render only safe metadata and owner-provided safe messages;
  never infer authorization from a hidden control or expose Admin/Operator-only surfaces to a
  Visualizador or direct URL. Do not add audit events, metrics, logs, flags, retries, or rollout
  settings; server authorization and auditing remain authoritative.

## Implementation Plan

1. Inventory the current company, certificate, and collection response types, APIs, location
   filters, mutation contracts, P10-01 primitives, role composition in `App.tsx`, and the
   dashboard-produced URLs. Define presentation-only label/state maps and accessible grouping;
   values, timestamps, cursors, safe errors, and authorization remain response-owned.
2. Recompose the three sections into semantic panels/tables with keyboard-accessible selection and
   action controls. Keep active/inactive company labels, public-enrichment non-authority, certificate
   state/freshness, ADN absence versus error, flow state/progress, execution outcome, and policy
   block visibly distinct. Use shared primitives for labels, feedback, focus, disabled/loading, and
   critical actions without adding a UI dependency.
3. Make initial deep links, hash/popstate changes, filter submission, reload, and certificate
   inventory pagination deterministic. Preserve every allowlisted query value, the returned total,
   limit, truncation flag, and opaque `next_cursor`; do not decode, synthesize, normalize, or
   locally reconcile server filters or domain totals.
4. Retain the last safe company, inventory, or collection response during refresh only with an
   explicit stale/loading indicator. On invalid, unavailable, degraded, or network failure show a
   safe retryable message and preserve unrelated prior context; never convert missing data, absent
   coverage, or an error into zero, success, or an available certificate.
5. Keep mutations bound to existing server contracts: confirmation and reason for deactivation,
   version and durable response for company edits, current authorization for certificate changes,
   and existing eligibility/idempotency for collection request/retry. Disable duplicate submits
   only at the interaction boundary, refresh authoritative state after completion, and ensure an
   older concurrent read cannot overwrite a newer filter, selected company, or operation result.
6. Extend `frontend/scripts/ui-contract.mjs` and the existing browser fixture/matrix with synthetic
   companies, certificate inventory, coverage, and collection responses covering every specified
   state, all three authenticated roles, anonymous/expired sessions, direct/deep links, opaque
   cursor preservation, stale/error/retry retention, confirmation/repeat/reload behavior,
   keyboard/focus semantics, and redaction. Run focused and repository validation with synthetic
   data only.
7. Update the company/certificate/collection development documentation and Graphify metadata
   through the repository workflow, synchronize P10-05 evidence in the spec, `specs/README.md`,
   and `IMPLEMENTATION_PLAN.md`, fill this issue's Resolution, and close only after the plan sync
   and one focused commit are recorded.

## Tests

- **Focused frontend contract:** `npm --prefix frontend run test:ui-contract`, extended with
  company lifecycle/enrichment presentation, certificate status/freshness/cursor behavior,
  collection coverage/execution states, filter/deep-link synchronization, stale/error/retry
  retention, mutation guards, and safe redaction using synthetic payloads.
- **Browser validation:** `npm --prefix frontend run test:browser` or the existing Docker browser
  target for Chrome, Firefox, and Edge desktop at the approved widths; cover Administrator,
  Operador, Visualizador, anonymous/expired sessions, keyboard/focus, direct anchors, filters,
  pagination, reload, failed refresh, confirmation/reason, repeated actions, and safe messages.
- **Frontend quality:** `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- **Repository regression:** `make lint`, `make test-unit`, `make build`, and `make smoke`; no
  real fiscal service, customer data, certificate, XML/PDF, or production credential is allowed.

## Acceptance Criteria

- [x] Company active/inactive/registered states, public-enrichment non-authority, and NF-e/NFS-e
  flow states are distinct, accessible, and never shown as unexplained raw API values.
- [x] Certificate current/expired/expiring, absent, fresh/stale/unknown, invalid, unavailable,
  degraded, and valid-empty states are distinct; certificate material, passwords, keys, and raw
  payloads are never rendered.
- [x] ADN coverage absence, unknown state, transient error, and collection policy block are clearly
  differentiated from collection success, empty, running, partial, failed, cooldown, and retry
  states; no missing/error state becomes a fabricated zero or success.
- [x] Company, certificate inventory, and collection execution filters preserve their existing
  allowlisted URL/query contracts, anchors, server totals/limits/truncation, and opaque cursor;
  pagination and deep links do not invent, decode, silently normalize, or locally recalculate data.
- [x] Company, certificate, and collection actions preserve existing role checks, confirmation and
  reason rules, version/idempotency semantics, audit behavior, and durable server responses; a
  repeated click is guarded at the interaction boundary without claiming success before the server
  confirms it.
- [x] Refresh, reload, filter, pagination, and mutation failures retain prior safe context only
  with explicit stale/loading/error state and a retry path; concurrent responses cannot overwrite a
  newer filter, selected company, or operation result, and no duplicate listener/request is added.
- [x] Administrator, Operador, and Visualizador see only their existing role-appropriate surfaces;
  anonymous and expired sessions remain on the existing authentication flow, including on direct
  URLs, and no hidden-control or fallback path bypasses server-side authorization.
- [x] UI and synthetic fixtures contain no passwords, certificate/key material, raw enrichment or
  adapter payloads, object keys, internal exceptions, production/customer data, or real CNPJ data.
- [x] Focused UI/browser tests cover positive and negative roles, every listed company/certificate/
  collection state, filter/deep-link/cursor preservation, stale/error/retry behavior, action
  confirmation and idempotency, keyboard/focus semantics, concurrency ordering, and redaction.
- [x] `npm --prefix frontend run test:ui-contract`, the applicable browser matrix, frontend
  lint/build, `make lint`, `make test-unit`, `make build`, and `make smoke` pass without backend,
  migration, dependency, or HTTP-contract changes.
- [x] Company/certificate/collection development documentation, P10-05 spec evidence,
  `specs/README.md`, `IMPLEMENTATION_PLAN.md`, and Graphify metadata are synchronized before
  closure.
- [x] The Resolution records implementation and validation evidence, the implementation-plan sync,
  and closure in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-05.
- Canonical spec: `specs/p10-companies-certificates-collections-ux.md` — v1.1.
- Functional owners: `specs/p2-company-lifecycle-and-public-enrichment.md`,
  `specs/p2-certificate-lifecycle-and-envelope-encryption.md`,
  `specs/p3-manual-collection-control.md`, `specs/p5-nfe-distribution-and-manifestation.md`,
  and `specs/p6-nfse-adn-distribution-and-coverage.md`.
- Related implementation contracts: issues 0005, 0013, 0014, 0020, 0022, 0028, 0029, 0034, and
  0035; neighboring P10-03/P10-04 issues 0036 and 0037 are separate owners.
- Architecture: `ARCHITECTURE.md` — `App → features → shared`, server-side authorization, and
  safe fiscal-data boundaries.

---

## Resolution

Implemented the P10-05 UX slice in the existing `App → features → shared` architecture. The
companies presentation now uses accessible semantic labels for lifecycle, public enrichment and
NF-e/NFS-e flows; preserves allowlisted URL filters, totals, truncation and opaque pagination; and
retains safe stale/error context with sequence and interaction guards. Certificate inventory and
detail distinguish current/absent/expiry/freshness states without rendering certificate material.
Collections distinguish ADN coverage from collection/execution outcomes and preserve independent
filters, owner-provided progress and retry/blocked semantics. Existing API calls, role checks,
confirmation/reason/version behavior, durable responses and the single `#certificados` anchor were
kept unchanged. No backend, endpoint, payload, dependency or migration changed.

Added synthetic UI-contract assertions and the `companies` browser fixture for all roles, negative
sessions, state/redaction coverage, opaque cursor handling, stale/retry behavior, focus/keyboard and
overflow. The browser image was rebuilt to include the fixture.

Validation completed:

- `npm --prefix frontend run test:ui-contract` — passed.
- `npm --prefix frontend run lint` and `npm --prefix frontend run build` — passed.
- `make test-browser` — 180/180 passed in Chrome, Firefox and Edge at 1024/1280/1440 px.
- `make lint`, `make test-unit`, `make build` and `make smoke` — passed.

Documentation and Graphify metadata were synchronized in the same focused commit. No production
credentials, customer data, real CNPJ, fiscal transport or destructive migration was used.
