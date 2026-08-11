---
id: 0026
title: "Reconcile dashboard collection cards with filtered execution drill-down"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0004, 0005, 0018, 0025]
blocked_by: []
affects:
  - backend/nfx/collection/
  - backend/nfx/operations/
  - backend/nfx/urls.py
  - frontend/src/features/collections/
  - frontend/src/features/dashboard/
  - tests/
  - docs/
---

## Description

Close the collection-card drill-down gap in the progressive P8-02 dashboard slice. The
dashboard already calculates `collections.recent`, `collections.running`,
`collections.failed`, `collections.blocked`, and `collections.partial` from
`CollectionExecution` records for the selected period, but each card currently links only to
the unfiltered `#coletas` section. The existing collection view exposes company flow state and
the latest execution per flow, so it cannot prove that the card's period/state count matches the
list the user opens.

This is a focused follow-up to issue 0018's initial dashboard delivery and is separate from issue
0025's completed backup-health integration. The remaining company, certificate, and job-card
drill-down gaps are follow-up work and are not part of this issue.

## Objective and Expected Outcome

For every collection execution card, an authenticated user can open a read-only collection
execution view carrying the exact dashboard period and execution-state filter. The view returns
the bounded matching execution count and safe execution summaries, and the count reconciles with
the card for the same `[from,to)` period. A source failure, invalid filter, expired session, or
unsupported state fails safely without inventing zeroes or exposing fiscal payloads, while
repeated and concurrent reads remain side-effect free.

The verified gap is the unchecked “Todo card clicável abre lista com filtro equivalente e
contagem reconciliada” requirement in `specs/p8-dashboard-and-operational-health.md` and the
non-equivalent `#coletas` links in the current dashboard implementation. The approved product
requirements are FR-DASH-003 and AC-013; no new dashboard business metric, cache, or persistence
policy is needed.

## In Scope

- An additive, bounded read-only collection-execution query owned by `nfx.collection`, accepting
  the dashboard's `from`/`to` civil dates and one of the existing collection execution states
  represented by the five dashboard cards.
- Exact `[from,to)` filtering in the same Brasília/civil-date semantics used by the dashboard,
  with a server-computed total and a stable, bounded page of safe execution summaries.
- Dashboard drill-down metadata that preserves the selected period and state, and collection UI
  behavior that loads and visibly applies that filter when the user follows a card link.
- Reconciliation tests proving each of the five card totals equals the filtered execution total,
  including empty periods, multiple companies/families, and executions on both period boundaries.
- Independent source-error/degraded handling, authenticated server-side authorization, safe
  response redaction, no-write behavior, and contributor/operator documentation of the contract.

## Out of Scope

- Company, certificate, job, document, rendering, backup, disk, monetary-value, notification, or
  report cards and their drill-downs; create separate P8-02 slices for those gaps.
- Changes to collection state transitions, scheduling, leases, retry/cooldown/block policy,
  cursors, ingestion, fiscal adapters, or the existing company-flow command endpoints.
- A new collection state vocabulary, dashboard-specific owner, snapshot/cache, migration,
  background job, audit event, metric family, or external monitoring integration.
- Fiscal XML, document content, object keys, certificate material, raw provider errors, or
  production credentials in the response, logs, fixtures, or tests.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02, “Dashboard e saúde operacional”, progressive
  dashboard expansion; this is the next independently valuable collection-card slice.
- Canonical spec: `specs/p8-dashboard-and-operational-health.md`, repository revision
  2026-08-11 (no explicit version field), especially “Contratos e dados Proposed”, “Falhas e
  testes”, and the P8-02 acceptance/DoD checklist.
- Product/architecture references: `PRD.md` FR-DASH-003 and AC-013; `ARCHITECTURE.md` sections
  14, 19, 20, 32, 36, and 37. Collection remains the owner of execution state; operations only
  composes the read model and drill-down link.
