---
id: 0018
title: "Implement capability-aware dashboard and operational health view"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0004, 0005, 0006, 0009, 0010]
blocked_by: []
affects:
  - backend/nfx/operations/
  - backend/nfx/companies/
  - backend/nfx/certificates/
  - backend/nfx/collection/
  - backend/nfx/jobs/
  - backend/nfx/infrastructure/
  - backend/nfx/urls.py
  - frontend/src/
  - tests/
  - docs/
---

## Description

The repository has the P3-04 operational health contract and the P2–P4 domain data needed
for a first dashboard, but no dashboard endpoint, aggregation boundary, or rendered dashboard
view. The current health response correctly marks future fiscal-source, document, rendering,
disk, and backup capabilities as unavailable; no implementation may turn those absent sources
into zeroes or a false healthy result. This issue delivers the independently useful first P8-02
slice while leaving later P5–P7 data to follow-up work.

## Objective and Expected Outcome

Provide an authenticated, read-only dashboard that reports current and immediately preceding
period aggregates for implemented company, certificate, collection, job, and operational-health
capabilities, with explicit freshness and degraded/unavailable states. Each available fiscal
card must lead to an equivalent supported list/filter view; unsupported P5–P7, backup, disk, and
rendering capabilities must remain visibly unknown/unavailable until their owning work exists.

## Implementation Plan

1. Map the P8-02 contract to the existing company, certificate, collection, job-observability,
   health, authorization, audit, and list boundaries. Define bounded card identifiers, interval
   semantics, status/freshness fields, and capability states without creating a second owner for
   domain data or operational health.
2. Add a read-only aggregation service and authenticated endpoint for the implemented slice.
   Validate bounded date intervals, compute an equal-duration immediately preceding period with
   exclusive boundaries, and return current/previous values, freshness, status, and supported
   drill-down filters. A source failure must degrade only its cards; missing future capabilities
   must be explicit rather than represented as zero.
3. Reuse server-side RBAC and existing domain query contracts for company, certificate,
   collection, job, and health data. Keep technical health, dependency details, and backup/disk
   information Admin-only; fiscal aggregates must follow the same permitted scope as existing
   authenticated views. Do not make the browser authoritative for permissions or state.
4. Add the dashboard UI and navigation entry using the existing React shell and compatible
   localized presentation. Render loading, real zero, stale, partial, degraded, unavailable, and
   unknown states distinctly, and make available cards navigate to the equivalent existing list
   context without adding unsupported filters or a second client-side aggregation model.
5. Test with deterministic synthetic data and faulted dependencies. Cover interval boundaries,
   zero versus unknown, independent card degradation, freshness, RBAC, drill-down reconciliation,
   redaction, and no-write behavior before running the repository validation commands.
6. Document the capability matrix and contributor/operator behavior, refresh Graphify with
   `graphify update .`, synchronize the P8-02 evidence in `IMPLEMENTATION_PLAN.md` and the
   owning spec/index, update this issue's Resolution, and close the work in one focused commit.

## In Scope

- The first P8-02 dashboard/read-model slice for existing P2–P4 company, certificate,
  collection, job, and operational-health data.
- A bounded read-only HTTP contract and React view with temporal comparison, freshness, explicit
  capability states, and supported drill-down links.
- Server-side authorization, safe aggregation, audit/observability as required by the spec,
  and unit/integration/browser-oriented coverage using synthetic/local data.
- Documentation of which P8-02 cards are implemented and which remain unavailable pending P5–P7,
  P9 backup, or later follow-up issues.

## Out of Scope

- NF-e/NFS-e transport or manifestation, advanced document search/download, PDF rendering, ZIP
  export, retention, deletion, backup implementation, alerts, BI, reports, notifications, or
  external telemetry infrastructure.
- Inventing document, fiscal-source, rendering, disk, or backup values before their owning
  capabilities exist; these remain explicit unknown/unavailable cards.
- New persistence, snapshots, caches, thresholds, quotas, business KPIs, or aggregation policy
  not required by the canonical P8-02 contract and existing accepted invariants.
- Changes to completed P3/P4 state machines, cursor/checkpoint ownership, frontend architecture
  refactoring owned by issue 0011, or unrelated cleanup.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02, “Dashboard e saúde operacional”; the plan and
  `specs/README.md` explicitly permit progressive dashboard delivery from P3-04 while declaring
  unavailable capabilities.
- Canonical spec: `specs/p8-dashboard-and-operational-health.md`, current repository revision
  (no explicit version field), especially “Contratos e dados Proposed”, “UI, autorização e
  observabilidade”, “Falhas e testes”, and the P8-02 acceptance/DoD checklist.
- Architectural authority: `ARCHITECTURE.md` sections 10.4, 18, 20, 32, 35, 36, 39, and 40;
  product requirements include FR-DASH-001…003, FR-OPS-001, BR-OPS-001, and BR-DASH-001.
- Completed prerequisites/related work: issues 0004 (P3-04 health), 0005 (collection state),
  0006 (document foundation), 0009 (ingestion pipeline), and 0010 (safe document status/list).
  Issue 0012 remains the owner of the pending P4-03 failure matrix; this slice must not create
  a competing state vocabulary or depend on undocumented P4 behavior.
