---
id: 0042
title: "Complete the P8-02 dashboard cross-owner contract gate"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0018, 0025, 0026, 0027, 0028, 0029, 0030]
blocked_by: []
affects:
  - backend/nfx/operations/
  - backend/nfx/companies/
  - backend/nfx/certificates/
  - backend/nfx/collection/
  - backend/nfx/documents/
  - backend/nfx/jobs/
  - tests/
  - docs/
---

## Description

Complete the remaining independently valuable P8-02 validation/documentation slice for the
dashboard capabilities already delivered by issues 0018 and 0025–0030. The endpoint currently
has the required period arithmetic, explicit unavailable/freshness states, and per-owner
drill-down contracts, but the repository has no single cross-owner gate proving that the current
dashboard response, all corresponding list owners, authorization matrix, failure isolation, and
read-only behavior remain one compatible contract. P8-02 must remain partial for capabilities
that are still explicitly unavailable; this issue closes only the verification gap for the
implemented capability set.

## Objective and Expected Outcome

The current P8-02 dashboard slice has one repeatable synthetic contract matrix covering every
implemented card and its owning list/query boundary. Administrators and permitted Operators can
reconcile dashboard totals with the equivalent server-filtered reads; Visualizers receive only
their allowed cards; anonymous, expired, and unauthorized requests fail closed; source failures
remain explicit and isolated; and repeated/concurrent reads do not create state. The repository
also records calculate-on-read as the adopted current strategy and keeps unavailable fiscal-source
and disk capabilities visibly unavailable without inventing values or claiming P9-05 readiness.

## In Scope

- A cross-owner contract matrix for the existing P8-02 cards: seven document filters, the
  collection execution filters, active/inactive company lifecycle filters, current/expired/
  expiring certificate inventory filters, and pending/failed/blocked job filters.
- Verification that period cards and their owners use the same `[from,to)` civil-date selection
  and equal-duration consecutive previous period, while snapshot cards reconcile at the owner’s
  evaluated timestamp; all cards must preserve their allowlisted predicate, total, deterministic
  page, bounded safe fields, and valid-empty semantics.
- One role/session matrix for Administrator, Operator, Visualizer, anonymous, expired, and
  otherwise unauthorized access, including the Admin-only operational-health and backup boundary
  and the absence of certificate/company detail leakage.
- Cross-source failure and freshness checks proving that an unavailable owner produces an explicit
  unavailable/degraded result rather than a successful zero and does not erase unrelated cards.
- Repeated and concurrent read checks proving no dashboard-owned snapshot/cache, job, lease,
  audit event, cursor advancement, mutation, or other durable side effect is created.
- Documentation of the existing calculate-on-read decision, the current capability matrix, and
  the remaining unavailable/proposed capabilities as a bounded P8-02 follow-up.

## Out of Scope

- New dashboard cards, monetary aggregation, notifications, reports, polling, client-side
  aggregation, a dashboard-specific owner, cache/materialization, migration, or persistent
  snapshot.
- Changes to company, certificate, collection, document, job, ingestion, rendering, backup,
  retention, or authorization business rules except a minimal compatibility correction proven by
  the new gate.
- Enabling real NF-e/ADN transport, fiscal-source status, disk-capacity health, physically
  separate backup, trusted CA, or any P9-05 pilot/homologation evidence.
- Repeating the completed feature/UI modernization work in issues 0034–0041 or adding a new
  browser-test framework.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational-health expansions,
  currently in progress by increments; this issue is the cross-owner validation/documentation
  increment after issues 0018 and 0025–0030.
- Canonical spec: `specs/p8-dashboard-and-operational-health.md` — P8-02, repository revision
  2026-08-12 (no explicit version field), especially “Contratos e dados Proposed”, “UI,
  autorização e observabilidade”, “Falhas e testes”, and the acceptance/DoD checklist.
- Supporting owners: `specs/p2-company-lifecycle-and-public-enrichment.md`,
  `specs/p2-certificate-lifecycle-and-envelope-encryption.md`,
  `specs/p4-fiscal-document-ingestion-and-integrity.md`,
  `specs/p7-document-consultation-and-individual-download.md`, and
  `specs/p3-durable-jobs-leases-and-policy-engine.md` define the states, authorization, and
  bounded list/query contracts that the dashboard must reuse.
