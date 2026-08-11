---
id: 0028
title: "Reconcile dashboard company cards with filtered company list"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0018, 0025, 0026, 0027]
blocked_by: []
affects:
  - backend/nfx/operations/
  - backend/nfx/companies/
  - backend/nfx/urls.py
  - frontend/src/features/dashboard/
  - frontend/src/features/companies/
  - tests/
  - docs/
---

## Description

Close the company-card drill-down gap in the progressive P8-02 dashboard slice. The dashboard
currently counts `Company` rows as active (`ativa`) or inactive (the combined `cadastrada` and
`desativada` states), but both cards link to the unfiltered `#coletas` section. The existing
company endpoint accepts a single raw status filter and returns only a bounded page, so a user
cannot verify that the company list opened from a card represents the card's value.

This is a focused follow-up to issue 0018 and is independent of the collection and document
drill-downs in issues 0026 and 0027. It must reuse the completed P2 company owner and state
vocabulary; it does not introduce a dashboard-owned company read model.

## Objective and Expected Outcome

For each company card, an Administrator or Operator who is already allowed to read the P2
company list can open `#empresas` with an explicit lifecycle filter and see a bounded company
total that reconciles with the dashboard snapshot. The active card maps only to `ativa`; the
inactive card maps to both `cadastrada` and `desativada`, exactly as the current dashboard
aggregation does. Empty results are valid zeroes, while query failures or unavailable data remain
unavailable/degraded and never become a successful zero.

The verified gap is the unchecked “Todo card clicável abre lista com filtro equivalente e
contagem reconciliada” requirement in `specs/p8-dashboard-and-operational-health.md`, together
with the current `#coletas` links and lack of a company-list reconciliation total. Product
requirements are FR-DASH-001, FR-DASH-003, and AC-013.

## In Scope

- The `companies.active` and `companies.inactive` dashboard cards only.
- An additive, bounded company-list read contract owned by `nfx.companies` that accepts one
  allowlisted lifecycle filter, maps it to the existing `CompanyStatus` values, returns a
  server-computed total, and retains stable cursor/page behavior.
- Dashboard drill-down metadata and company-section URL hydration so the selected lifecycle
  filter is visible and applied by the server when a card is followed.
- Reconciliation of both card values with the same status predicates used by the company query,
  including zero-result data and concurrent company changes between reads.
- Loading, valid-empty, unavailable/degraded, invalid-filter, and redacted-result UI states,
  plus documentation of the read contract and authorization boundary.

## Out of Scope

- Certificate, collection, document, job, rendering, disk, backup, monetary-value, notification,
  report, or other dashboard cards; those remain separate P8-02 slices or existing issues 0026
  and 0027.
- Changes to company lifecycle transitions, status vocabulary, CNPJ normalization, enrichment,
  flows, mutations, audit events, collection state, or P2 business ownership.
- Broadening the completed P2 `Action.ADMINISTER_COMPANIES` read policy to Visualizers. The PRD's
  general statement that authenticated users can consult companies conflicts with the completed
  P2 contract/code, which restricts company administration reads to Administrators and Operators;
  this issue preserves that baseline and must omit or safely disable the company drill-down for a
  Visualizer rather than expose a protected section or resolve the policy discrepancy.
- A dashboard-specific owner, snapshot/cache, background job, migration, new persistence, bulk
  mutation, external endpoint, or browser-test runner.
- Company payloads containing certificates, secrets, fiscal XML/PDF, object keys, raw exceptions,
  unbounded search data, or unnecessary identifiers in responses, logs, metrics, fixtures, or
  audit records.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02, “Dashboard e saúde operacional”, progressive
  dashboard expansion. This is the next uncovered company-card slice; P8-02 remains partial
  until its independently delivered cards satisfy the spec's drill-down and reconciliation
  criteria.
- Canonical spec: `specs/p8-dashboard-and-operational-health.md`, repository revision
  2026-08-11 (no explicit version field), especially “Contratos e dados Proposed”, “UI,
  autorização e observabilidade”, “Falhas e testes”, and the P8-02 acceptance/DoD checklist.
