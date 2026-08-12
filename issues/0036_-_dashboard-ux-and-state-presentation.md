---
id: 0036
title: "Modernize dashboard cards and operational-state presentation"
type: feature
status: closed
priority: high
phase: P10
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues:
  - 0011
  - 0018
  - 0025
  - 0026
  - 0027
  - 0028
  - 0029
  - 0030
  - 0034
  - 0035
blocked_by: ["0034", "0035"]
affects:
  - frontend/src/features/dashboard/
  - frontend/src/shared/ui/
  - frontend/scripts/
  - frontend/browser-tests/
  - tests/
  - docs/
---

## Description

Deliver the pending P10-03 dashboard UX slice on top of the completed visual foundation and
authenticated shell. The P8-02 endpoint and its progressive card/drill-down contracts are already
implemented and covered by issues 0018 and 0025–0030, but the current `DashboardSection` renders a
flat list of panels, exposes capability names/status values without a user-facing hierarchy, and
does not make the owner-provided freshness and operational states sufficiently clear. Reload/error
handling can also discard the last dashboard response instead of preserving it as explicitly stale
context.

## Objective and Expected Outcome

Authenticated users can understand the current and preceding dashboard periods, grouped fiscal and
operational cards, source state/freshness, and available drill-downs without learning API field
names. The UI preserves every value, status, freshness signal, URL/filter, role boundary, and safe
message supplied by `GET /api/dashboard` and the existing job observability drill-down. A loading,
partial, degraded, unavailable, stale, or valid-zero result remains distinguishable and never becomes
a fabricated zero or success.

## In Scope

- Presentation of the existing dashboard response: period comparison, grouped cards, values,
  previous-period context, freshness, statuses, capabilities, and Admin-only operational health.
- Clear accessible labels and semantic grouping for fiscal cards, collection/job cards,
  certificate cards, capabilities, backup, dependencies, process health, and backlog where those
  fields are present in the existing response.
- Loading, retry, request-error, stale-last-read, valid-zero, partial, degraded, unavailable, and
  unknown presentation using the P10-01 primitives and the feature-owned response states.
- Existing dashboard period controls and all server-produced drill-down URLs, including the job
  observability navigation that preserves `from`, `to`, and `filter`.
- Focused synthetic UI/browser contract coverage for Administrator, Operador, Visualizador,
  anonymous/expired session composition, keyboard/focus behavior, and side-effect-free rendering.

## Out of Scope

- Changes to `/api/dashboard`, `/api/jobs/observability`, any domain aggregation/query, period
  calculation, filter allowlist, pagination, reconciliation, or server-side authorization.
- New dashboard metrics, monetary calculations, client-side aggregation, cache/snapshot/materialized
  read models, polling, notifications, reports, alerts, or a new dashboard route.
- P8-02 source expansion for fiscal transports, disk capacity, or any other capability still marked
  unavailable/Proposed; P8-02 backend follow-up is not folded into this frontend slice.
- Document, company, certificate, collection, export, administration, retention, or PDF feature
  redesign beyond the existing dashboard link/summary presentation.
- Mobile behavior below the approved desktop/notebook baseline, a client router, global state,
  framework/UI dependency, backend change, migration, or production data/credentials.

## Dependencies and Notes

- **Plan item:** `IMPLEMENTATION_PLAN.md` — P10-03 “Dashboard UX — pending”, under “P10 Frontend
  UX & Visual System”. The plan explicitly makes P10-03 the next UX slice after the shell.
- **Canonical spec:** `specs/p10-dashboard-ux.md`, v1.1. Its contract requires preservation of
  the P8 owner response, grouped cards, explicit source/freshness states, safe period/deep-link
  behavior, and no browser-side domain or authorization logic.
- **Prerequisites:** P10-01 is verified by issue 0034 and P10-02 by issue 0035. The P8-02 response
  and reconciled sources are delivered by issues 0018 and 0025–0030; these are related completed
  contracts, not replacement owners.
- **Verified gap:** `frontend/src/features/dashboard/DashboardSection.tsx` currently maps cards
  directly to an ungrouped panel list, prints raw capability keys/status strings, exposes only a
  limited period/status summary, and has no explicit freshness/stale-last-read presentation. Its
  request error path clears the existing response, and the current feature types do not model the
  operational-health fields needed for a structured presentation. No open/in-progress issue covers
  this P10-03 outcome; issue 0035 explicitly leaves P10-03..08 out of scope.