- Completed prerequisites: issues 0018 (initial dashboard), 0025 (Admin-only backup health),
  0026 (collection drill-down), 0027 (document drill-down), 0028 (company drill-down), 0029
  (certificate drill-down), and 0030 (job drill-down). No open or in-progress issue covers this
  cross-owner outcome.
- Data/migration/compatibility: use synthetic/local data and the existing owners; preserve
  `/api/dashboard`, `/api/documents`, `/api/collections/executions`, `/api/companies`,
  `/api/certificates/inventory`, and `/api/jobs/observability` request/response compatibility.
  No schema change, backfill, destructive action, or new persistence is expected.
- Security/observability: enforce the existing server-side policies on every endpoint and assert
  bounded identifiers, safe errors, no fiscal payload/certificate material/object keys/leases or
  raw exceptions, and no high-cardinality test or metric labels. The gate must not weaken the
  Admin-only health/backup contract or expose a protected drill-down to a Visualizer.
- Rollout: run the gate against isolated synthetic services/data. A failure should identify the
  owning contract and block closure without changing unrelated card behavior; no production
  transport or external credential is needed.

## Implementation Plan

1. Build a compact matrix from the existing dashboard card IDs and owner allowlists. For each
   period card, assert the dashboard predicate and owner list/query predicate are identical and
   the response total equals the card value for the selected current period. For company and
   certificate snapshot cards, assert the equivalent owner predicate and evaluated-at semantics.
   In both cases the returned page is bounded and deterministic, and a real empty result remains
   a zero rather than unavailable.
2. Exercise period edges using Brasília civil dates, including the exact `[from,to)` boundary,
   equal-duration predecessor, invalid/repeated/reversed/overlong bounds, and any DST-relevant
   local-date fixture supported by the existing test setup. Verify that links/filters preserve the
   canonical current period and do not broaden an invalid or conflicting filter.
3. Run the role/session matrix against dashboard and drill-down endpoints. Verify the permitted
   card set, Admin-only health/backup details, anonymous/expired/Visualizer denials, safe error
   mapping, and redaction of fiscal content, certificate material, object references, leases,
   policies, and raw exceptions. Where a card carries a period, verify its link preserves that
   period; snapshot-card links must preserve their owner filter without inventing period semantics.
4. Inject one owner failure at a time and repeat identical reads concurrently. Assert explicit
   unavailable/degraded/freshness states, isolation from unrelated cards, deterministic payloads,
   and no database/object-store writes, jobs, leases, audit events, cursor advancement, or other
   domain transitions. Keep any implementation adjustment limited to a contract defect exposed by
   these checks; do not add a new owner or persistence path.
5. Record the already implemented calculate-on-read/no-dashboard-cache boundary and update the
   relevant dashboard/operations documentation plus the P8-02 spec/index and plan evidence. Keep
   fiscal-source, disk, rendering, and other unavailable capabilities explicitly bounded; do not
   mark the whole P8-02 spec or P9-05 complete. Refresh Graphify metadata as required by the repo
   workflow, fill this issue's Resolution, and close in one focused commit.

## Tests

- **Unit:** matrix construction, period arithmetic/boundaries, allowlisted filter/predicate
  mapping, real-zero versus unavailable/freshness states, redaction, and no-write assertions.
- **Integration:** one synthetic reconciliation dataset covering all current card/owner pairs;
  role and session denials; empty and mixed results; invalid/repeated filters; source failure
  isolation; deterministic pagination; repeated/concurrent reads; and no migration, audit, job,
  lease, cursor, or domain-state side effect.
- **Frontend contract:** only if the cross-owner response matrix reveals a current payload/state
  mismatch, extend the existing contract fixture for the affected state; do not add a browser
  runner or duplicate issues 0036–0041.
