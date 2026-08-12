---
id: 0035
title: "Deliver the desktop application shell and role-aware navigation"
type: feature
status: open
priority: high
phase: P10
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: ~
related_issues: [0011, 0034]
blocked_by: []
affects:
  - frontend/src/App.tsx
  - frontend/src/features/auth/
  - frontend/src/features/companies/
  - frontend/src/shared/ui/
  - frontend/scripts/
  - tests/
  - docs/
---

## Description

Implement the approved P10-02 application shell on top of the completed P10-01 visual foundation.
The current authenticated composition in `App.tsx` uses a single flex header and navigation row,
does not expose a skip-to-content path or active navigation state, and publishes `#certificados`
without a matching DOM destination. The existing role conditions, hash navigation, feature anchors,
and server-side authorization are the baseline to preserve; issue 0034 explicitly leaves shell,
sidebar, header, and navigation work out of scope.

## Objective and Expected Outcome

Authenticated users receive a consistent desktop/notebook shell with an institutional header,
role/session identity, logout, Brasília/BRL context, sidebar navigation, an active-item indication,
named landmarks, and a keyboard-focusable skip link. Every currently published area remains
addressable by its existing hash and query/drill-down URL. The certificate navigation link resolves
to one authorized destination inside the existing companies/certificates surface without creating a
parallel route or feature.

Anonymous and expired sessions continue to render only the existing authentication flow. The shell
is presentation/composition work: it introduces no client router, global state store, endpoint,
permission rule, persistence, fiscal computation, or new UI dependency.

## In Scope

- The authenticated desktop/notebook composition: header, sidebar/navigation, main landmark,
  skip-to-content link, identity/role display, logout action, and Brasília/BRL context.
- A typed role-aware navigation model that preserves the existing visibility matrix: all
  authenticated roles see Dashboard, Documentos, Exportações, and Coletas; Administrador/Operador
  see Empresas and Certificados; Administrador sees Usuários, Auditoria, and Retenção.
- Perceptible active navigation for the current hash, including accessible naming/current-item
  semantics and keyboard operation.
- Stable destinations for `#dashboard`, `#documentos`, `#exportacoes`, `#empresas`,
  `#certificados`, `#coletas`, `#usuarios`, `#auditoria`, and `#retencao`, with exactly one
  `id="certificados"` destination in the existing authorized companies/certificates area.
- Desktop/notebook layout behavior at widths of 1024 px, 1280 px, and 1440 px, using the P10-01
  tokens/primitives and avoiding horizontal scrolling, overlap, or hidden navigation labels.
- Preservation of existing feature-owned hash/query handling, drill-down URLs, safe notification
  messages, load callbacks, and server-enforced authorization.

## Out of Scope

- Dashboard, document, company, certificate, collection, export, administration, or retention
  feature restyling beyond the shell integration required for layout and navigation.
- P10-03 through P10-08, mobile behavior below the approved desktop/notebook baseline, or a new
  browser-routing model.
- New HTTP endpoints, query parameters, API payloads, authorization policies, session behavior,
  database tables, migrations, audit events, telemetry, feature flags, or rollout configuration.
- A client router, global state library, component framework, icon dependency, or other relevant
  frontend dependency.

## Dependencies and Notes

- **Plan item:** `IMPLEMENTATION_PLAN.md`, P10-02 “Application Shell — pending”.
- **Canonical spec:** `specs/p10-application-shell.md`, P10-02 v1.0.
- **Prerequisite:** P10-01 is implemented and verified by `issues/0034_-_shared-visual-tokens-and-accessible-primitives.md`.
- **Related baseline:** `issues/0011_-_frontend-architecture-refactor.md` and
  `specs/p1-authentication-sessions-and-rbac.md` define the `App → features → shared` ownership,
  role matrix, session shell, hash anchors, and server-side authorization boundary.
- No migration, infrastructure, data compatibility, or external service dependency is expected.
  The existing safe-message behavior and same-origin HTTP client remain authoritative.
- P9-05 was evaluated first in the plan sequence but remains blocked by unresolved external
  NF-e/ADN endpoints, envelopes, limits, certificates/homologation, and physically separate
  backup/recovery evidence; it is not part of this issue.

## Implementation Plan

1. Inventory the existing `AuthenticatedApp`, `AuthShell`, feature section IDs, certificate
   inventory/detail composition, and P10-01 tokens/primitives before changing composition. Keep the
   navigation targets and role predicates in one shell-owned model, while leaving feature state,
   fetching, query parsing, and authorization in their existing owners.
2. Compose the authenticated view with semantic header, named navigation/sidebar, and main
   landmarks. Add a focusable skip link targeting the main content, retain the existing identity,
   role, logout, Brasília, BRL, and safe notification information, and ensure an anonymous or
   expired session never receives the authenticated shell.
3. Replace the current link-row presentation with the role-filtered navigation model. Each item
   must retain its published hash and existing load callback behavior; active state must follow the
   current hash on initial render and hash changes without rewriting query strings or introducing
   a second data-loading path. Preserve all existing drill-down/query URLs and feature-owned
   `hashchange`/`popstate` behavior.
4. Provide one stable `#certificados` destination within the already authorized companies/
   certificates surface. Do not create a certificate route or bypass the existing `canManage`
   visibility boundary; direct URL access remains subject to the server-side policy.
5. Use only the completed shared token/primitives contract for shell presentation. At and above
   1024 px, verify that the sidebar, header, main content, controls, and navigation labels remain
   usable without overlap or horizontal scrolling; if any compact presentation is used, retain an
   accessible item name.
