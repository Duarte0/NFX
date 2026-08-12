---
id: 0040
title: "Modernize administration, audit, and retention UX"
type: feature
status: closed
priority: high
phase: P10
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0011, 0017, 0019, 0024, 0025, 0034, 0035, 0036]
blocked_by: [0034, 0035]
affects:
  - frontend/src/features/users/
  - frontend/src/features/audit/
  - frontend/src/features/retention/
  - frontend/src/shared/ui/
  - frontend/scripts/
  - frontend/browser-tests/
  - tests/
  - docs/
---

## Description

Deliver the P10-07 administration UX slice on top of the completed visual foundation and
authenticated shell. The P1 user and audit contracts, P8 retention preview, P9 controlled-deletion
saga, and P9 backup/health contracts are already implemented and server-authoritative. The current
administrative UI is still a set of minimal forms and tables: users expose only list/create from the
client, audit has no filter or cursor controls and prints technical fields, and retention/deletion
renders raw reason/state/error values without a complete accessible state model or consistent action
guards.

## Objective and Expected Outcome

Administrators can manage users, inspect the append-only audit stream, understand retention decisions,
and follow a controlled-deletion operation through clear pt-BR presentation of the existing durable
states. Critical actions show the safe target and scope, required reason, confirmation/cancel choice,
and authoritative result without declaring false success. Operators, Visualizadores, anonymous users,
and expired sessions retain the existing server denial behavior and never receive administrative data.
The existing Admin-only dashboard health/backup boundary remains intact; its dashboard presentation
continues to be owned by issue 0036 rather than being duplicated here.

## In Scope

- Recompose `UsersSection` with P10-01 primitives and the existing user routes for listing with
  bounded cursor/filter context, creating, editing, role changes, password reset, activation/
  deactivation, and the authenticated user's own password-change flow where the current session
  contract permits it. Show localized role/active states, safe validation, optimistic-version
  conflicts, last-Administrator protection, and redacted success/error feedback.
- Recompose `AuditSection` as an accessible, bounded read view using the existing actor/action/
  entity/result filters, cursor, `next_cursor`, and integrity result. Map known action, entity, and
  result values to pt-BR labels, retain safe context when refresh fails with explicit stale/error/
  retry feedback, and do not present secrets, fiscal content, paths, hashes, raw internal errors, or
  unnecessary sensitive identifiers.
- Recompose `RetentionSection` so retained, eligible, and non-executable decisions are distinct and
  understandable; the preview remains metadata-only and shows only safe bounded evidence context.
  Preserve the current scope hash/version handshake and expose the exact reason and confirmation
  requirements only when the owner says the decision is eligible.
- Present controlled-deletion `pending`, `executing`, `recovery_required`, `failed`, and `completed`
  states with safe step/error wording, refresh and authorized resume actions, and no completion claim
  before the authoritative operation response. Keep stale previews visibly invalid and require a new
  preview before retrying a changed scope.
- Add focused synthetic UI-contract and applicable browser coverage for all three roles, direct
  administrative deep links, anonymous/expired sessions, loading/empty/error/stale/retry states,
  action confirmation and cancellation, optimistic conflicts, last-Administrator refusal, audit
  filtering/pagination/integrity, retention eligibility, deletion recovery, focus, keyboard, and
  redaction.

## Out of Scope

- Changes to identity, audit, retention, deletion, backup, health, job, migration, storage, or
  authorization behavior; changes to existing HTTP methods, payloads, CSRF/session semantics,
  cursor/filter allowlists, version checks, retention rules, deletion checkpoints, or recovery
  policy.
- Automatic deletion, retention recalculation in the browser, automatic restore/resume policy,
  backup creation or expiration, a new backup endpoint, or a second backup/health surface. Issue
  0036 owns the visual redesign of `DashboardSection` operational health and backup presentation;
  this issue only preserves its Admin-only boundary and existing server-provided safe data.
- New user powers, user invitation/recovery, 2FA, physical deletion, audit writes, audit schema
  changes, new telemetry, notifications, polling, snapshots, caches, client-side authorization,
  or client-side fiscal/retention/deletion business rules.
- Display of passwords, hashes, tokens, certificate/key material, XML/PDF/ZIP bytes, object keys,
  manifests, backup paths, provider exceptions, customer data, or unbounded technical identifiers.
