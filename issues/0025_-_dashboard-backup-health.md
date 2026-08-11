---
id: 0025
title: "Expose verified backup health in the Administrator dashboard"
type: feature
status: closed
priority: medium
phase: P8
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0004, 0017, 0018]
blocked_by: []
affects:
  - backend/nfx/backup/
  - backend/nfx/operations/
  - frontend/src/features/dashboard/
  - tests/
  - docs/
---

## Description

Complete the next independently valuable P8-02 dashboard slice by exposing the already
implemented P9-02 backup status through the existing Administrator operational-health view. The
dashboard currently hard-codes the backup capability as unavailable with
`p9_backup_slice_pending`, even though `BackupService.status()` and the Administrator-only
`/api/backups/status` contract now provide verified latest-backup, age, retention, failure, and
latest-restore information.

## Objective and Expected Outcome

An Administrator can see whether backup coverage is successful, failed, or unavailable, the
latest successful backup age, bounded retention counts, and the latest isolated-restore outcome
from the dashboard. The response preserves explicit unknown/unavailable states and never claims
freshness or success when the backup owner has no successful set. Operators and Visualizers retain
the existing fiscal dashboard but receive no backup details or existence leak. The dashboard
remains read-only and reuses P9-02's service ownership, safe fields, and same-host limitation.

The verified gap is the P8-02 partial-delivery note in `IMPLEMENTATION_PLAN.md` and the open
backup capability in `specs/p8-dashboard-and-operational-health.md`; P9-02 is complete in issue
0017 and its canonical spec. This is a dashboard integration gap, not missing backup capture or
restore behavior.

## In Scope

- Replace the dashboard's P9-02-pending backup capability with an Administrator-only summary
  sourced through the existing `BackupService.status()`/`backup_status()` boundary.
- Map the P9-02 `success`, `failure`, and `unavailable` outcomes, latest-success age, bounded
  daily/weekly/monthly retention counts, latest backup state, and latest restore state into the
  existing operational-health response without exposing paths, manifest contents, or raw IDs.
- Preserve a safe `admin_only` contract for non-Administrators and keep fiscal cards available
  when backup status is missing or fails.
- Add the existing dashboard frontend state/labels for success, failure, unavailable, unknown
  age, latest restore failure, loading, and safe error behavior.
- Add focused unit/integration/contract tests and update the dashboard/operations documentation
  to describe the ownership and same-host limitation.

## Implementation Plan

1. Map `specs/p8-dashboard-and-operational-health.md` P8-02 to `build_dashboard()` and its
   Administrator-only operational-health branch, then map the fields to the P9-02
   `BackupService.status()` contract. Use the backup service as the sole owner; do not query
   backup tables directly from the dashboard or create a second freshness/retention rule.
2. Extend the safe dashboard response with an allowlisted backup summary. Preserve the P9-02
   state and safe error vocabulary, carry `latest_success_age_seconds` and retention counts as
   bounded values, and represent absent successful sets or unavailable service as unknown or
   unavailable. Do not expose `backup_path`, manifest contents/hashes, object keys, raw provider
   exceptions, or restore target details. Do not introduce a new stale threshold or invent an
   SLA; the age must remain an explicit measurement for operators to interpret.
3. Enforce the role boundary before loading backup data: Administrators may receive the summary,
   while Operators, Visualizers, anonymous callers, and invalid sessions receive the existing
   dashboard authorization behavior with no backup status, age, retention, restore, or error
   details. A backup-service/database failure must degrade only the backup portion and preserve
   unrelated fiscal cards.
4. Update the existing dashboard UI and TypeScript contract to render the bounded summary in the
   operational-health area with explicit success, failure, unavailable, unknown-age, and latest
   restore states. Keep the interaction read-only; no dashboard action may trigger capture,
   cleanup, restore, or a retry with side effects.
5. Add tests before implementation for Administrator success/failure/unavailable responses,
   missing successful backup, restore failure, bounded field selection, non-Administrator denial
   and non-leakage, source failure isolation, repeated reads with no writes, and preservation of
   the existing period/card/drill-down contract. Use synthetic backup records only.
6. On completion, update the dashboard and operations documentation, run `graphify update .`,
   synchronize only the P8-02 evidence in `IMPLEMENTATION_PLAN.md`,
   `specs/p8-dashboard-and-operational-health.md`, and `specs/README.md`, fill this issue's
   Resolution, and close the work in one focused commit. Do not claim P9-04 hardening, P9-05
   pilot/homologation, physically separate backup, or any new backup automation complete.

## Out of Scope

- Backup capture, verification, retention cleanup, isolated restore, restore automation, or
  changes to the P9-02 schema, commands, state machine, or same-host limitation.
- Physically separate backup destinations, loss-of-host recovery, ransomware controls, new
  backup freshness thresholds, alerting, notifications, or SLA policy.
- Dashboard caching/materialization, new migrations, new operational owners, new fiscal cards,
  P5/P6 transport status, PDF rendering, controlled deletion, hardening, or pilot work.
- Direct object-store/database access from the frontend, public backup URLs, backup paths,
  manifest data, credentials, fiscal content, raw exceptions, or unrelated UI refactoring.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard expansions, priority 3 in the current
  pending-work sequence; this issue is the backup-health increment only.
- Canonical dashboard spec: `specs/p8-dashboard-and-operational-health.md` — P8-02, repository
  revision 2026-08-11 (no explicit version field), especially the Admin-only health/backup,
  explicit freshness, source isolation, and read-only DoD requirements.
