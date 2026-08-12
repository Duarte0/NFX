---
id: 0030
title: "Reconcile dashboard processing cards with filtered job observability"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0001, 0002, 0004, 0018]
blocked_by: []
affects:
  - backend/nfx/jobs/
  - backend/nfx/operations/
  - backend/nfx/urls.py
  - frontend/src/features/dashboard/
  - tests/
  - docs/
---

## Description

Close the remaining implemented-source drill-down gap for the P8-02 processing cards. The
dashboard currently aggregates `jobs.pending`, `jobs.failed`, and `jobs.blocked` from durable
`Job` rows, but all three cards link to the generic `#coletas` anchor. There is no bounded job
list carrying the selected period and the exact canonical state/outcome mapping, so the displayed
count cannot be reconciled with the view the user opens.

This is a focused follow-up to issue 0018 and is independent of issues 0026–0029, which cover
collection, document, company, and certificate card drill-downs. It must reuse P3-01/P3-02 job
ownership and P3-04 observability semantics rather than introducing a dashboard job state or a
second retry/outcome model.

## Objective and Expected Outcome

For an authenticated dashboard user, each processing card opens a read-only, bounded job
observability view with the exact selected `[from,to)` period and its canonical filter. The view
returns a server-computed total and safe job summaries whose total reconciles with the card for
the same period. Invalid filters, unavailable durable state, expired sessions, or unauthorized
requests fail safely without becoming a successful zero or exposing payloads, lease details, or
raw errors. Repeated and concurrent reads remain side-effect free.

The verified gap is the unchecked “Todo card clicável abre lista com filtro equivalente e
contagem reconciliada” requirement in `specs/p8-dashboard-and-operational-health.md` and the
three current `href="#coletas"` links for the job cards. The approved product requirements are
FR-DASH-003, FR-OPS-001, BR-OPS-001, and AC-013; no new job metric or persistence policy is
needed.

## In Scope

- The three displayed processing cards: pending, failed, and blocked.
- Dashboard drill-down metadata preserving the selected period and canonical job filter.
- A bounded, authenticated, read-only job query/list contract with a server-computed total and
  stable deterministic pagination.
- Canonical mappings matching `_job_counts`: pending is queued or running; failed is the existing
  temporary, permanent, or partial `last_outcome` set; blocked is the durable blocked state.
- A processing drill-down UI that applies the server-provided period/filter, shows safe rows and
  total, and distinguishes loading, valid empty, unavailable, invalid, and degraded results.
- Unit, integration, and frontend-contract coverage for reconciliation, redaction, authorization,
  source failure, boundaries, pagination, concurrency, and no-write behavior.

## Out of Scope

- Collection-execution, document, company, certificate, rendering, disk, backup, fiscal-source,
  monetary-value, notification, report, export, or retention cards.
- Changes to job enqueue, claim, lease, retry, cooldown, blocking, scheduler, worker, handler,
  collection state, policy selection, or operational-health evaluation semantics.
- A new job state or outcome vocabulary, dashboard-specific job owner, snapshot/cache, migration,
  audit event, background job, or external monitoring integration.
- Returning job payloads, credentials, certificates, XML/PDF content, object keys, lease owners,
  policy internals, stack traces, raw provider errors, or unbounded correlation data.
- Client-side authorization, filtering, total recomputation, or a browser-test runner.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02, “Dashboard e saúde operacional”, progressive
  dashboard expansion. P8-02 remains partial until each delivered card has an equivalent,
  reconciled drill-down; this slice is the next independently valuable available source.
- Canonical spec: `specs/p8-dashboard-and-operational-health.md`, repository revision
  2026-08-11 (no explicit version field), especially “Contratos e dados Proposed”, “UI,
  autorização e observabilidade”, “Falhas e testes”, and the P8-02 acceptance/DoD checklist.
- Supporting spec: `specs/p3-durable-jobs-leases-and-policy-engine.md`, repository revision
  2026-08-11 (no explicit version field), for durable job ownership, safe fields, outcome
  vocabulary, read-only metrics, and lease/retry invariants.
