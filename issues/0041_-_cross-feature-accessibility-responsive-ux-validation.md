---
id: 0041
title: "Complete cross-feature accessibility, responsive, and UX validation"
type: feature
status: closed
priority: high
phase: P10
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0034, 0035, 0036, 0037, 0038, 0039, 0040]
blocked_by: [0035, 0036, 0037, 0038, 0039, 0040]
affects:
  - frontend/src/App.tsx
  - frontend/src/features/
  - frontend/src/shared/ui/
  - frontend/playwright.config.ts
  - frontend/browser-tests/
  - frontend/scripts/
  - docs/
---

## Description

Deliver the pending P10-08 transversal validation slice after the completed P10-02 through
P10-07 feature surfaces. The existing browser projects already execute synthetic fixtures in
Chrome, Firefox, and Edge at 1024, 1280, and 1440 px, and the feature issues verify important
states independently. The remaining gap is a single cross-feature gate: keyboard and focus paths,
labels and landmarks, critical dialogs, contrast usage, table overflow containment, responsive
readability, negative role/session contexts, and reproducible visual evidence are not validated
with one consistent contract across every delivered area.

## Objective and Expected Outcome

Administrators, Operadores, Visualizadores, and safe anonymous/expired-session flows can use the
delivered desktop/notebook experience with visible focus, semantic names and states, keyboard
alternatives, understandable operational feedback, and no clipping or page-level horizontal
overflow. The validation is repeatable across the supported browser/width matrix and records the
skills or plugins evaluated, the flows and roles exercised, observed divergences, and refinements.
Any implementation adjustment is limited to a verified presentation defect and preserves the
existing server-owned data, contracts, anchors, roles, authorization, and feature state behavior.

## In Scope

- Audit the composed `App.tsx` shell and all P10-02..07 surfaces: Dashboard, Documents and
  XML/PDF actions, Companies/Certificates/Collections, ZIP Exports, and Administration/Audit/
  Retention/controlled deletion.
- Add or strengthen repository-native UI-contract and browser assertions for named landmarks and
  headings, visible token-based focus, label/control associations, semantic loading/empty/error/
  unavailable/degraded/blocked/success/critical states, keyboard alternatives, and critical
  dialog cancellation/focus behavior where a dialog is used.
- Exercise the existing synthetic roles and negative sessions, direct anchors/deep links, filters,
  tables, detail panels, downloads or owner-provided action URLs, retry/stale states, repeated
  actions, and the state transitions that each completed P10 issue identifies as critical. Assert
  that opaque cursors, technical errors, secrets, certificate material, fiscal content, and
  internal identifiers remain redacted.
- Validate each required browser and viewport in the existing Playwright project matrix. Detect
  clipping, overlap, unreadable density, action loss, or page-level horizontal overflow; permit
  horizontal scrolling only inside an identified table container with its header/association
  intact.
- Refine shared tokens/primitives or an owning feature presentation only when the matrix exposes
  a concrete defect. Keep the established `App → features → shared` dependency direction and
  use the canonical P10-01 focus, contrast, state, and spacing tokens.
- Record representative browser/width/role/flow results, screenshots or deterministic
  reproduction descriptions, divergences, and applied refinements in the repository’s frontend
  validation documentation and the P10-08 evidence section. Evaluate applicable skills/plugins
  before implementation and record the capabilities used and any required concept/design
  approval in that evidence.

## Out of Scope

- Mobile layouts, touch-specific behavior, widths below the approved desktop/notebook baseline,
  or support for browsers other than current desktop Chrome, Firefox, and Edge.
- New endpoints, payloads, HTTP methods, API error semantics, data-fetching behavior, fiscal or
  retention rules, server-side RBAC, authorization, CSRF/session handling, cursor contracts,
  download ownership/expiration, or audit semantics.
- New routes, router or global state, UI framework/library, production dependency, backend code,
  migrations, infrastructure, telemetry, feature flags, rollout configuration, or unrelated
  cleanup. Do not add a client-side access-control boundary.
- Rewriting feature owners’ functional tests or duplicating domain logic in fixtures. Do not hide,
  truncate, recalculate, or synthesize owner-provided operational data to make a visual check
  pass.
- A new product decision about accessibility standards, responsive breakpoints, supported
  browsers, mobile scope, or visual language; the P10-08 spec and P10-01 tokens remain canonical.

## Dependencies and Notes

- **Plan item:** `IMPLEMENTATION_PLAN.md` — P10-08 “Accessibility, Responsive Polish & UX
  Validation”, under “P10 Frontend UX & Visual System”. This is the next executable item after
  P10-07; P8-02 future source expansions have no spec-ready owner and P9-05 remains externally
  blocked.
