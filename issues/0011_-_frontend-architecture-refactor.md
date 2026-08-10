---
id: 0011
title: "Refactor frontend into feature-oriented architecture"
type: refactor
status: closed
priority: high
phase: cross-cutting
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0005, 0010]
blocked_by: []
affects:
  - frontend/src/
  - frontend/package.json
  - docs/
---

## Description

Refactor the React frontend into the feature-oriented structure defined by
`ARCHITECTURE.md` section 10.4 without changing product behavior. The current baseline places
all TypeScript types, API calls, state, event handlers, and UI for authentication, users,
companies, certificates, collections, documents, and audit in the 988-line
`frontend/src/main.tsx` entry module. This concentration makes ownership unclear and increases
the regression risk of every subsequent frontend feature.

The expected outcome is a small bootstrap entrypoint, an explicit application composition root,
one shared HTTP boundary, and independently owned feature modules. Existing endpoints, payloads,
permissions, labels, navigation anchors, and visible states remain compatible.

## Implementation Plan

1. Capture the current frontend behavior and dependency boundaries before moving code. Inventory
   the rendered sections, role-based visibility, side effects, API requests, loading/error/empty
   states, and hash-navigation IDs; use this as the regression checklist throughout the refactor.
2. Extract shared HTTP behavior into a typed client that owns same-origin credentials, CSRF token
   lookup/header application, JSON and multipart request handling, and safe response failures.
   Keep endpoint-specific request and response contracts in their owning features; do not add a
   second authentication, authorization, retry, or durable-state policy in the browser.
3. Move TypeScript contracts and label/format helpers to the feature that owns them. Extract the
   authentication/session shell first, then users, companies and certificates, collections,
   documents, and audit as independently renderable feature sections. Preserve their current
   request timing, mutations, refresh behavior, messages, role gates, and DOM section IDs.
4. Introduce `App.tsx` as the composition root for session state, the authenticated shell, and
   feature sections. Pass only the user/session and cross-feature callbacks that are actually
   shared; keep feature-local forms, loading flags, errors, and server data inside their owning
   modules. Avoid circular feature imports and generic shared abstractions that contain domain
   rules.
5. Reduce `main.tsx` to validating the root element and mounting `App`. Keep the existing
   anchor-based navigation and React/Vite stack; do not introduce routing, a global state library,
   a component framework, or a new runtime dependency unless separately approved.
6. Validate every existing role and UI branch with synthetic/local data and the repository's
   configured checks. Document the resulting module boundaries for contributors, refresh Graphify
   with `graphify update .`, synchronize this issue's Resolution, and close the work in one focused
   commit. Do not claim or implement unrelated product backlog.

## In Scope

- Structural decomposition of `frontend/src/main.tsx` into bootstrap, application composition,
  shared HTTP infrastructure, shared presentation primitives, and business feature modules.
- Relocation of existing TypeScript types, helpers, hooks/state, API calls, handlers, and JSX.
- Preservation and verification of authentication, user administration, company/certificate,
  collection, document, and audit behavior.
- Contributor documentation describing module ownership and dependency direction.

## Out of Scope

- New product functionality, redesigned screens, changed copy, styling overhaul, or accessibility
  redesign beyond preserving the current markup behavior.
- Changes to backend endpoints, payloads, permissions, models, migrations, jobs, or fiscal rules.
- React Router, a global state library, a design system, a data-fetching framework, or other new
  runtime dependencies.
- A new frontend test framework or broad test-infrastructure project; existing validation remains
  mandatory, and additional infrastructure requires a separate issue.
- P4-03, P5-P9, document search/download, exports, rendering, retention, or operational features.

## Dependencies and Notes

- Architectural authority: `ARCHITECTURE.md` section 10.4, version 1.1.
- Current baseline: `frontend/src/main.tsx`, `frontend/package.json`, TypeScript/ESLint/Vite config,
  and the frontend contracts already recorded by the P1-P4 specs.
- Related completed work: issue 0005 owns manual collection behavior and issue 0010 owns the
  minimum document status/list contract. This refactor may move their UI code but must not change
  their semantics or reopen their completed scope.
- Data/migration/rollout: no schema or data migration is expected. Deliver the extraction in small,
  buildable steps and retain compatible exports during intermediate moves when needed.