- Product/architecture references: `PRD.md` FR-DASH-003, FR-OPS-001, BR-OPS-001, AC-013,
  AC-024, and `ARCHITECTURE.md` sections 14, 20, 32, 36, 37, 40, and 41. Jobs remain owned by
  infrastructure; operations composes the dashboard read model and link.
- Completed prerequisites: issues 0001 and 0002 deliver durable job/lease and policy semantics;
  issue 0004 delivers P3-04 observability and Admin-only operational health; issue 0018 delivers
  the dashboard period/card contract. Issues 0026–0029 are adjacent dashboard slices, not
  prerequisites for this job-owned read.
- Data/compatibility: filter `Job.created_at` with the same local Brasília date-boundary helper
  and half-open `[from,to)` semantics used by dashboard aggregation. Preserve existing job
  engine, `/health/operational`, and dashboard aggregate response contracts. No schema change is
  expected; if an additive route is required, keep all existing callers unchanged.
- Security/observability: enforce the existing authenticated dashboard/job read policy on every
  request and preserve the repository's server-side role boundaries. Return only bounded safe
  identifiers, job type, allowed state/outcome, safe timestamps, attempt/status information, and
  allowlisted safe error codes needed by the view. Never expose payload JSON, lease ownership,
  policy configuration, secrets, fiscal content, or raw exceptions. Reads must not write jobs,
  leases, audits, metrics with unbounded labels, or collection state.
- Rollout: a job/database dependency failure must mark only processing cards and their
  drill-down unavailable or degraded; it must not become zero and must not change collection,
  document, company, certificate, backup, or Admin health cards. Unsupported, repeated, missing,
  reversed, overlong, or unknown filter values must be rejected rather than broadened to an
  unfiltered result.

## Implementation Plan

1. Define the bounded job drill-down contract at the existing jobs/operations boundary. Accept
   only the dashboard period plus one allowlisted card filter, reject repeated or unsupported
   parameters, and centralize the three mappings so the dashboard aggregate and list total cannot
   diverge. Use the existing period normalization and durable `Job` fields; do not add a failed
   state or infer outcomes from arbitrary error text.
2. Query the same `[from,to)` `created_at` interval used by `_job_counts`, apply the selected
   pending/failed/blocked predicate, compute the total from that queryset, and return a bounded
   stable page ordered by timestamp plus UUID tie-breaker. Serialize only safe fields and map
   missing durable state or source exceptions to the established safe unavailable/degraded
   contract.
3. Extend the three dashboard card links with the exact period and filter metadata, and update
   the dashboard/processing UI to consume that context from the URL or navigation state. The
   browser may render state and filters but must not authorize, broaden the query, or recalculate
   the total. Keep Admin-only operational-health internals separate from this safe card view.
4. Add unit and integration coverage for all three mappings, inclusive start/exclusive end
   boundaries, empty periods, mixed job types, repeated/invalid/unknown filters, deterministic
   pagination, anonymous/expired/unauthorized sessions, safe-field redaction, source failure,
   concurrent/repeated reads, and unchanged dashboard/health/collection behavior. Use synthetic
   jobs only and assert no database or job-state mutation.
5. Update the relevant contributor/operator documentation and refresh Graphify metadata for the
   new relationship. On completion, synchronize the P8-02 evidence in `IMPLEMENTATION_PLAN.md`,
   `specs/p8-dashboard-and-operational-health.md`, and `specs/README.md`, fill this issue's
   Resolution, and close the work in one focused commit.

## Tests

- **Unit:** period/filter parsing; canonical state/outcome predicates; Brasília `[from,to)`
  conversion; stable ordering/pagination; safe serialization; and source-error mapping.
- **Integration:** card-to-query reconciliation for pending, failed, and blocked jobs; boundary
  timestamps; empty and mixed-type periods; authenticated role access; invalid/repeated filters;
  expired sessions; source failure isolation; response redaction; default dashboard and health
  compatibility; and repeated reads with no job/lease/audit mutation.
- **Frontend:** period/filter drill-down navigation and loading, valid, zero, unavailable,
  invalid, degraded, and redacted-result branches under the existing TypeScript/ESLint/Vite
  contract. Do not add a browser-test runner.