- **Data/migration/compatibility:** no persisted data or migration is expected. Keep the existing
  response shape, `Cache-Control: no-store` behavior, pt-BR labels, Brasília `[from,to)` period
  semantics, published anchors, query parameters, role visibility, and server-produced URLs.
- **Security/observability:** the client must treat role-filtered health as presentation only;
  non-Administrators must not receive or reveal Admin-only operational/backup details through a
  direct URL or fallback UI. Do not expose payloads, leases, policies, backup identifiers/paths,
  XML/PDF, secrets, or internal exceptions. No new metrics, audit events, feature flags, or rollout
  settings are needed.

## Implementation Plan

1. Inventory the current `DashboardResponse`, `DashboardCard`, `DashboardSignal`, backup/health
   fields, P8 card IDs, and the existing `JobObservabilityPanel` before changing presentation.
   Define a small dashboard-owned view model or grouping map only for labels/order/layout; every
   value, status, freshness timestamp, and drill-down URL must remain sourced from the API response.
2. Compose the dashboard into named semantic groups for the approved fiscal/operational areas.
   Show current and previous periods exactly as returned, retain the `[from,to)` Brasília meaning,
   and keep monetary formatting/labels owner-provided if such a field is introduced later rather
   than calculating or inferring values in React. Keep period input requests limited to the existing
   `from`/`to` contract and let server validation remain authoritative.
3. Render each card's value, status, and freshness as accessible content with distinct treatment
   for ready, real zero, stale, partial, degraded, unavailable, and unknown. During refresh retain
   the last successful response only when it is visibly marked as stale/loading; on a failed refresh
   keep safe prior context available while showing a retryable safe error. Never turn `null`, a
   missing source, or an error into zero/success, and never show a raw status code as the only label.
4. Use the existing `drilldown.href` and `filters` as the only source for card links. Preserve the
   job-panel `history`/`popstate` behavior, deep links, query strings, filter reconciliation, and
   role-based visibility. Render Admin-only operational health and backup only when the authorized
   response contains it; do not infer authorization from a hidden control.
5. Make repeated refreshes and period changes deterministic: an older in-flight response must not
   overwrite a newer selection, and rendering, loading, retry, or navigation must not create
   domain writes, jobs, leases, audit events, fiscal calculations, or duplicate listeners.
6. Extend the repository-native UI contract and, where useful, the existing browser matrix with
   synthetic responses covering each card group, all owner states, previous-period data, source
   failure, stale refresh, invalid period, each role, anonymous/expired sessions, every published
   drill-down, keyboard navigation, and safe redaction. Run the focused checks and repository
   validation before closure.
7. Update the dashboard/development documentation and Graphify metadata, synchronize the P10-03
   evidence in `IMPLEMENTATION_PLAN.md` and `specs/README.md`, fill this issue's Resolution, and
   close only after the plan sync and one focused commit are recorded.

## Tests

- **Focused frontend contract:** `npm --prefix frontend run test:ui-contract`, extended with
  dashboard grouping, period comparison, card-state/freshness semantics, safe error/retry,
  capability redaction, and side-effect assertions using synthetic non-fiscal responses.