- Supporting completed spec: `specs/p2-company-lifecycle-and-public-enrichment.md`, repository
  revision 2026-08-11 (no explicit version field), which owns `Company`, lifecycle states,
  `GET /api/companies`, and the `ADMINISTER_COMPANIES` server policy.
- Product/architecture references: `PRD.md` FR-COMP-002, FR-DASH-001, FR-DASH-003, AC-013, and
  AC-023; `ARCHITECTURE.md` sections 10.1, 14–16, 32, 36, and 37. Company remains the owner
  of lifecycle state; operations composes the dashboard value and link.
- Completed prerequisites: issue 0018 (initial P8-02 dashboard) and issue 0025 (Admin-only
  backup-health integration). Issues 0026 and 0027 are adjacent but own collection-execution and
  document-card reconciliation, not company rows.
- Data/migration/compatibility: derive the total and page from one canonical filtered queryset;
  preserve existing raw `status`, `search`, `limit`, `cursor`, default response behavior, and
  mutation routes for existing callers. No migration or destructive data change is expected.
- Security/observability: enforce the existing server-side company read policy on every request;
  do not treat a client-supplied dashboard link as authorization. Keep response fields bounded to
  the existing safe company list contract, and do not create a dashboard audit event or log raw
  query data. A Visualizer must receive the existing authorization outcome and no company detail.
- Rollout: a company query/count failure must degrade only company cards/list navigation and must
  not affect document, collection, job, or Admin-only backup/operational-health cards. Invalid
  lifecycle filters must fail closed instead of falling back to an unfiltered company list.

## Implementation Plan

1. Define the additive lifecycle-filter contract at the company-list boundary. Map `active` to
   `CompanyStatus.ACTIVE` and `inactive` to the exact `REGISTERED`/`DEACTIVATED` set already used
   by `_company_counts`; reject repeated, unsupported, malformed, or conflicting filter values.
   Keep the existing raw status behavior compatible for callers that need one physical state.
2. Build the bounded page and server-side total from the same filtered `Company` queryset, with a
   stable UUID order and the existing safe company serialization. Do not count from a second
   dashboard query, broaden an invalid filter, expose mutation-only data, or change lifecycle
   state while reading.
3. Extend only the two dashboard cards with the selected lifecycle filter and role-appropriate
   `#empresas` navigation. Hydrate the filter in the companies feature, display the server total
   and applied state, and preserve the existing unfiltered management view and mutation flows.
   The browser may render the filter but must not authorize, recompute totals, or bypass server
   validation.
4. Add focused unit, integration, and frontend-contract coverage for active/inactive mappings,
   the combined inactive states, exact totals, empty data, stable pagination, invalid/repeated
   filters, anonymous/expired/unauthorized sessions, source failure, response redaction, and
   repeated/concurrent read behavior. Prove unrelated dashboard cards and company mutations remain
   unchanged.
5. Update the relevant dashboard/company contributor or operator documentation and refresh
   Graphify metadata for the new relationship. On completion, synchronize only the P8-02 evidence
   in `IMPLEMENTATION_PLAN.md` and `specs/README.md`, fill this issue's Resolution, and close the
   work in one focused commit. Do not claim certificate/job cards, P9-04 hardening, or P9-05 pilot
   readiness complete.

## Tests

- **Unit:** lifecycle-filter parsing and allowlist; active/inactive status mapping; shared
  queryset/count invariants; deterministic cursor pagination; and safe unavailable/error mapping.
- **Integration:** both dashboard-card/list reconciliations with synthetic companies in all three
  lifecycle states; empty and mixed-state data; concurrent/repeated reads; default endpoint
  compatibility; Administrator/Operator access; Visualizer/anonymous/expired-session rejection;
  response redaction; source failure isolation; and no mutation/audit side effects.
- **Frontend:** company-card link construction, URL hydration, displayed filter/total, and
  loading, valid, empty, unavailable, invalid, and role-restricted branches under the existing
  TypeScript/ESLint/Vite contract. Do not add a browser-test runner.
- **Validation commands:** focused dashboard/company tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] `companies.active` and `companies.inactive` expose role-appropriate drill-down metadata
  carrying the exact allowlisted lifecycle filter; permitted users land in `#empresas`, while a
  Visualizer is not given a link that exposes the protected company-management section.
