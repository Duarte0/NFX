---
id: 0029
title: "Reconcile dashboard certificate cards with filtered certificate inventory"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0018, 0025, 0028]
blocked_by: []
affects:
  - backend/nfx/operations/
  - backend/nfx/certificates/
  - backend/nfx/urls.py
  - frontend/src/features/dashboard/
  - frontend/src/features/companies/
  - frontend/src/features/certificates/
  - tests/
  - docs/
---

## Description

Close the certificate-card drill-down gap in the progressive P8-02 dashboard slice. The
dashboard currently counts current, expired, and soon-to-expire certificates from the
certificate owner, but all three cards link to the unfiltered company section and no bounded
certificate inventory response exposes a reconciliable total. A user can therefore not verify
which companies account for a certificate card or distinguish a real zero from an unavailable
certificate source.

This is a focused follow-up to issue 0018's initial dashboard delivery and is independent of the
collection, document, and company-card outcomes in issues 0026–0028. It must reuse the completed
P2 certificate state and authorization contracts; it does not add certificate lifecycle or
material-handling behavior.

## Objective and Expected Outcome

An Administrator or Operator who is allowed to administer certificates can open a bounded,
read-only certificate inventory from each certificate dashboard card and see a server-computed
total that reconciles with the card's predicate at the same evaluation. The three filters must
remain explicit: `current` means a persisted `CertificateState.CURRENT` row, `expired` means a
current row whose `not_after` is at or before the evaluation time, and `expiring` means a current
row whose `not_after` is after the evaluation time and within the approved 30-day warning window.
Replaced, pending, and storage-failed history is not silently counted as current certificate
coverage.

The verified gap is the unchecked “Todo card clicável abre lista com filtro equivalente e
contagem reconciliada” requirement in `specs/p8-dashboard-and-operational-health.md`, together
with the current `#empresas` links and the absence of a certificate inventory/count contract.
The canonical P2 status vocabulary and 30-day boundary are defined by
`specs/p2-certificate-lifecycle-and-envelope-encryption.md` and
`backend/nfx/certificates/services.py`.

## In Scope

- The `certificates.current`, `certificates.expired`, and `certificates.expiring` dashboard
  cards for roles already allowed to administer certificates.
- An additive, bounded certificate-inventory read contract owned by `nfx.certificates`, with an
  allowlisted filter, server-computed total, stable page/cursor ordering, evaluation timestamp,
  and safe company/certificate status summaries.
- Dashboard drill-down metadata and company-section navigation that preserve the selected
  certificate filter without weakening the existing `ADMINISTER_CERTIFICATES` policy or
  conflicting with the lifecycle-filter hydration from issue 0028.
- Reconciliation of each card with the same `Certificate` queryset predicates used by the
  inventory, including empty data, the exact 30-day boundary, expired certificates, replaced
  history, and concurrent/repeated read behavior.
- Loading, valid-empty, unavailable/degraded, invalid-filter, and redacted-result UI states,
  plus contributor/operator documentation for the read contract and authorization boundary.

## Out of Scope

- Certificate upload, parsing, encryption, replacement, rotation, collection eligibility,
  initial-collection jobs, or changes to certificate state transitions and migrations.
- Company, collection, document, job, rendering, disk, backup, monetary-value, notification,
  report, or other dashboard cards; collection/document/company drill-downs remain in issues
  0026–0028 and job cards are a separate P8-02 slice.
- Exposing PFX bytes, passwords, encrypted object references, private keys, raw parser/storage
  errors, or a new certificate authorization policy to Visualizer users.
- A dashboard-specific certificate owner, snapshot/cache, background job, audit event, external
  source, bulk mutation, or browser-test runner.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02 “Dashboard e saúde operacional”, progressive
  dashboard expansion. P8 remains partial; this is the next independently valuable uncovered
  certificate-card slice after the existing open drill-down issues 0026–0028.
- Canonical spec: `specs/p8-dashboard-and-operational-health.md`, repository revision
  2026-08-11 (no explicit version field), especially “Contratos e dados Proposed”, “UI,
  autorização e observabilidade”, “Falhas e testes”, and the P8-02 acceptance/DoD checklist.
- Supporting owner spec: `specs/p2-certificate-lifecycle-and-envelope-encryption.md`, repository
  revision 2026-08-11 (no explicit version field), which owns certificate state, safe metadata,
  the `<=30`-day warning boundary, encrypted material, and `ADMINISTER_CERTIFICATES` access.