- Mobile behavior below the approved desktop/notebook baseline, a client router, global state,
  framework/UI dependency, backend code, migration, infrastructure, feature flag, or rollout
  configuration. P10-08 owns the later transversal accessibility/responsive validation slice.

## Dependencies and Notes

- **Plan item:** `IMPLEMENTATION_PLAN.md` — P10-07 “Administration UX — concluído no issue 0040”, under “P10
  Frontend UX & Visual System”. P10-03 through P10-06 are already represented by open issues
  0036–0039; P10-08 remains the later transversal validation slice.
- **Canonical spec:** `specs/p10-administration-ux.md`, v1.1. It requires presentation-only
  modernization, Admin-only server enforcement, explicit critical-action states, safe audit/backup
  wording, retention/deletion distinctions, and focus/keyboard/type-check validation.
- **Functional owners:** `specs/p1-user-administration.md` (P1-04),
  `specs/p1-audit-foundation.md` (P1-05), `specs/p8-retention-eligibility.md` (P8-03),
  `specs/p9-controlled-deletion.md` (P9-03), and `specs/p9-backup-and-restore.md` (P9-02).
  Their completed issues 0017, 0019, and 0024 remain authoritative for the response and state
  contracts; this issue must not create a parallel owner.
- **Prerequisites:** P10-01 shared tokens/primitives are verified by issue 0034 and P10-02 shell
  composition by issue 0035. Issue 0036 is related because it owns dashboard operational-health and
  backup presentation, but it is not a dependency for the users/audit/retention slice here.
- **Verified gap:** `frontend/src/features/users/UsersSection.tsx` currently calls only list/create,
  has no cursor/filter or administrative action controls, and uses raw role/active text. The audit
  client requests only the default list and renders raw action/entity/result/reason values without
  filter, cursor, integrity, stale, or retry presentation. `RetentionSection.tsx` exposes raw
  document/scope and rule metadata, maps only the three decision values, and prints raw deletion
  operation states, steps, and safe-error codes without a complete state/action model or consistent
  in-flight guards. The existing UI contract and shell browser tests verify primitives/navigation,
  not these administrative contracts or negative action cases.
- **Data/migration/compatibility:** no persisted data or migration is expected. Preserve all existing
  routes, response fields, cursor/filter semantics, `#usuarios`, `#auditoria`, and `#retencao`
  anchors, pt-BR wording, same-origin credentials, CSRF behavior, no-store reads, UTC audit display,
  and civil-date retention semantics. Do not store passwords, scopes, or operation state outside the
  existing feature state.
- **Security/observability/rollout:** the UI is not an access-control boundary. Render administrative
  sections only from the existing authorized composition, but rely on server responses for RBAC,
  versioning, eligibility, confirmation, audit, and deletion authority. Map safe error categories
  locally without exposing raw response internals. Do not add logs, metrics, audit events, flags, or
  rollout settings.

## Implementation Plan

1. Inventory the existing user, audit, retention, and deletion response types and routes, P10-01
   primitives, shell role composition, and current synthetic harness. Define feature-owned maps for
   roles, actions, results, retention decisions, deletion states/steps, and safe errors; unknown or
   missing values must remain visibly unknown/unavailable rather than becoming success, empty, or
   complete.
2. Extend the user client and section to consume only the existing `/api/users` contracts. Keep
   `version` with every edit/action, send bounded reasons where the owner requires them, guard
   duplicate submissions, refresh authoritative rows after success/conflict, and preserve server
   handling of duplicate email, stale version, invalid role, last active Administrator, CSRF, and
   session expiry. Password inputs must be write-only and must never be rendered in feedback or
   fixtures.
3. Add audit filter and bounded-cursor controls for the existing `actor_id`, `action`,
   `entity_type`, and `result` query parameters. Render the server-provided `integrity` result and
   safe event metadata with accessible labels; retain the last safe page only when it is marked stale
   and retryable, and ensure an older response cannot replace a newer filter or cursor selection.
4. Recompose retention and deletion panels around explicit accessible state descriptions. Preserve
   the preview scope hash/version and exact confirmation contract, enable the request only for an
   eligible current preview with a bounded reason, and require the owner response before showing
   pending/executing/recovery/failed/completed outcomes. Refresh or resume only through the existing
   endpoints; never simulate progress, auto-resume, or remove a document locally.