- [x] The server accepts only bounded authenticated company-list reads, maps `active` to
  `ativa` and `inactive` to `cadastrada` plus `desativada`, rejects repeated/conflicting/
  unsupported values, and never falls back to an unfiltered result.
- [x] The server total and returned page use the same canonical status queryset, and synthetic
  data proves each company card value equals its filtered total, including zero-result and mixed
  lifecycle-state cases; concurrent reads do not silently alter the selected filter.
- [x] Existing raw-status/search/cursor/limit behavior, company payload compatibility, lifecycle
  mutations, flow state, enrichment, and audit behavior remain unchanged; no migration, cache,
  snapshot, job, or state transition is introduced by the read path.
- [x] Anonymous, expired, Visualizer, and otherwise unauthorized requests are rejected by the
  server-side policy without company-count or company-detail leakage; permitted roles receive
  only the existing bounded safe company metadata.
- [x] A company database/source failure or unavailable dependency is represented as unavailable or
  degraded, never as a successful zero, and leaves unrelated dashboard cards and Admin-only
  operational/backup health intact.
- [x] Repeated and concurrent identical reads are deterministic and side-effect free: no company
  mutation, collection transition, job, audit event, or duplicate row is created by navigation.
- [x] Synthetic unit, integration, and frontend-contract tests cover expected and negative
  behavior, lifecycle mapping, reconciliation, pagination, RBAC, redaction, failure isolation,
  and no-write behavior; focused checks and all listed validation commands pass.
- [x] Contributor/operator documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the
  P8-02 spec index, this issue's Resolution, and one focused implementation commit are
  synchronized before closure.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational-health expansions.
- Spec: `specs/p8-dashboard-and-operational-health.md` — P8-02 period, cards, drill-down,
  degradation, authorization, and reconciliation contract.
- Spec: `specs/p2-company-lifecycle-and-public-enrichment.md` — canonical company states,
  company-list owner, safe payload, and completed authorization boundary.
- Product: `PRD.md` — FR-COMP-002, FR-DASH-001, FR-DASH-003, AC-013, and AC-023.
- Architecture: `ARCHITECTURE.md` — company ownership, role enforcement, safe read boundaries,
  observability, and dashboard composition.
- Related issues: `issues/0018_-_initial-dashboard-and-operational-health.md`,
  `issues/0025_-_dashboard-backup-health.md`,
  `issues/0026_-_dashboard-collection-drilldown-reconciliation.md`, and
  `issues/0027_-_dashboard-document-drilldown-reconciliation.md`.

---

## Resolution

Implemented and closed the P8-02 company-card reconciliation slice.

- Added the canonical `active`/`inactive` lifecycle mapping in `nfx.companies`, preserving the
  existing raw `status`, `search`, `limit`, and UUID cursor filters. The bounded read response now
  includes the normalized filter, full filtered total, truncation flag, and stable page cursor;
  total and page use the same status queryset.
- Updated `companies.active` and `companies.inactive` dashboard cards for Administrator/Operator
  drill-down to `#empresas`, while Visualizers receive no protected company-management link.
  Company source failures return safe `503` responses and do not degrade unrelated dashboard data.
- Hydrated lifecycle filters in the React companies section and added visible reconciled totals,
  valid-empty, loading, invalid, unavailable, and degraded states. Existing company mutation and
  lifecycle flows remain unchanged.
- No migration, cache, snapshot, job, audit event, or read-side company mutation was introduced.

Validation performed:

- `make build` — passed.
- `make lint` — passed (Ruff, mypy over 110 backend files, TypeScript/ESLint).
- `make test-unit` — 268 passed, 1 known botocore deprecation warning.
- `make test-integration` — isolated PostgreSQL/MinIO migration/schema validation and 93 passed,
  7 known botocore deprecation warnings.
- `make smoke` — passed with isolated web, worker, scheduler, PostgreSQL, and MinIO services.
- Focused parser/dashboard tests — 23 passed.
- `graphify update .` — code graph refreshed; the pre-existing dirty generated Graphify outputs
  were preserved and not included in this focused commit.

Documentation synchronized in `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md`,
`specs/p8-dashboard-and-operational-health.md`, `specs/README.md`, and `IMPLEMENTATION_PLAN.md`.

Status: closed.