- P5/P6 distribution, P7 consultation/download, P7 PDF, and P9 backup remain follow-up work.
  The dashboard must expose their absence as capability state and must not claim those slices
  complete.
- Data/compatibility: no schema or destructive migration is expected. Aggregates must be
  read-only, use explicit UTC/civil-date handling required by the contract, and reconcile with
  source lists without mutating jobs, cursors, documents, or artifacts.
- Security/observability: enforce authorization server-side on every request and drill-down;
  expose bounded counts, timestamps, statuses, and safe identifiers only. Do not log fiscal
  content, certificates, tokens, object keys, raw exceptions, or high-cardinality labels.
- Rollout: the endpoint and UI must degrade safely when PostgreSQL, MinIO, a source query, or
  backup evidence is unavailable; an unavailable card must not make unrelated cards fail.

## Tests

- **Unit:** interval normalization and previous-period boundaries; aggregate status/freshness;
  real zero versus unknown; capability mapping; redaction; and no-write behavior.
- **Integration:** endpoint authorization, company/certificate/collection/job/health aggregation,
  independent source failure, technical-health Admin-only access, and reconciliation with the
  existing list contracts.
- **Browser-oriented:** loading, valid values, zero, stale, partial, degraded, unavailable, and
  unknown card branches plus supported drill-down navigation using synthetic/local data.
- **Validation commands:** focused dashboard/operations tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A read-only authenticated dashboard endpoint and UI expose only the approved initial P8-02 cards and declare unsupported P5–P7, backup, disk, and rendering capabilities as unknown/unavailable.
- [x] Current and previous periods have equal duration, are consecutive, use documented inclusive/exclusive boundaries, and never overlap.
- [x] Real zero values are distinct from unknown, unavailable, stale, partial, and degraded results; a failure in one source does not erase or falsify unrelated cards.
- [x] Every available card returns bounded value, status, freshness, and an equivalent supported drill-down filter/link that reconciles with its source list.
- [x] Fiscal aggregates follow existing server-side authorization, and operational dependency/backup/disk details are inaccessible to non-Admin roles even through direct URL/API access.
- [x] The endpoint and UI perform no writes and do not alter jobs, leases, collections, documents, artifacts, cursors, checkpoints, or source state.
- [x] Faulted or unavailable dependencies fail closed for affected data, preserve safe error/status information, and never synthesize readiness, zero counts, or successful freshness.
- [x] Synthetic tests cover expected and negative interval, aggregation, RBAC, drill-down, freshness, degradation, redaction, and browser-state behavior without network or production credentials. Automated browser execution is N/A because this repository has no browser runner; the React state branches are compiled/linted and the HTTP contract is integration-tested.
- [x] No new dashboard-specific business owner, unsupported filter, alerting system, report/export feature, or unapproved persistence/cache policy is introduced.
- [x] Documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the owning P8 spec/index evidence, this issue's Resolution, and one focused implementation commit are synchronized before closure.
- [x] `make lint`, `make test-unit`, `make test-integration`, `make build`, `make smoke`, and focused dashboard checks pass without regressions.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational health.
- Spec: `specs/p8-dashboard-and-operational-health.md` — current repository revision.
- Architecture: `ARCHITECTURE.md` sections 10.4, 18, 20, 32, 35, 36, 39, and 40.
- Related issues: `issues/0004_-_job-observability-and-initial-health.md`,
  `issues/0005_-_manual-collection-control.md`,
  `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0009_-_durable-ingestion-pipeline-and-cursor.md`, and
  `issues/0010_-_minimum-document-status-and-list-contract.md`.
- Follow-up coverage: issues 0012–0017 and the P5–P9 specs remain separate outcomes.

---

## Resolution

## Resolution

- Implementation: added the calculate-on-read `nfx.operations.dashboard` service and
  `GET /api/dashboard`, with bounded `[from,to)` civil-date periods, equal-duration comparison,
  company/document/collection/job/certificate cards, explicit freshness/status signals, safe
  source isolation, and Admin-only reuse of operational health. Added the React `#dashboard`
  feature, period controls, card drill-down links, capability matrix, and explicit loading,
  zero, unavailable, degraded, partial, stale, and unknown presentation branches.
- Tests: added unit coverage for period arithmetic/validation and source isolation, plus isolated
  integration coverage for aggregation, real zero, drill-down, anonymous/invalid requests, and
  Admin versus Viewer health exposure. No migration, snapshot, cache, audit write, or fiscal state
  mutation was introduced.
- Documentation: synchronized `docs/OPERATIONS.md`, `docs/DEVELOPMENT.md`,
  `specs/p8-dashboard-and-operational-health.md`, `specs/README.md`, and `IMPLEMENTATION_PLAN.md`;
  refreshed Graphify with `graphify update .`.
- Key decisions: calculate-on-read preserves domain ownership and avoids unapproved persistence;
  unsupported P5–P7, PDF, disk, and backup capabilities remain unavailable; no monetary card is
  synthesized because current document persistence has no approved value source.
- Validation: focused dashboard tests (`10 passed`); `make lint`; `make test-unit` (`206 passed`);
  `make test-integration` (`59 passed`, 5 existing botocore deprecation warnings); `make build`;
  and `make smoke` all passed. Frontend TypeScript/ESLint and Vite build passed as part of lint/build.