- Completed prerequisites: issue 0004 (safe job/health observability), issue 0005 (collection
  control and execution state), issue 0018 (initial P8-02 dashboard), and issue 0025 (dashboard
  backup-health integration). No issue currently covers this filtered execution outcome.
- Data/compatibility: prefer an additive read contract and preserve the default
  `GET /api/collections` company-flow response for existing callers. No schema or destructive
  migration is expected; if query pagination is needed, keep it bounded and deterministic.
- Security/observability: enforce the existing authenticated read policy on the endpoint and
  every drill-down request; return only bounded IDs, company name/identifier already permitted by
  the collection view, family, requested scope, state/outcome/recovery, safe error, and safe
  timestamps. Do not log fiscal content, correlation payloads, secrets, object keys, or raw
  exceptions. Reads must not create jobs, audits, collection records, or state transitions.
- Rollout: a collection query failure must degrade only the collection drill-down/card path and
  must not change unrelated dashboard cards. Invalid or unsupported filters return the existing
  safe client-error contract rather than a broad unfiltered result.

## Implementation Plan

1. Define the collection-owner read contract for a bounded execution drill-down. Parse exactly the
   dashboard period parameters and one allowlisted execution-state filter, reject repeated,
   missing, reversed, overlong, or unsupported values, and use the same local date-boundary
   helper as dashboard aggregation. Preserve the existing unfiltered collection response for
   current callers and do not add a second state mapping.
2. Query `CollectionExecution` by `created_at >= start` and `created_at < end` plus the selected
   state, order by a stable timestamp/UUID tie-breaker, and return `total`, normalized filter
   metadata, and a bounded page of redacted execution summaries. Keep the total query and the
   dashboard's five state mappings on the same canonical model fields so `running`, `failed`,
   `blocked`, and `partial` cannot drift from their cards; preserve `completed`/valid-empty
   executions in the existing source contract without silently classifying them into another
   card.
3. Extend dashboard drill-down payloads for the five collection cards with the exact period and
   state, and update the collections feature to consume that context on navigation, display the
   filtered total and matching rows, and distinguish loading, valid empty, unavailable, invalid,
   and degraded results. The browser may render links and state but must not authorize, filter
   outside the server contract, or recompute the total.
4. Add focused unit and integration coverage for all five states, inclusive/exclusive boundaries,
   previous/current periods, multiple companies and families, stable pagination, repeated/invalid
   parameters, anonymous/expired sessions, source failure, redaction, and no-write behavior.
   Add regression coverage that the existing default collection view, dashboard cards, backup
   health, and unrelated cards remain unchanged. Use synthetic fixtures only.
5. Update the relevant dashboard/collection contributor or operator documentation and refresh
   Graphify metadata for the new relationship. On completion, synchronize the P8-02 evidence in
   `IMPLEMENTATION_PLAN.md`, `specs/p8-dashboard-and-operational-health.md`, and
   `specs/README.md`, fill this issue's Resolution, and close the work in one focused commit.

## Tests

- **Unit:** bounded period/state parsing; Brasília `[from,to)` conversion; state allowlist;
  deterministic ordering/pagination; safe execution serialization; and source-error mapping.
- **Integration:** five card-to-query reconciliation cases; boundary timestamps; empty and
  multi-company/family periods; default collection endpoint compatibility; authenticated role
  access; invalid/expired sessions; source failure isolation; response redaction; and repeated
  reads with no database/job/audit mutation.
- **Frontend:** period/state drill-down navigation and loading, valid, zero, unavailable,
  invalid, degraded, and redacted-result branches under the existing TypeScript/ESLint/Vite
  contract. Do not add a browser-test runner.
- **Validation commands:** focused dashboard/collection tests plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] Each of `collections.recent`, `collections.running`, `collections.failed`,
  `collections.blocked`, and `collections.partial` exposes a drill-down carrying the exact
  selected period and its canonical execution-state filter.
- [x] The server accepts only bounded, authenticated read requests with valid `from`/`to` dates
  and an allowlisted state, uses `[from,to)` Brasília semantics, and rejects invalid, repeated,
  reversed, overlong, or unsupported parameters without falling back to an unfiltered result.