- Security: server-side RBAC remains authoritative. CSRF, same-origin credentials, secret/password
  clearing, safe errors, and the prohibition on exposing raw fiscal payloads or object keys must
  remain intact.

## Tests

- **Static:** TypeScript strict checking and ESLint over the decomposed modules, including React
  hook dependency rules and import-cycle review.
- **Behavioral:** verify login/logout/session restoration; administrator-only user and audit areas;
  company create/edit/lifecycle/enrichment; certificate upload/status; collection request/retry;
  and document loading, empty, degraded, quarantine, conflict, and persisted states.
- **Roles:** verify administrador, operador, visualizador, anonymous, and expired/revoked session
  presentation against the unchanged server-enforced permissions.
- **Validation commands:** run focused checks plus `make lint`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] `frontend/src/main.tsx` only validates the root element and mounts the application composition root.
- [x] Authentication, users, companies, certificates, collections, documents, and audit have explicit feature ownership for their types, API contracts, state, handlers, and presentation.
- [x] Shared HTTP code consistently applies same-origin credentials and CSRF handling and exposes no secrets, raw payloads, object keys, or unsafe server errors.
- [x] `App.tsx` composes the session shell and features without absorbing their local forms, loading/error state, or domain-specific request logic.
- [x] Feature dependencies are one-directional, contain no circular imports, and shared modules contain no feature-specific business rules.
- [x] Existing endpoints, payloads, role visibility, labels, messages, section IDs, anchor navigation, loading/error/empty branches, and refresh behavior remain compatible.
- [x] No router, global state library, component framework, data-fetching framework, or other runtime dependency is added.
- [x] No backend, database, migration, job, fiscal-domain, or unrelated product behavior is changed.
- [x] Administrator, operator, viewer, anonymous, and invalid-session paths retain their current behavior, with authorization still enforced by the server.
- [x] `make lint`, `make build`, `make smoke`, and focused behavioral checks pass without regression.
- [x] Contributor documentation, Graphify metadata, this issue's Resolution, and the focused implementation commit are synchronized on completion.

## References

- Architecture: `ARCHITECTURE.md` section 10.4 — frontend module ownership and constraints.
- Current entrypoint: `frontend/src/main.tsx`.
- Related completed work: `issues/0005_-_manual-collection-control.md` and
  `issues/0010_-_minimum-document-status-and-list-contract.md`.
- Relevant specs: `specs/p1-authentication-sessions-and-rbac.md`,
  `specs/p1-user-administration.md`, `specs/p2-company-lifecycle-and-public-enrichment.md`,
  `specs/p2-certificate-lifecycle-and-envelope-encryption.md`,
  `specs/p3-manual-collection-control.md`, and
  `specs/p4-fiscal-document-ingestion-and-integrity.md`.

---

## Resolution

Implemented the frontend architecture extraction without changing backend or runtime dependencies.
`frontend/src/main.tsx` now only validates `#root` and mounts `App.tsx`; authentication/session
presentation is owned by `features/auth`, and users, companies, certificates, collections,
documents, and audit each own their contracts, API calls, local state, handlers, and UI. The
single `shared/http.ts` boundary applies same-origin credentials and CSRF to mutations, handles
JSON/multipart requests, and converts failures to bounded safe errors. `shared/ui/Feedback.tsx`
contains only presentation behavior.

The refactor preserves the existing endpoint paths/payloads, role gates, Portuguese labels and
messages, section IDs, anchor navigation, loading/error/empty branches, refresh-on-navigation
behavior, certificate password clearing, and server-side authorization. No router, global state
library, component framework, data-fetching framework, backend code, migration, or fiscal behavior
was added. Contributor module-boundary documentation was added to `docs/DEVELOPMENT.md`, and the
implementation plan/spec index now record this cross-cutting increment without marking P1–P4
specs or P5/P6 product work complete.

Validation performed:

- Baseline before implementation: `make lint`, `make build`, and `make smoke` passed.
- Focused after implementation: `npm --prefix frontend run lint`, `npm --prefix frontend run build`,
  and static import/fetch-boundary checks passed.
- Final repository checks: `make lint`, `make test-unit`, `make build`, and `make smoke` passed;
  `make test-integration` was also run successfully against disposable PostgreSQL/MinIO services.