- **Validation commands:** focused dashboard/owner integration tests, `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A repeatable synthetic matrix covers every implemented P8-02 dashboard card and its
  corresponding server-owned list/query filter, with the exact allowlist and predicate recorded.
- [x] Current and previous periods have equal duration, are consecutive and non-overlapping,
  use the documented `[from,to)` boundary, and reject malformed, repeated, reversed, incomplete,
  and overlong input without broadening the query.
- [x] For every current card/owner pair, the server-computed total reconciles with the dashboard
  value for mixed and zero-result data at the card’s applicable period or evaluated timestamp,
  while the bounded page and cursor/order remain compatible and deterministic.
- [x] Owner failure, unavailable dependency, and unknown freshness are represented explicitly and
  degrade only the affected card/list; no failure is converted into a successful zero or false
  freshness.
- [x] Administrator, Operator, and Visualizer responses preserve the existing role matrix;
  anonymous, expired, and otherwise unauthorized requests fail closed without exposing counts,
  protected links, health/backup details, certificate material, fiscal payloads, or raw errors.
- [x] Repeated and concurrent dashboard/drill-down reads are deterministic and side-effect free:
  they create no snapshot/cache, migration, job, lease, audit event, cursor advancement,
  mutation, or fiscal/domain state transition.
- [x] The adopted calculate-on-read strategy and no-dashboard-persistence boundary are documented
  with source freshness/reconciliation ownership; unavailable fiscal-source, disk, rendering, and
  externally blocked pilot capabilities remain explicitly unavailable or blocked.
- [x] Synthetic unit/integration coverage and any justified existing frontend-contract adjustment
  pass, using no production endpoints, credentials, fiscal content, or certificate material.
- [x] Dashboard/operations documentation, the P8-02 spec/index and `IMPLEMENTATION_PLAN.md` are
  synchronized without claiming the full P8-02 spec or P9-05 complete; this issue's Resolution,
  Graphify metadata, and one focused commit are recorded before closure.
- [x] Focused checks, `make lint`, `make test-unit`, `make test-integration`, `make build`, and
  `make smoke` pass without unrelated regressions.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational-health expansions.
- Spec: `specs/p8-dashboard-and-operational-health.md` — P8-02 current cards, period contract,
  failure/freshness behavior, authorization, reconciliation, and DoD.
- Supporting specs: P2 company/certificate lifecycle, P3 durable jobs/health, P4 ingestion and
  P7 document consultation/list contracts listed under Dependencies and Notes.
- Related issues: `issues/0018_-_initial-dashboard-and-operational-health.md`,
  `issues/0025_-_dashboard-backup-health.md`, `issues/0026_-_dashboard-collection-drilldown-reconciliation.md`,
  `issues/0027_-_dashboard-document-drilldown-reconciliation.md`,
  `issues/0028_-_dashboard-company-drilldown-reconciliation.md`,
  `issues/0029_-_dashboard-certificate-drilldown-reconciliation.md`, and
  `issues/0030_-_dashboard-job-drilldown-reconciliation.md`.

---

## Resolution

Implemented the P8-02 cross-owner contract gate in
`tests/unit/test_dashboard_cross_owner_contract.py` and
`tests/integration/test_dashboard_cross_owner_contract.py`. The synthetic integration dataset
covers all 20 implemented cards, exact canonical allowlists, Brasília `[from,to)` boundaries,
equal-duration predecessor periods, deterministic bounded owner pages, real zero versus
unavailable/freshness states, source-failure isolation, redaction, role/session authorization, and
repeated/concurrent read behavior. No application, migration, endpoint, or frontend contract
changes were necessary; the gate found no compatibility defect.

The documented decision remains calculate-on-read with no dashboard snapshot/cache. Dashboard,
collection, company, certificate, and job reads are side-effect free; document consultation keeps
the pre-existing P7 read-audit event, which is owner-prescribed evidence and not dashboard-owned
persistence. Fiscal-source, disk, rendering limitations where unavailable, real transport, and
P9-05 external pilot evidence remain explicitly bounded.

Validation completed:

- `python -m pytest tests/unit/test_dashboard.py tests/unit/test_dashboard_cross_owner_contract.py` — 23 passed; one existing botocore deprecation warning.
- `python -m ruff check tests/unit/test_dashboard_cross_owner_contract.py tests/integration/test_dashboard_cross_owner_contract.py` — passed.
- `make test-integration` with isolated Docker PostgreSQL/MinIO — 121 passed; seven existing botocore deprecation warnings.
- `make lint` — passed (Ruff, mypy, and frontend lint).
- `make test-unit` — 315 passed; one existing botocore deprecation warning.
- `make build` — passed (Django checks and Vite build).
- `make smoke` — passed against isolated Docker services.
- The pre-change local integration attempt was unavailable because PostgreSQL was not listening on `127.0.0.1:5432`; the required isolated Docker run passed afterward.

Documentation synchronized in `specs/p8-dashboard-and-operational-health.md`, `specs/README.md`,
`IMPLEMENTATION_PLAN.md`, and `docs/OPERATIONS.md`. No frontend contract adjustment was needed,
so the frontend-contract criterion is N/A with the issue’s scope-permitted reason. Graphify was
refreshed after the code/test changes. This issue is closed.