5. Apply keyboard/focus semantics and shared feedback to loading, valid empty, unavailable,
   validation error, stale-last-read, retry, blocked, critical-action, success, and recovery states.
   Preserve the existing administrative anchors and role composition, and leave dashboard health/
   backup redesign to issue 0036 while asserting its Admin-only response boundary.
6. Extend `frontend/scripts/ui-contract.mjs`, the browser fixture, and the existing browser matrix
   with synthetic data for positive and negative roles, direct hashes, expired sessions, every
   administrative state, concurrent/out-of-order reads, duplicate actions, optimistic conflicts,
   last-Administrator refusal, stale previews, recovery, integrity failure, keyboard/focus, and
   redaction. Keep all fixtures free of credentials, fiscal content, object paths, and provider
   errors.
7. Run focused and repository validation with synthetic data only. Update the relevant development/
   operations documentation and the evidence sections of the canonical P10-07 spec, then synchronize
   `specs/README.md`, `IMPLEMENTATION_PLAN.md`, and Graphify metadata through the repository workflow.
   Close this issue only after its Resolution records the evidence, the plan sync is complete, and
   the implementation is delivered in one focused commit.

## Tests

- **Focused frontend contract:** `npm --prefix frontend run test:ui-contract`, extended with role
  visibility/direct-link denial, user action/version/reason mapping, audit filters/cursor/integrity,
  retention/deletion states, stale/error/retry retention, duplicate-action guards, concurrency
  ordering, focus/keyboard, and redaction assertions using synthetic responses.
- **Browser validation:** `npm --prefix frontend run test:browser` or the existing Docker browser
  target for Chrome, Firefox, and Edge desktop at the approved widths; cover Administrator,
  Operador, Visualizador, anonymous/expired sessions, direct `#usuarios`, `#auditoria`, and
  `#retencao` access, critical-action cancellation, recovery/reload, and keyboard behavior without
  real service or network data.