- Supporting backup contract: `specs/p9-backup-and-restore.md` — P9-02, repository revision
  2026-08-11 (no explicit version field); issue 0017 completed the status endpoint and safe
  `BackupService.status()` fields.
- Prerequisites: issue 0004 owns the operational-health boundary, issue 0017 owns backup and
  restore status, and issue 0018 owns the initial P8-02 dashboard slice; all are closed.
- Data/migration: no migration or persistent dashboard state is required. Reads must use the
  existing backup service and preserve the P9-02 safe result contract.
- Compatibility/security: preserve `/api/backups/status` and `/api/dashboard` authorization,
  existing dashboard periods/cards/drill-downs, and the no-existence-leak behavior for
  non-Administrators. Keep all response fields bounded and redacted.
- Observability/rollout: expose source status and measured age without adding metrics labels or
  thresholds. If the backup owner is unavailable, show an explicit unavailable/degraded state;
  never turn the condition into zero, fresh, or successful backup coverage.

## Tests

- **Unit:** safe P9-02 status mapping, absent-success and failure states, bounded retention/age
  handling, role gating, redaction, and source-failure isolation.
- **Integration:** Administrator versus Operator/Visualizer/anonymous dashboard access, success
  and failed backup fixtures, latest restore failure, no backup set, no backup-detail leakage,
  repeated read/no-write behavior, and regression coverage for periods, fiscal cards, and health.
- **Frontend:** dashboard loading, available, failure, unavailable, unknown-age, restore-failure,
  and safe-error branches using the existing TypeScript/ESLint/build contract; do not add a
  browser-test runner.
- **Validation commands:** focused dashboard/backup tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] Administrator dashboard responses source backup information through the existing P9-02
  service contract and distinguish successful, failed, and unavailable backup outcomes without
  adding a dashboard-owned query, cache, migration, or persistence path.
- [x] The Administrator summary includes only bounded latest-backup state, measured latest
  successful age, daily/weekly/monthly completed counts, and latest-restore state/error code;
  paths, manifest data, object keys, target details, raw IDs, and provider exceptions are absent.
- [x] No successful backup produces explicit unavailable/unknown age state rather than zero,
  fresh, or successful coverage; when the latest backup is failed, partial, or running while an
  older success exists, its latest state remains visible and is not presented as an unqualified
  current success.
- [x] Backup-service or dependency failure degrades only the backup summary and preserves the
  existing fiscal cards, period comparison, drill-down filters, and Admin health response.
- [x] Operators, Visualizers, unauthenticated callers, and invalid sessions cannot obtain backup
  status, age, retention, restore, or failure details through the dashboard; existing server-side
  authorization and no-existence-leak behavior remain intact.
- [x] The UI renders loading, success, failure, unavailable, unknown-age, latest-restore-failure,
  and safe-error states without offering capture, cleanup, restore, or side-effecting retry
  controls.
- [x] Repeated or concurrent dashboard reads are read-only and do not create backup records,
  restore operations, jobs, audit events, migrations, or changes to fiscal/application state.
- [x] Synthetic unit, integration, and frontend-contract tests cover expected and negative
  behavior, redaction, role boundaries, source failure isolation, and no-write behavior; focused
  checks plus `make lint`, `make test-unit`, `make test-integration`, `make build`, and
  `make smoke` pass.
- [x] Dashboard/operations documentation, `IMPLEMENTATION_PLAN.md`, the P8-02 spec/index,
  Graphify metadata, and this issue's Resolution are synchronized, and the issue is closed in
  one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard expansions.
- Spec: `specs/p8-dashboard-and-operational-health.md` — P8-02 dashboard, health/backup
  authorization, freshness, degradation, and read-only contract.
- Supporting spec: `specs/p9-backup-and-restore.md` — P9-02 safe backup status, retention, restore
  validation, and same-host limitation.
- Related issues: `issues/0004_-_job-observability-and-initial-health.md`,
  `issues/0017_-_verifiable-backup-and-isolated-restore.md`, and
  `issues/0018_-_initial-dashboard-and-operational-health.md`.
- Current boundaries: `backend/nfx/backup/`, `backend/nfx/operations/`,
  `frontend/src/features/dashboard/`, and the existing dashboard/backup test suites.

---

## Resolution

Implemented the P8-02 backup-health increment at the dashboard boundary. `build_dashboard()` now
reads the existing P9-02 `backup_status()` contract only for Administrators, maps its safe outcome,
latest-set state/error, measured successful age, capped 7/4/12 retention counts, and latest
validation state/error into `operational_health.backup`, and degrades that summary to
`unavailable` without disturbing fiscal cards when the source fails. Operators, Visualizers, and
unauthenticated/invalid-session callers receive no backup details or source access. The React
dashboard renders loading, coverage, latest-set, unknown-age, retention, restore-failure, and
allowlisted safe-error states without side-effecting controls.

No migration or backup-service change was required. Existing period, card, drill-down, RBAC,
same-host limitation, and read-only contracts remain unchanged; physically separate backup,
hardening, and pilot evidence remain out of scope.

Validation completed:

- `make lint` — Ruff, mypy, TypeScript, and ESLint passed.
- `make build` — Django checks and Vite production build passed.
- `make test-unit` — 240 passed.
- `make test-integration` — 77 passed in isolated PostgreSQL/MinIO containers.
- `make smoke` — isolated web/worker/scheduler topology and health checks passed.

Documentation synchronized in `docs/OPERATIONS.md`, `IMPLEMENTATION_PLAN.md`,
`specs/p8-dashboard-and-operational-health.md`, `specs/README.md`, this issue, and Graphify
outputs. The focused commit is titled `feat(dashboard): expose verified backup health (#0025)`.