- **Canonical spec:** `specs/p10-accessibility-responsive-validation.md`, v1.1. It requires the
  Chrome/Firefox/Edge desktop matrix at 1024/1280/1440 px, accessible keyboard/focus/label/state
  behavior, contained table overflow, synthetic role/session coverage, and recorded evidence.
- **Product and architecture references:** `PRD.md` NFR-009..012 and AC-023/026; `ARCHITECTURE.md`
  §10.4; the frontend workflow and P10-01 token contract in `docs/DEVELOPMENT.md`.
- **Prerequisites:** issues 0035–0040 are closed owners of the shell and each P10 domain slice;
  issue 0034 remains the shared visual-token/primitives baseline. Preserve their HTTP, state,
  anchor, redaction, and server-authorization contracts.
- **Verified gap:** `frontend/playwright.config.ts` runs the required matrix and the individual
  browser specs check selected overflow, focus, keyboard, role, and state cases, but coverage is
  uneven across features and does not produce the P10-08 cross-feature evidence record. The UI
  contract validates shared primitives and feature presentations, while no completed P10 issue
  owns the final consolidated accessibility/responsive pass or its divergence/refinement log.
- **Data/migration/compatibility:** no persisted data or migration is expected. Use only synthetic
  fixtures and preserve `App.tsx`, all existing section IDs and deep links, owner-provided values,
  opaque cursors, same-origin behavior, pt-BR labels, Brasília/R$ presentation, and existing
  desktop browser support.
- **Security/observability/rollout:** validation fixtures must not contain credentials, tokens,
  certificate/key material, XML/PDF/ZIP bytes, customer identifiers, or raw internal errors. The
  UI remains presentation-only; the server remains authoritative for RBAC, ownership,
  authorization, state, expiration, and audit. No new telemetry or rollout setting is needed.

## Implementation Plan

1. Establish the baseline by reading the P10-08 spec, P10-01 token/primitives contract, and the
   closed P10 issue evidence; run `npm --prefix frontend run test:ui-contract`, frontend lint/build,
   and the existing synthetic browser suite so failures are separated from newly introduced
   findings. Inventory every delivered anchor, role/session context, critical state, action,
   table, detail view, and dialog that must remain covered.
2. Extend the existing UI-contract and browser fixtures with shared assertions and focused cases
   for landmark/heading naming, control labels, state semantics, visible keyboard focus, tab order
   for representative flows, safe dialog cancellation/focus return, repeated critical actions,
   stale/error/retry retention, negative role/session access, redaction, and owner-provided data
   integrity. Keep fixtures network-isolated and synthetic.
3. Run the complete matrix in Chrome, Firefox, and Edge at 1024, 1280, and 1440 px. Check page
   `scrollWidth`, bounding boxes, overlap/clipping, action reachability, table-container scrolling,
   header association, focus visibility, contrast against the P10-01 token values, and color-
   independent state cues. Use manual inspection where automation cannot establish perceptual
   contrast or visual clarity, and capture a screenshot or deterministic reproduction note for
   representative flows and every divergence.
4. Correct only confirmed presentation defects in the shared UI or owning feature boundary. Do
   not fix a check by removing functional information, weakening a role/session guard, exposing a
   technical value, changing an endpoint/anchor, adding a second owner, or introducing a new
   layout breakpoint outside the approved desktop/notebook scope. Re-run the affected feature
   contract and matrix cases after each refinement.
5. Run the focused UI contract, frontend lint/build, full browser matrix, and the repository
   validation commands applicable to the changed surface (`make lint`, `make build`, `make
   test-unit`, and `make smoke`). Repeat the browser pass as needed to confirm deterministic
   results and no cross-browser-only regression.
6. Update the P10-08 evidence in `specs/p10-accessibility-responsive-validation.md`, the
   implementation/validation guidance in `docs/DEVELOPMENT.md`, the spec index and
   `IMPLEMENTATION_PLAN.md` status according to repository conventions, and Graphify metadata via
   the established workflow. Complete the issue Resolution with the matrix/evidence summary and
   close it in one focused commit.

## Tests

- **UI contract:** `npm --prefix frontend run test:ui-contract`
- **Frontend static validation:** `npm --prefix frontend run lint` and
  `npm --prefix frontend run build`
- **Browser matrix:** `make test-browser` (or the documented Docker equivalent), with synthetic
  fixtures in Chrome, Firefox, and Edge at 1024, 1280, and 1440 px; retain the manual visual
  inspection/evidence record required by the spec.
- **Repository regression checks:** `make lint`, `make build`, `make test-unit`, and `make smoke`
  when the final diff touches the corresponding shared/frontend surface.