- **Frontend quality:** `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- **Browser validation:** the existing `npm --prefix frontend run test:browser`/Docker browser
  target where applicable, using synthetic Administrator, Operador, Visualizador, anonymous, and
  expired-session contexts; cover keyboard/focus, desktop widths, refresh/error retention, URL
  deep links, and no horizontal overflow.
- **Repository regression:** `make lint`, `make test-unit`, configured `make build`, and
  `make smoke`; no real fiscal service, customer data, certificate, XML/PDF, or production
  credential is permitted.

## Acceptance Criteria

- [x] Dashboard cards are presented in the semantic groups required by P10-03, with clear labels,
  current/previous period context, and no raw API field name as the sole user-facing meaning.
- [x] The UI preserves the server-provided `[from,to)` period, current/previous values, card IDs,
  statuses, freshness, and capability states without recalculating metrics, periods, eligibility,
  or authorization in the browser.
- [x] Ready, real-zero, stale, partial, degraded, unavailable, unknown, loading, and request-error
  states remain distinct and accessible; a missing/null/error source is never rendered as zero or
  success.
- [x] A refresh or period request retains the last safe response only with an explicit stale/loading
  indication, and a failed refresh leaves safe prior context visible with a retryable message rather
  than silently discarding unrelated card data.
- [x] Every existing card drill-down uses the server-produced URL/filter contract, preserves period
  and query parameters, keeps job observability navigation functional, and remains reconciled with
  the owning list; no new filter or client-side list is introduced.
- [x] Administrator, Operador, and Visualizador receive the existing role-appropriate dashboard
  presentation; operational health/backup details are rendered only for an authorized Admin
  response and no direct URL or fallback path exposes them to other roles.
- [x] Anonymous and expired sessions continue to expose only the existing authentication flow, and
  safe dashboard errors do not reveal internal exceptions, payloads, leases, policies, backup
  identifiers/paths, XML/PDF, secrets, or customer data.
- [x] Repeated or concurrent refreshes cannot let an older response overwrite a newer period or
  selection, and rendering/navigation causes no persistence, job, lease, audit, fiscal, or duplicate
  listener side effect.
- [x] Focused tests cover positive and negative roles, all card states, stale/error/retry behavior,
  period/deep-link preservation, card-to-list URLs, keyboard/focus semantics, and redaction using
  synthetic data only.
- [x] `npm --prefix frontend run test:ui-contract`, frontend lint/build, the applicable browser
  matrix, `make lint`, `make test-unit`, `make build`, and `make smoke` pass without backend,
  migration, dependency, or contract changes.
- [x] Dashboard/development documentation, the P10-03 spec evidence, `specs/README.md`,
  `IMPLEMENTATION_PLAN.md`, and Graphify metadata are synchronized before closure.
- [x] The Resolution records implementation and validation evidence, the implementation-plan sync,
  and closure in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-03.
- Canonical spec: `specs/p10-dashboard-ux.md` — v1.0.
- P8 owner contract: `specs/p8-dashboard-and-operational-health.md` — P8-02 and its current
  progressive evidence.
- Product requirements: `PRD.md` — FR-DASH-001..003, NFR-008..012, AC-013/023/024/026.
- Architecture: `ARCHITECTURE.md` — §§10.4 and 11, including `App → features → shared` and
  server-side authorization boundaries.
- Related: issues 0018, 0025–0030 (P8 dashboard response/drill-downs), 0034 (P10-01), and 0035
  (P10-02 shell).

---

## Resolution

Implemented P10-03 in the existing `App → features → shared` frontend boundary. Reworked
`DashboardSection` into a grouped, accessible presentation of the server-owned dashboard response:
current/previous `[from,to)` periods, card values and statuses, freshness, server-produced
drill-down URLs, user-facing capability labels, and Admin-only operational health/backup details.
Loading, stale-last-read, valid-zero, unavailable, degraded, partial, unknown, and retryable error
states remain distinct; the last safe response is retained during refresh and failed refreshes.
Request sequencing prevents an older dashboard or job-observability response from replacing a newer
selection. The job drill-down also retains stale safe rows and translates allowlisted error codes.
No endpoint, payload, backend, migration, dependency, role rule, or durable state changed.

Added synthetic UI-contract assertions and a browser fixture/matrix for dashboard grouping, period
comparison, freshness/state semantics, drill-down URL preservation, keyboard focus, overflow, and
Admin-only health redaction. No production or fiscal data is used.

Validation performed:

- Baseline: `npm --prefix frontend run test:ui-contract`, `npm --prefix frontend run lint`, and
  `npm --prefix frontend run build` passed before implementation.
- Focused: `npm --prefix frontend run test:ui-contract`, `npm --prefix frontend run lint`, and
  `npm --prefix frontend run build` passed after implementation.
- Browser: `docker compose -f docker-compose.test.yml build browser-tests` and
  `docker compose -f docker-compose.test.yml run --rm --no-deps browser-tests` passed 90 tests
  across Chrome, Firefox, and Edge at 1024, 1280, and 1440 px.
- Repository: `make lint`, `make test-unit`, `make build`, and `make smoke` passed.

Synchronized `specs/p10-dashboard-ux.md`, `specs/README.md`, `IMPLEMENTATION_PLAN.md`, and
`docs/DEVELOPMENT.md`. Graphify was refreshed with `graphify update .`. No migration or dependency
change was required.