- Completed prerequisites: issue 0018 provides the dashboard period/card contract; issue 0025
  provides the Admin-only backup-health branch. Issue 0028 is related UI coordination for
  `#empresas`, but it does not own certificate rows or certificate predicates.
- Current baseline: `build_dashboard()` computes the three certificate values from current rows
  and `certificate_status()`; `/api/companies/<company_id>/certificate` is a per-company
  metadata endpoint protected by `ADMINISTER_CERTIFICATES`, while no inventory endpoint exists.
- Data/migration/compatibility: derive the page and total from one canonical filtered queryset;
  preserve the existing per-company certificate response, company lifecycle filters, cursor,
  search, limit, and mutation behavior. No schema or destructive migration is expected.
- Security/observability: enforce `ADMINISTER_CERTIFICATES` server-side on every inventory and
  drill-down request. Return only bounded company identity, certificate state/status, validity
  timestamps, and days-to-expiry already permitted by the P2 metadata contract. Never log or
  return certificate material, object keys, secrets, raw exceptions, or unbounded identifiers;
  read paths must not create audit events or mutate certificate/company/job state.
- Rollout: an inventory query failure must mark only certificate cards/navigation unavailable or
  degraded, never a successful zero, and must leave company, document, collection, job, and
  Admin-only backup/operational-health cards readable. Invalid filters fail closed instead of
  falling back to an unfiltered inventory.

## Implementation Plan

1. Define one canonical inventory-filter mapping shared by dashboard aggregation and the
   certificate owner: `current` selects `state=CertificateState.CURRENT`; `expired` selects
   current rows with `not_after <= evaluated_at`; and `expiring` selects current rows with
   `evaluated_at < not_after <= evaluated_at + 30 days`. Keep the `current` card's existing
   meaning as all current rows, including the expired/expiring subsets, and do not classify
   replaced, pending, or storage-failed history into it. Reject repeated, malformed, or
   unsupported filters without broadening the query.
2. Add the bounded read contract at the certificate boundary. Compute `total` and the stable
   page from the same filtered queryset, order deterministically by company/certificate UUID,
   return the normalized filter and evaluation metadata, and serialize only safe company and
   certificate summaries. Keep status calculations in UTC using the existing service boundary;
   do not accept client-provided status counts or expose decrypted material.
3. Extend only the three certificate cards with the exact allowlisted filter and a
   role-appropriate `#empresas` destination. Hydrate certificate-filter context in the existing
   company/certificate UI, display the applied filter, total, and evaluation/freshness state,
   and preserve issue 0028's company lifecycle filter and existing unfiltered management view.
   The browser may render navigation but must not authorize, recompute totals, or bypass server
   validation.
4. Add focused unit and integration/frontend-contract coverage for current/expired/expiring
   mappings, the exact 30-day and expiration boundaries, replaced/pending/storage-failed rows,
   empty and mixed inventories, stable pagination, repeated/invalid parameters, anonymous,
   Visualizer, expired-session, and unauthorized requests, source failure, safe redaction, and
   no-write behavior. Prove concurrent reads are deterministic for one evaluation and that
   unrelated dashboard cards, certificate mutation routes, and Admin-only health remain intact.
5. Update the certificate/dashboard contributor or operator documentation and refresh Graphify
   metadata for the new relationship. On completion, synchronize the P8-02 evidence in
   `IMPLEMENTATION_PLAN.md` and `specs/README.md`, update the P8-02 spec evidence if required,
   fill this issue's Resolution, and close the work in one focused commit. Do not claim job
   cards, P9-04 hardening, or P9-05 pilot readiness complete.

## Tests

- **Unit:** allowlisted filter parsing; current/expired/expiring predicates; UTC clock and
  30-day boundary arithmetic; deterministic ordering/cursor pagination; safe serialization; and
  unavailable/error mapping.
- **Integration:** card-to-inventory reconciliation with synthetic certificates in every
  relevant state; exact expiration and 30-day boundary cases; history exclusion; empty/mixed
  results; same-query total/page consistency; role/session denial; source failure isolation;
  response redaction; repeated/concurrent reads; and no mutation/audit/job side effects.
- **Frontend:** card link construction, certificate-filter URL hydration alongside the existing
  company filter, visible filter/total/evaluation state, and loading, empty, unavailable,
  degraded, invalid, and role-restricted branches under the existing TypeScript/ESLint/Vite
  contract. Do not add a browser-test runner.
- **Validation commands:** focused dashboard/certificate/company tests plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] `certificates.current`, `certificates.expired`, and `certificates.expiring` expose
  role-appropriate drill-down metadata carrying their exact allowlisted certificate filter; a
  Visualizer receives no certificate inventory link or certificate metadata.