6. Extend the repository-native UI contract or an equivalent focused shell test with synthetic
   authenticated contexts for Administrador, Operador, and Visualizador. Cover landmarks, skip-link
   target/focus, active state, all anchor destinations, the unique certificate target, role matrix,
   unchanged query/hash behavior, and absence of rendering side effects. Run the focused frontend
   checks and repository validation before closure.
7. On completion, record the verified shell evidence in the canonical P10-02 spec and synchronize
   its status in `specs/README.md` and `IMPLEMENTATION_PLAN.md`; update relevant development/UI
   documentation and Graphify metadata through the repository workflow. Close this issue only after
   the plan sync and one focused commit are recorded in the Resolution.

## Data, Migration, Compatibility, Security, and Observability Notes

- No data model, migration, stored state, backup content, or external integration changes are
  permitted.
- Hashes, query strings, deep links, section IDs, feature HTTP contracts, pt-BR labels, and
  Brasília/BRL presentation remain compatible. Navigation may improve discoverability but must not
  authorize a hidden action or alter server-side enforcement.
- UI hiding is not access control. Role-filtered navigation is only a presentation affordance;
  direct requests and actions continue through the existing server policy.
- The shell must not expose credentials, session tokens, cookies, certificate material, fiscal XML/
  PDF, object keys, raw payloads, or internal exception details. Existing logout/session failure
  semantics remain intact.
- No new metrics, logs, audit events, feature flags, or rollout settings are needed.

## Tests

- **Focused frontend contract:** `npm --prefix frontend run test:ui-contract`, extended to verify
  shell markup/landmarks, role-filtered navigation, anchors, active state, skip-link focus target,
  unique `#certificados`, and side-effect-free rendering with synthetic users.
- **Frontend quality:** `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- **Repository regression:** `make lint`, `make test-unit`, `make build`, and `make smoke`.
- **Manual browser matrix:** Chrome, Firefox, and Edge desktop at 1024 px, 1280 px, and 1440 px;
  exercise keyboard-only tab order, skip-link focus, active hash navigation, deep links with
  published query parameters, logout, and all three roles. Confirm no horizontal scroll, overlap,
  hidden navigation label, or unauthorized certificate/admin destination.
- Use synthetic/non-production identities and data only; no browser test may call a real fiscal
  service or include credentials, certificates, XML, or customer data.

## Acceptance Criteria

- [x] The authenticated UI has semantic header, named navigation/sidebar, main content landmark,
  and a keyboard-focusable skip link that moves focus to the main content.
- [x] Header content is limited to the approved session identity/role, logout, and Brasília/BRL
  context while existing safe notifications remain available without exposing internal details.
- [x] All published anchors remain addressable and semantically equivalent:
  `#dashboard`, `#documentos`, `#exportacoes`, `#empresas`, `#certificados`, `#coletas`,
  `#usuarios`, `#auditoria`, and `#retencao`; there is exactly one `#certificados` DOM destination.
- [x] The navigation visibility matrix is preserved for Administrador, Operador, and Visualizador,
  and direct access/actions remain protected by the existing server-side authorization.
- [x] The current hash has a perceptible, accessible active navigation item on initial load and
  after hash changes; navigation preserves existing query strings, drill-down URLs, and feature
  load behavior.
- [x] The certificate destination is within the existing authorized companies/certificates surface
  and does not add a route, duplicate feature, or unauthorized access path.
- [ ] At 1024 px, 1280 px, and 1440 px in Chrome, Firefox, and Edge desktop, shell controls and
  labels do not overlap, disappear, or require horizontal scrolling; keyboard focus remains
  visible and usable.
- [x] Anonymous and expired sessions continue to expose only the existing authentication flow, and
  logout clears the authenticated shell using the existing session behavior.
- [x] Rendering and navigation do not create HTTP requests, persistence, audit events, fiscal
  calculations, or duplicate feature listeners beyond the existing load callbacks/owners.
- [x] No router, global state library, relevant UI dependency, endpoint, payload, permission rule,
  migration, or backend behavior is introduced.
- [x] Focused tests cover positive and negative role visibility, all anchors, active/deep-link
  behavior, skip-link/focus semantics, certificate uniqueness, query preservation, and safe
  session/notification behavior using synthetic data.
- [x] `npm --prefix frontend run test:ui-contract`, frontend lint/build, `make lint`,
  `make test-unit`, `make build`, and `make smoke` pass without new dependency or migration
  requirements.
- [x] The P10-02 spec evidence, `specs/README.md`, `IMPLEMENTATION_PLAN.md`, relevant UI/development
  documentation, and Graphify metadata are synchronized before closure.
- [ ] The Resolution records implementation and validation evidence, the implementation-plan sync,
  and closure in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-02.
- Canonical spec: `specs/p10-application-shell.md` — v1.0.
- Prerequisite spec: `specs/p10-design-system-foundation.md` — v1.1, implemented in issue 0034.
- Product requirements: `PRD.md` — NFR-010..012, AC-023, and AC-026.
- Architecture: `ARCHITECTURE.md` — §10.4 and §11.
- Authentication/RBAC baseline: `specs/p1-authentication-sessions-and-rbac.md`.
- Related issue: `issues/0011_-_frontend-architecture-refactor.md`.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->

## Build status

The implementation and repository validation are complete except for the mandatory manual
desktop-browser matrix. This checkout has no Chrome, Firefox, or Edge binary and no configured
browser/e2e runner, so keyboard-only focus movement, runtime `hashchange` updates, deep links at
1024/1280/1440 px, and cross-browser overflow behavior remain unverified. Keep this issue open;
run the documented synthetic UI contract plus the manual Chrome/Firefox/Edge matrix in an
equipped validation environment, then complete the remaining browser criterion and Resolution.