- **Frontend quality:** `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- **Repository regression:** `make lint`, `make test-unit`, `make build`, and `make smoke`; no
  backend, migration, dependency, production credential, customer, certificate, XML/PDF/ZIP, or
  backup-path data may be used.

## Acceptance Criteria

- [x] Administrator-only users, audit, and retention sections remain hidden from Operador and
  Visualizador navigation, and direct hashes/requests preserve the existing uniform server denial
  without revealing administrative data to non-Administrators, anonymous users, or expired sessions.
- [x] User creation, edit, role change, password reset, activation/deactivation, and permitted
  own-password change use the existing endpoints and display localized success, validation, stale
  version, duplicate-email, and last-Administrator outcomes without exposing a password or hash.
- [x] User critical actions require the existing bounded reason/confirmation rules, have explicit
  confirm/cancel and in-flight behavior, and refresh the authoritative user/version state after a
  successful or rejected mutation; no local state transition is treated as durable success.
- [x] Audit filters for actor, action, entity, and result preserve the existing allowlist, bounded
  cursor, `next_cursor`, and Admin-only contract; integrity failure is visibly distinct from a valid
  stream and safe event metadata is presented without secrets, fiscal content, paths, manifests,
  raw exceptions, or unnecessary sensitive identifiers.
- [x] Retained, eligible, and non-executable retention decisions have distinct accessible pt-BR
  labels and explanations; valid empty, unavailable, stale, and retry states are not rendered as
  zero, eligible, or successful data.
- [x] A deletion request is available only for an eligible current preview with the exact existing
  scope/version, confirmation, and bounded reason; a changed/stale scope blocks the action and
  requires a new authoritative preview.
- [x] Pending, executing, recovery-required, failed, and completed deletion states are distinct;
  refresh and resume are offered only for the returned operation state, recovery/failure never
  becomes completion, and no automatic restore, resume, or local document removal occurs.
- [x] Refreshes, filters, pagination, previews, mutations, status checks, and resume actions have
  explicit loading/stale/error/retry feedback, guard duplicate interactions, and prevent an older
  concurrent response from overwriting a newer selection or authoritative state.
- [x] Existing routes, anchors, response payloads, CSRF/session behavior, server-side RBAC,
  optimistic versioning, audit requirements, retention rules, deletion saga/checkpoints, and
  Admin-only dashboard health/backup boundary remain unchanged; no client-side authorization or
  fiscal/retention/deletion rule is introduced.
- [x] UI and synthetic fixtures contain no passwords, hashes, tokens, certificate/key material,
  XML/PDF/ZIP bytes, object keys, backup paths, manifests, customer data, raw provider exceptions,
  or unbounded technical identifiers.
- [x] Focused UI and browser tests cover expected and negative roles, all listed states, valid empty,
  source/session failure, retry/stale retention, version/concurrency conflicts, duplicate actions,
  confirmation/motive rules, pagination/filtering, recovery/reload, focus/keyboard, and redaction.
- [x] `npm --prefix frontend run test:ui-contract`, the applicable browser matrix, frontend
  lint/build, `make lint`, `make test-unit`, `make build`, and `make smoke` pass without backend,
  migration, dependency, HTTP-contract, or unrelated feature changes.
- [x] Administrative/development documentation, P10-07 evidence in `specs/p10-administration-ux.md`,
  `specs/README.md`, `IMPLEMENTATION_PLAN.md`, and required Graphify metadata are synchronized before
  closure.
- [x] The Resolution records implementation and validation evidence, the `IMPLEMENTATION_PLAN.md`
  sync, and closure in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-07.
- Canonical spec: `specs/p10-administration-ux.md` — v1.1.
- Functional owners: `specs/p1-user-administration.md`, `specs/p1-audit-foundation.md`,
  `specs/p8-retention-eligibility.md`, `specs/p9-controlled-deletion.md`, and
  `specs/p9-backup-and-restore.md`.
- Product and architecture: `PRD.md` — FR-AUTH-001..007, RET-001..008, AUD-001..010,
  OPS-BKP-005, NFR-008..012, and AC-003/004/014/015/016/026; `ARCHITECTURE.md` — server-side
  authorization, audit, retention, deletion, backup, and `App → features → shared` boundaries.
- UI baseline: issues 0011, 0034, and 0035; issue 0036 owns the neighboring dashboard operational
  health/backup presentation and must not be duplicated here.
- Current components: `frontend/src/features/users/UsersSection.tsx`,
  `frontend/src/features/audit/AuditSection.tsx`, `frontend/src/features/retention/RetentionSection.tsx`,
  `frontend/src/shared/ui/`, `frontend/scripts/ui-contract.mjs`, and the browser shell fixture/matrix.

---

## Resolution

Implemented the P10-07 presentation slice in the existing `App → features → shared` boundaries:

- `UsersSection` now supports bounded list filters/cursors, create/edit, role changes, password
  reset, activation/deactivation, own-password change, localized owner errors, version-aware
  critical dialogs, duplicate-action guards, and authoritative refreshes.
- `AuditSection` now supports allowlisted filters/cursors, UTC presentation, integrity status,
  safe context/reason redaction, stale reads, retry, and ordered responses.
- `RetentionSection` now distinguishes retention decisions and all controlled-deletion durable
  states, blocks stale previews, preserves the exact scope/version/confirmation handshake, and
  exposes refresh/recovery only through owner endpoints.
- Added synthetic UI-contract assertions and `admin.*` browser fixtures covering RBAC, deep links,
  negative sessions, loading/empty/error/stale/retry, confirmation/cancellation, focus/keyboard,
  integrity, recovery, and redaction. No backend, migration, dependency, or HTTP contract changed.

Validation completed with synthetic data:

- `npm --prefix frontend run test:ui-contract` — passed.
- `npm --prefix frontend run lint` and `npm --prefix frontend run build` — passed.
- Browser fixture TypeScript check — passed.
- `make lint` — passed; `make test-unit` — 307 passed; `make build` — passed; `make smoke` — passed.
- `make test-browser` using the rebuilt Docker image — 306 passed across Chrome, Firefox, and Edge
  at 1024, 1280, and 1440 px. Direct host Playwright was unavailable because the host lacks the
  branded Chrome binary and Firefox graphical libraries.

Documentation and graph synchronization completed in `specs/p10-administration-ux.md`,
`specs/README.md`, `IMPLEMENTATION_PLAN.md`, `docs/DEVELOPMENT.md`, and `graphify update .`.

<!-- Filled by the agent on close. DO NOT edit manually. -->
