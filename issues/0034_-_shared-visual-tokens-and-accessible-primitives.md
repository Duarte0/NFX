---
id: 0034
title: "Establish shared visual tokens and accessible UI primitives"
type: feature
status: closed
priority: high
phase: P10
created_at: 2026-08-11
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0011]
blocked_by: []
affects:
  - frontend/src/shared/ui/
  - frontend/src/features/
  - frontend/src/App.tsx
  - frontend/
  - tests/
  - docs/
---

## Description

Start the independent P10 frontend UX sequence by adding one shared visual language and a small
set of accessible presentation primitives. The current React application has semantic feature
markup and a minimal `Feedback` component, but no shared source of truth for typography, spacing,
color, surfaces, borders, elevation, or common operational states. This leaves the already
delivered screens visually inconsistent and makes later shell and feature modernization prone to
duplicated values and incompatible states.

## Objective and Expected Outcome

The frontend exposes a documented, reusable token set and primitives for actions, fields, panels,
tables, badges, and feedback. The default visual direction is institutional wine as primary,
gray as structural/neutral, and white as the main surface, with semantic auxiliary tones only
where their purpose and contrast are documented. Loading, valid-empty, error, unavailable,
degraded, blocked, success, and critical-action states remain distinguishable, preserve the
functional information supplied by the owning feature, and provide visible focus and appropriate
HTML/ARIA semantics.

Later P10 slices can consume these primitives without inventing local visual constants. Existing
routes, anchors, feature ownership, HTTP calls, server-side authorization, fiscal behavior,
pt-BR labels, Brasília time, and BRL presentation remain unchanged.

## In Scope

- The shared token contract for typography, spacing, colors, surfaces, borders, radii/shadows,
  focus, and semantic state colors, including exact values selected within the approved wine,
  gray, and white direction and their documented purposes.
- Repository-native shared primitives for action, form control, panel, table, badge, feedback,
  and the common operational states required by the canonical spec.
- Adopting the primitives in the existing shared feedback path and a bounded representative set
  of current feature surfaces so the contract is exercised without redesigning a whole feature.
- Semantic HTML, ARIA labeling/live-region behavior, visible keyboard focus, disabled/blocked
  behavior, and safe user-facing messages for the primitives.
- Focused tests and deterministic rendering/validation for every common state using synthetic
  non-fiscal data, plus documentation of token purpose and contrast pairs.

## Out of Scope

- Application-shell redesign, sidebar/header/navigation work, responsive polish across every
  feature, or any P10-02..08 feature-specific modernization.
- Changes to routes, section IDs/anchors, URL parameters, HTTP payloads, API clients, domain
  state, fiscal calculations, authorization, role visibility, or server-side enforcement.
- New router, global state library, UI framework, data-fetching framework, or other material
  frontend dependency; do not duplicate business rules in shared components.
- Backend code, database tables, migrations, object storage, external services, production
  credentials, or real fiscal/XML/PDF content in fixtures, tests, logs, or screenshots.
- Introducing a browser-test platform as a separate infrastructure project; use the repository's
  supported validation approach or keep any narrowly scoped test support local to this slice.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — **P10-01 Design System Foundation**, the first pending
  P10 slice and the prerequisite for P10-02..07. P0 follow-ups are independently covered by
  issues 0032 and 0033; P9-05 remains externally blocked and does not block this frontend slice.
- Canonical spec: `specs/p10-design-system-foundation.md`, v1.1. Its contract and four acceptance
  statements govern tokens, primitives, states, semantics, contrast, and compatibility.
- Product sources: `PRD.md` NFR-009..012 and AC-026 require the wine/gray/white identity,
  consistent operational states, desktop/notebook readability, and preservation of functional
  and server-side authorization behavior.
- Architecture: `ARCHITECTURE.md` §§10.4 and 11 require `App → features → shared`, local state
  by default, centralized shared HTTP behavior, and no client-side authorization substitute.