- [x] The server accepts only bounded authenticated inventory reads, maps the three filters to
  the canonical P2 predicates, applies UTC evaluation and the exact `<=30`-day warning boundary,
  and rejects repeated, malformed, or unsupported filters without an unfiltered fallback.
- [x] The server total and returned page use the same canonical queryset, and synthetic data
  proves each certificate card value equals its filtered inventory total, including zero-result,
  expired, exact-30-day, just-over-30-day, and mixed-company cases.
- [x] Replaced, pending, and storage-failed certificate history is excluded from current-card
  coverage; existing per-company certificate payloads, upload/replacement behavior, company
  lifecycle filters, cursor/limit/search behavior, and certificate state transitions remain
  backward compatible, with no migration or read-side mutation introduced.
- [x] Anonymous, expired-session, Visualizer, and otherwise unauthorized requests are rejected
  server-side without certificate-count or company-detail leakage; permitted roles receive only
  bounded metadata and never PFX/password/key/object/raw-error content.
- [x] A certificate database/source failure or unavailable dependency is represented as
  unavailable or degraded, never as a successful zero, and leaves unrelated dashboard cards,
  company mutations, and Admin-only operational/backup health intact.
- [x] Repeated and concurrent identical reads are deterministic for the same evaluation and
  side-effect free: no certificate mutation, company mutation, collection transition, job,
  audit event, or duplicate row is created by dashboard navigation.
- [x] Synthetic unit, integration, and frontend-contract tests cover expected and negative
  behavior, boundaries, reconciliation, pagination, RBAC, redaction, failure isolation, and
  no-write behavior; focused checks and all listed repository validation commands pass.
- [x] Contributor/operator documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the
  P8-02 spec index/evidence, this issue's Resolution, and one focused implementation commit are
  synchronized before closure.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational-health expansions.
- Spec: `specs/p8-dashboard-and-operational-health.md` — P8-02 period, cards, drill-down,
  degradation, authorization, and reconciliation contract.
- Spec: `specs/p2-certificate-lifecycle-and-envelope-encryption.md` — canonical certificate
  states, 30-day status boundary, safe metadata, encryption ownership, and RBAC.
- Product: `PRD.md` — FR-CERT-001/002, FR-DASH-001/003, SEC-005/007, AC-002, AC-013, and
  AC-014.
- Architecture: `ARCHITECTURE.md` — certificate/object ownership, server-side authorization,
  bounded observability, and dashboard composition.
- Related issues: `issues/0018_-_initial-dashboard-and-operational-health.md`,
  `issues/0025_-_dashboard-backup-health.md`, and
  `issues/0028_-_dashboard-company-drilldown-reconciliation.md`.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->

Implemented the bounded certificate dashboard drill-down and closed issue 0029.

- Shared the canonical `current`, `expired`, and `expiring` certificate predicates between
  dashboard counts and the new role-protected `/api/certificates/inventory` endpoint.
- Added bounded limit/cursor pagination, one UTC evaluation timestamp, same-queryset totals and
  pages, safe certificate/company metadata, redacted failure responses, and no-store caching.
- Added certificate-card filter metadata and the `#empresas` inventory panel with loading,
  empty, invalid, unavailable, degraded, freshness, and redacted-result behavior while
  preserving company lifecycle filtering and existing certificate mutations.
- Added unit and isolated integration coverage for boundaries, history exclusion, pagination,
  RBAC/session denial, source failure, redaction, reconciliation, and no-write behavior.
- No migration or read-side mutation was introduced.

Validation performed:

- Focused certificate/dashboard tests: `25 passed`.
- `make build` passed.
- `make lint` passed.
- Isolated Docker unit runner: `272 passed, 6 pre-existing root-fixture packaging failures`;
  all new certificate-inventory unit tests passed. The failures occur because the repository test
  image omits root-level files required by existing contract tests; the host test database port
  was also unavailable without touching an existing service (a direct host attempt reached 230
  non-database tests and reported 48 database connection errors).
- `make test-integration`: `101 passed`.
- `make smoke`: passed with isolated PostgreSQL/MinIO and web, worker, and scheduler services.
- `graphify update .`: completed; generated Graphify output was left un-staged alongside the
  pre-existing dirty worktree.

Documentation synchronized: `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md`,
`IMPLEMENTATION_PLAN.md`, `specs/README.md`, and the P8-02 specification evidence.