- **Validation commands:** focused dashboard/jobs tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] `jobs.pending`, `jobs.failed`, and `jobs.blocked` expose drill-down metadata carrying the
  exact selected period and one canonical allowlisted filter.
- [x] The server accepts only bounded authenticated reads, uses the dashboard's Brasília
  `[from,to)` interval, and rejects missing, repeated, reversed, overlong, or unknown filters
  without falling back to an unfiltered result.
- [x] For synthetic data, each card value equals the filtered job total for the same period,
  including jobs exactly on both period boundaries and periods with no matches; pending,
  failed, and blocked mappings remain those defined by P3-04/P8-02.
- [x] The drill-down returns a stable bounded page and safe summaries only; it excludes payloads,
  lease owners, policy internals, secrets, fiscal content, object keys, raw exceptions, and
  unbounded correlation data.
- [x] Existing job engine transitions, retry/cooldown/block semantics, `/health/operational`,
  collection views, dashboard aggregate shape, and Admin-only technical health behavior remain
  backward compatible; the read introduces no migration, cache, job, lease, audit event, or
  state transition.
- [x] Anonymous, expired, and unauthorized requests are rejected server-side; permitted roles
  receive only the safe job scope allowed by the existing policy.
- [x] A job/database/source failure marks only the affected processing cards/drill-down
  unavailable or degraded, never as a successful zero, and leaves unrelated cards unchanged.
- [x] Repeated and concurrent identical reads are deterministic and side-effect free, with no
  duplicate rows or changing totals caused by the read path.
- [x] Synthetic unit, integration, and frontend-contract tests cover expected and negative
  behavior, boundaries, reconciliation, redaction, authorization, error isolation, pagination,
  and no-write behavior; all listed validation commands pass.
- [x] Documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the P8-02 spec/index, this
  issue's Resolution, and one focused implementation commit are synchronized before closure.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational-health expansions.
- Spec: `specs/p8-dashboard-and-operational-health.md` — period, cards, drill-down,
  degradation, authorization, and DoD.
- Supporting spec: `specs/p3-durable-jobs-leases-and-policy-engine.md` — durable job state,
  outcome vocabulary, safe fields, and observability invariants.
- Product: `PRD.md` — FR-DASH-003, FR-OPS-001, BR-OPS-001, AC-013, and AC-024.
- Architecture: `ARCHITECTURE.md` — job ownership, authorization, safe read boundaries,
  observability, and no-write operation.
- Related issues: `issues/0001_-_durable-job-queue-and-leases.md`,
  `issues/0002_-_policy-driven-job-retry-and-blocking.md`,
  `issues/0004_-_job-observability-and-initial-health.md`, and
  `issues/0018_-_initial-dashboard-and-operational-health.md`.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->

Implemented issue 0030 as the canonical read-only job drill-down for the three P8 processing
cards. `nfx.jobs` now owns the bounded query parser, Brasília `[from,to)` selection, shared
pending/failed/blocked predicates, deterministic 50-row cap, safe summary serializer, and
authenticated `GET /api/jobs/observability` route. The dashboard cards carry the exact period
and filter metadata, and the frontend renders loading, empty, invalid, unavailable, degraded,
bounded-result, and reconciled-total states without client-side authorization or counting.

Added unit and integration coverage for filter validation, boundaries, empty periods, all three
reconciliations, redaction, authorization and expiry, source failure isolation, stable bounded
pagination, concurrent/repeated reads, and no-write behavior. No migration or job/lease/audit
state transition was required. The intentional P8 mapping is preserved: `failed` includes
temporary, permanent, and partial outcomes, while `blocked` selects the durable blocked state.

Updated `specs/p8-dashboard-and-operational-health.md`, `specs/README.md`,
`IMPLEMENTATION_PLAN.md`, `docs/DEVELOPMENT.md`, and `docs/OPERATIONS.md`; refreshed Graphify
with `graphify update .`.

Validation completed:

- `make build` — passed.
- `make lint` — passed.
- `make test-unit` — 286 passed, 1 warning.
- `make test-integration` — 106 passed, 7 warnings, including migration/schema checks.
- `make smoke` — passed.
- Focused dashboard/job unit tests — 23 passed, 1 warning.