## Acceptance Criteria

- [x] All delivered P10 flows and their critical loading, valid-empty, error, unavailable,
  degraded, blocked, success, and critical-action states pass in current desktop Chrome, Firefox,
  and Edge at 1024, 1280, and 1440 px using synthetic data.
- [x] Administrator, Operador, Visualizador, anonymous, and expired-session contexts preserve the
  existing visible/denied surfaces, anchors/deep links, server-owned role boundary, and safe
  messages; no administrative or fiscal data appears in a negative context.
- [x] Representative navigation, filtering, detail, download/action, retry, and critical-action
  flows are operable by keyboard with a visible token-based focus indicator, a logical tab order,
  and no mouse-only required step.
- [x] Every exercised control has an accessible name and state; headings, landmarks, labels,
  captions, live regions, and error associations remain semantically understandable in the
  rendered UI.
- [x] User and retention critical dialogs, where rendered, support the safe cancel/Escape behavior
  defined by the spec, retain focus appropriately, and return focus to the triggering control
  without falsely completing the action.
- [x] Contrast and state cues meet the P10-01 token contract and do not rely on color alone;
  manual checks are recorded wherever automated assertions cannot establish visual clarity.
- [x] No supported viewport cuts off, overlaps, or hides an essential action, applied filter,
  error, or operational value; any table overflow is contained in an identified scroll region with
  understandable header/column association and no page-level horizontal scroll.
- [x] Owner-provided counts, timestamps, URLs, state labels, safe messages, and opaque cursor
  behavior remain intact; the validation/refinement does not synthesize progress, alter data, or
  expose opaque/internal values.
- [x] Repeated request/retry/critical-action input remains guarded and deterministic, stale or
  out-of-order responses cannot replace a newer visible selection/state, and refresh failures
  retain the last safe context according to the owning feature contracts.
- [x] `npm --prefix frontend run test:ui-contract`, frontend lint/build, the applicable repository
  checks, and the full Docker browser matrix pass without introducing a new production dependency,
  backend change, migration, endpoint change, or authorization regression.
- [x] The evidence records skills/plugins evaluated and applied, any required concept/design
  approval, browser, viewport, role, flow, result, capture or deterministic reproduction,
  divergences, and refinements; no sensitive or customer data is included.
- [x] The P10-08 spec evidence, `docs/DEVELOPMENT.md`, `specs/README.md`,
  `IMPLEMENTATION_PLAN.md`, and required Graphify metadata are synchronized, and the Resolution
  records the validation evidence, plan sync, and closure in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-08.
- Canonical spec: `specs/p10-accessibility-responsive-validation.md` — v1.1.
- Product requirements: `PRD.md` — NFR-009..012, AC-023, and AC-026.
- Architecture: `ARCHITECTURE.md` — §10.4 and frontend dependency boundaries.
- Frontend workflow: `docs/DEVELOPMENT.md` — P10-01..08 validation and Docker browser matrix.
- Related completed issues: 0034 (tokens/primitives), 0035 (shell), 0036 (dashboard), 0037
  (documents), 0038 (companies/certificates/collections), 0039 (exports), and 0040
  (administration/audit/retention).

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- Include: flows, matrix results, divergences/refinements, files modified, tests, documentation,
     Graphify update, implementation-plan sync, and focused commit. -->

Implemented issue 0041 as the transversal P10-08 validation gate.

- Added `frontend/browser-tests/accessibility.spec.ts` for semantic names, labels, live regions,
  redaction, role/session boundaries, page overflow, table containment, clipping, and shell skip
  navigation across the four feature fixture families and the composed shell.
- Added the critical-dialog browser assertion to `frontend/browser-tests/admin.spec.ts`. User and
  retention dialogs now expose names, focus on open, cancel safely with Escape while idle, and
  return focus to their triggering controls; retention cancellation is disabled while busy.
- Extended `frontend/scripts/ui-contract.mjs` for dialog naming/focusability and table overflow.
- No migration, endpoint, backend, production dependency, authorization, anchor, or mobile scope
  change was made.
- `npm --prefix frontend run test:ui-contract`, frontend lint/build, the focused red-green dialog
  check, and `make test-browser` passed. The final Docker matrix passed 342 tests across Chrome,
  Firefox, and Edge at 1024, 1280, and 1440 px.
- Updated `specs/p10-accessibility-responsive-validation.md`, `docs/DEVELOPMENT.md`,
  `specs/README.md`, and `IMPLEMENTATION_PLAN.md`. Graphify was updated after the implementation.
- Skills/plugins evaluated: installed Graphify used for repository relationship navigation; no
  additional frontend/browser skill was installed or applicable, and no design-approval gate was
  required.