- [x] For synthetic data, each collection card value equals the filtered execution `total` for
  the same period/state, including executions exactly at the start/end boundary and periods with
  no matches; no dashboard-specific count or state vocabulary is introduced.
- [x] The drill-down returns a stable bounded page and safe summaries only; it excludes fiscal
  payloads, XML/PDF content, object keys, certificate data, raw provider exceptions, and
  unbounded correlation or error data.
- [x] The existing default collection/company-flow response and collection command behavior stay
  backward compatible, and no migration, cache, snapshot, job, audit event, cursor, lease, or
  collection state transition is introduced by a read.
- [x] Anonymous, expired, and unauthorized requests are rejected server-side; permitted roles
  receive only the same collection scope already exposed by the existing read contract.
- [x] A collection database/source failure or unavailable dependency marks only the affected
  card/drill-down unavailable or degraded, never as a successful zero, and leaves unrelated
  dashboard cards and Admin-only backup health intact.
- [x] Repeated and concurrent identical reads are idempotent and side-effect free, with no
  duplicate rows or changing totals caused by the read path.
- [x] Synthetic unit, integration, and frontend-contract tests cover expected and negative
  behavior, boundaries, reconciliation, redaction, RBAC, error isolation, and no-write
  behavior; focused checks and all listed validation commands pass.
- [x] Documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the P8-02 spec/index, this
  issue's Resolution, and one focused implementation commit are synchronized before closure.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational health expansions.
- Spec: `specs/p8-dashboard-and-operational-health.md` — current P8-02 contract and DoD.
- Product: `PRD.md` — FR-DASH-003 and AC-013.
- Architecture: `ARCHITECTURE.md` — state ownership, collection/cursor boundaries, safe
  degradation, observability, and test strategy.
- Related issues: `issues/0005_-_manual-collection-control.md`,
  `issues/0018_-_initial-dashboard-and-operational-health.md`, and
  `issues/0025_-_dashboard-backup-health.md`.

---

## Resolution

Implemented the collection execution drill-down slice for P8-02.

- Added the authenticated, read-only `GET /api/collections/executions` contract with required
  `from`, `to`, and allowlisted `state` parameters, Brasília `[from,to)` bounds, a 50-row bounded
  page, stable timestamp/UUID ordering, server-side totals, and safe redacted summaries.
- Reused the collection-owned state mapping and query for dashboard reconciliation; all five
  collection cards now carry the selected period and canonical filter in their drill-down URL.
- Added the React collection execution view with loading, valid-empty, success, invalid,
  unavailable, degraded, and bounded-result states. Existing collection/company-flow commands
  remain unchanged.
- No migration was needed. The read path creates no job, audit event, cursor, lease, cache,
  snapshot, collection row, or state transition, and source failures return safe `503` responses.

Validation performed:

- `python -m pytest tests/unit/test_dashboard.py tests/unit/test_collection_execution_query.py`
- `python -m ruff check backend/nfx/collection backend/nfx/operations tests/unit/test_collection_execution_query.py tests/integration/test_collection_execution_endpoint.py`
- `NFX_PROFILE=test ... python -m mypy backend`
- `npm --prefix frontend run lint && npm --prefix frontend run build`
- `make build`, `make lint`, `make test-integration`, and `make smoke` all passed; the integration
  target used ephemeral PostgreSQL/MinIO, migrations, schema check, and the full integration
  suite (82 passed).
- The full unit suite collected 251 tests in the isolated test environment: 245 passed and 6
  pre-existing repository-test-image contract checks failed because that image omits the root
  `Makefile`, runtime Compose file, and `.env.example`; the issue-specific unit tests passed.
- `graphify update .`

Documentation synchronized in `specs/p8-dashboard-and-operational-health.md`,
`specs/README.md`, `IMPLEMENTATION_PLAN.md`, `docs/DEVELOPMENT.md`, and `docs/OPERATIONS.md`.

Status: closed.