- Related issue 0011 established the frontend feature/shared boundaries; it does not provide the
  visual token or primitive contract. Issues 0032–0033 are unrelated P0 operational follow-ups.
- Verified gap: the former `frontend/src/shared/ui/Feedback.ts` only rendered a role-bearing
  paragraph, and
  the current frontend has no shared token stylesheet or equivalent primitive set. Feature
  components currently declare buttons, inputs, tables, and loading/degraded messages locally.
- Data/migration: none. Tokens and primitives are presentation code only and must not introduce
  persisted state, network requests, audit events, or changes to fiscal data.
- Security/compatibility: visual hiding is never authorization; blocked and unavailable states
  must retain safe functional information. Do not render internal exceptions, secrets, XML/PDF,
  certificate material, object keys, or raw API payloads. Preserve existing role-based rendering
  and the shared HTTP redaction behavior.
- Observability/rollout: no new metrics, logs, feature flags, or external rollout configuration.
  The change is safe to adopt incrementally because primitives remain presentation-only; record
  any intentionally unsupported state as an explicit follow-up rather than silently mapping it
  to success or zero.

## Implementation Plan

1. Inventory the existing shared feedback path and representative feature markup, then define the
   finite token names, semantic purposes, and exact values in the canonical spec's implementation
   evidence. Keep the palette within the approved wine/gray/white direction, document auxiliary
   meanings, and verify every foreground/background pair used by text, controls, focus, and
   states before wiring consumers.
2. Add the repository-native shared token source and primitives under the existing shared
   presentation boundary. Ensure variants are explicit rather than feature-specific booleans,
   primitives render semantic HTML with stable labels/roles, expose visible focus, and keep
   disabled/blocked controls non-actionable without relying on color or display:none alone.
3. Model the common state contract so loading, valid-empty, error, unavailable, degraded,
   blocked, success, and critical action are distinguishable and safe. A valid empty result may
   say empty; unavailable/degraded must not become zero or success; raw internal messages must be
   reduced to the existing safe user-facing error contract.
4. Migrate the existing shared `Feedback` usage and a small representative set of current
   dashboard/domain controls to the primitives without changing their HTTP timing, local state,
   role checks, section IDs, anchors, labels, or data. Leave full feature restyling for the
   dependent P10 issues.
5. Add focused tests for token usage, contrast, semantic/ARIA output, visible focus, keyboard
   interaction, disabled/blocked behavior, safe messages, and rendering of every common state
   with synthetic data. Run the frontend and repository validation commands, update the relevant
   visual-system/runtime documentation and Graphify metadata, synchronize the P10-01 evidence in
   `IMPLEMENTATION_PLAN.md` and `specs/README.md`, fill this issue's Resolution, and close in one
   focused commit.

## Tests

- **Frontend contract:** `npm --prefix frontend run lint` and
  `npm --prefix frontend run build`, plus focused shared-UI/component or DOM checks supported by
  the repository.
- **Accessibility/visual:** verify all documented foreground/background pairs, visible focus,
  keyboard operation, labels, roles/live regions, and each loading, empty, error, unavailable,
  degraded, blocked, success, and critical-action rendering with synthetic non-fiscal data.
- **Compatibility:** assert existing section IDs/anchors, role-based visibility, safe feedback
  messages, and unchanged shared HTTP behavior for representative feature consumers.
- **Repository regression:** run the focused tests together with `make lint`, `make test-unit`,
  configured `make build`, and `make smoke`; no database, migration, integration endpoint, or
  real fiscal service is required by this issue.

## Acceptance Criteria

- [x] Shared tokens are the only source of shared typography, spacing, color, surface, border,
  elevation, focus, and semantic state values used by the primitives; each token documents its
  purpose and approved wine/gray/white or auxiliary meaning.
- [x] The documented foreground/background pairs for text, controls, focus, and operational
  states pass the applicable contrast verification, and the result is reproducible from the
  repository's validation commands.
- [x] Shared primitives cover action, form control, panel, table, badge, and feedback concerns
  with explicit variants and no duplicated domain rules or feature-owned HTTP behavior.
- [x] Loading, valid-empty, error, unavailable, degraded, blocked, success, and critical-action
  states render distinct, understandable semantics; unavailable/degraded never appear as zero or
  success, and safe messages never expose internal exceptions, secrets, XML/PDF, certificates,
  object keys, or raw payloads.
- [x] Primitive output uses appropriate semantic HTML/ARIA, visible focus, labels/live-region
  behavior, and keyboard operation; blocked or disabled actions cannot be triggered through the
  presentation layer and do not depend on color alone.
- [x] Existing `App → features → shared` ownership, role-based visibility, shared HTTP behavior,
  pt-BR presentation, Brasília/BRL labels, routes, IDs, anchors, and feature data remain
  unchanged; direct URL access and server-side authorization are not weakened.
- [x] Repeated rendering and state transitions are deterministic and side-effect free: no API
  request, persistence, audit event, fiscal computation, or mutation occurs solely because a
  primitive renders or re-renders.
- [x] Focused tests exercise positive and negative variants, all common states, contrast,
  keyboard/focus/ARIA behavior, safe-message handling, and representative existing consumers
  using synthetic non-fiscal data only.
- [x] `npm --prefix frontend run lint`, `npm --prefix frontend run build`, `make lint`,
  `make test-unit`, configured `make build`, and `make smoke` pass with no new dependency or
  migration requirement.
- [x] Visual-system documentation, the P10-01 spec evidence, `specs/README.md`,
  `IMPLEMENTATION_PLAN.md`, and Graphify metadata are synchronized before closure.
- [x] The issue is closed only after its Resolution records the evidence, the implementation-plan
  sync is recorded, and all changes are committed in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-01.
- Canonical spec: `specs/p10-design-system-foundation.md` — v1.0.
- Product requirements: `PRD.md` — NFR-009..012 and AC-026.
- Architecture: `ARCHITECTURE.md` — §§10.4 and 11.
- Related issue: `issues/0011_-_frontend-architecture-refactor.md`.
- Dependent specs: `specs/p10-application-shell.md` and `specs/p10-dashboard-ux.md` (and the
  remaining P10 feature specs) consume this foundation after it is verified.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->

## Resolution

Implemented P10-01 under the existing `App → features → shared` boundary. Added the documented
token source in `frontend/src/shared/ui/tokens.css` and repository-native `Button`, `Field`,
`Panel`, `DataTable`, `Badge`, and stateful `Feedback` primitives. The dashboard, job drill-down,
authenticated shell, login, and all existing Feedback consumers adopt the shared presentation path;
HTTP clients, local feature state, routes, anchors, roles, Portuguese/Brasília/BRL presentation,
and server-side authorization remain unchanged. Blocked actions use native `disabled`; unsafe
technical error content is reduced to a safe user-facing message.

Validation performed:

- Baseline: `npm --prefix frontend run lint` and `npm --prefix frontend run build` passed before implementation.
- Focused: `npm --prefix frontend run lint`, `npm --prefix frontend run test:ui-contract`, and
  `npm --prefix frontend run build` passed; the contract test covers eight states, ten contrast
  pairs, semantic/ARIA output, visible focus, native keyboard behavior, safe messages and blocking.
- Repository: `make lint`, `make test-unit`, `make build`, and `make smoke` passed after implementation.

Documentation synchronized in `specs/p10-design-system-foundation.md`, `specs/README.md`,
`IMPLEMENTATION_PLAN.md`, and `docs/DEVELOPMENT.md`. No migration, dependency, backend change,
external service, fiscal fixture, or production credential was added. Graphify was refreshed with
`graphify update .` after the code changes.
