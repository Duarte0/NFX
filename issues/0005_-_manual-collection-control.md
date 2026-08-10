---
id: 0005
title: "Implement manual collection control and execution tracking"
type: feature
status: closed
priority: high
phase: P3
created_at: 2026-08-07
updated_at: 2026-08-09
closed_at: 2026-08-09
related_issues: [0001, 0002, 0003]
blocked_by: []
affects:
  - backend/nfx/collection/
  - backend/nfx/companies/
  - backend/nfx/certificates/
  - backend/nfx/jobs/
  - backend/nfx/urls.py
  - frontend/src/
  - backend/nfx/migrations/
  - tests/
  - docs/
---

## Description

Deliver P3-05: an authorized, durable collection-command and execution-tracking flow for complete, NF-e-only, NFS-e-only, and permitted retry requests. Admins and Operators must be able to request and monitor collection by company/flow; duplicate concurrent requests must return the existing active execution, while cooldowns, blocks, disabled flows, inactive companies, and invalid certificates remain non-bypassable.

Verified gap: `nfx.collection` currently contains only the `InitialCollectionRequest` handoff created after a valid certificate is activated. There is no collection execution or per-flow operational state, no command that consumes that handoff and creates collection jobs, no collection HTTP contract, and no collection controls/status in the existing company UI. `Action.CONTROL_COLLECTIONS`, company flow state, certificate eligibility, the durable job/policy engine, synthetic adapters, and append-only audit support already exist, but are not connected into this outcome.

## Objective and Expected Outcome

Provide one server-authoritative collection boundary that routes manual, retry, and automatic-initial requests through the same validation, idempotency, job-enqueue, audit, and reconciliation rules. The UI presents safe per-flow state and allowed actions without becoming the authority for authorization or state transitions. This is the P3-05 implementation slice only; fiscal collection remains synthetic and document ingestion remains owned by P4.

## In Scope

- Durable collection execution and per-company/per-family flow state required to request, recover, and display collection work.
- Manual, retry, and certificate-triggered automatic-initial commands; HTTP endpoints and the company collection-status/control UI needed to use them.
- Server-side RBAC, audit evidence, concurrency/idempotency, cooldown/block checks, and synthetic job-handler integration.
- Additive migration, focused documentation, and tests for the new contracts.

## Implementation Plan

1. Define the collection-owned persisted contracts described by `p3-manual-collection-control.md`: an execution records company, requested scope, origin, optional requester, lifecycle state, linked job(s), captured effective policy, safe summary/error, correlation, and timing; per-family state records last attempt/success, next run, cooldown, blocked condition, progress, and active execution. Use PostgreSQL constraints, row locking, and indexes to prevent more than one active execution for a company/family while retaining history. Keep IDs/references and safe codes only—never certificate material, XML, raw adapter responses, credentials, or unredacted errors.
2. Implement a transactional internal `request_collection` contract shared by manual, retry, and automatic-initial paths. It must authorize the requested actor/origin, expand a complete request into independently trackable NF-e/NFS-e work, validate active company, enabled flow, current valid certificate, effective policy, cooldown, and blocking before enqueue, and atomically create/reuse executions plus idempotent jobs. A concurrent or duplicate request returns the active execution as a business-conflict result rather than creating another job. If persistence fails between execution creation and enqueue, roll back or leave a deterministic reconciliation path; never retain an active execution without recoverable work.
3. Consume `InitialCollectionRequest` through this same service after certificate activation, preserving its idempotency and system origin. Retry must reference a prior failed/eligible execution and create new work only when the captured/current policy permits it; it must not resurrect a blocked job, skip cooldown, or alter immutable job-policy references. Update execution/flow state from the synthetic handler/job outcome boundary so success, valid empty, partial, retry, cooldown, blocked, and safe failure remain distinct without claiming that no fiscal documents exist before P4/P6 establish a valid result.
4. Add authenticated collection command and read contracts alongside the established company HTTP patterns. Revalidate `Action.CONTROL_COLLECTIONS` in every mutating handler: Admin and Operator may request/retry, Viewer may only receive the permitted safe operational view. Return stable safe execution/flow identifiers and states, with conflict/validation errors that disclose neither certificate state details beyond the allowed corrective condition nor any secret. Preserve CSRF/session behavior and do not introduce a public API.
5. Extend the company-oriented frontend with safe NF-e/NFS-e collection status, last attempt/success, next execution, cooldown/block condition, progress, safe error/corrective state, and controls whose visibility reflects role/state. The browser must treat the server response as authoritative and distinguish concluded, valid-empty, partial, retrying, blocked, failed, and running states; it must not display “Nenhum documento encontrado” as a collection result before a valid fiscal query. Emit only bounded, safe collection-command instrumentation compatible with the P3-04 operational work; do not implement health aggregation or a dashboard here.
6. Append audit events for request, duplicate/conflict refusal, retry, automatic initial request, completion/outcome, and relevant rejection. Record actor/role, request IP, company/flow, origin, reason where required, correlation, and redacted safe context. Audit persistence must participate in the authoritative operation so a successful critical command is not reported without its evidence.
7. During the build pass, synchronize P3-05 evidence/status in `IMPLEMENTATION_PLAN.md`, `specs/p3-manual-collection-control.md`, and `specs/README.md`; document the collection command/state contract; refresh Graphify with `graphify update .`; update this issue’s Resolution; and commit the completed work as one focused commit.

## Out of Scope

- Official SEFAZ/ADN transports, endpoint/envelope/layout decisions, real credentials, or any fiscal network call.
- P4 document/event persistence, object storage, cursor/NSU checkpoints, parsing, quarantine, conflict persistence, or document-list APIs.
- P3-04 job/process health, global operational metrics, dashboards, alerts, or external telemetry infrastructure (covered by issue 0004).
- P5/P6 distribution/manifestation flows, P7 consultation/downloads, and changes to P3-01 lease semantics or P3-02 policy/backoff/cooldown/block semantics.
- Changing company/certificate lifecycle rules except to route the existing valid-certificate initial handoff through the collection command contract.

## Tests

- **Unit:** collection state/command tests for scope expansion, each role, inactive company, paused flow, invalid/expired certificate, duplicate and concurrent requests, cooldown, blocked work, retry eligibility, automatic-initial idempotency, outcome-to-state mapping, redaction, and audit failure handling.
- **Integration:** PostgreSQL migration installation/upgrade; transactional execution/job creation and reconciliation; concurrent requests from independent connections; restart/reclaim with a synthetic handler; and job-policy compatibility without duplicate logical collection work.
- **HTTP/UI:** protected endpoint tests for CSRF/session/RBAC and safe payloads, plus frontend/browser coverage of role/state-gated actions and distinct operational states.
- **Validation:** run focused collection, company, certificate, job, audit, HTTP, frontend, and migration tests, then `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] An additive migration persists collection executions and independent NF-e/NFS-e flow state with safe history, constraints/indexes, and locking that prevent concurrent active execution for the same company/family without deleting prior evidence.
- [x] One server-authoritative command handles complete, family-specific, retry, and automatic-initial requests; complete scope creates independently trackable per-family work and all paths use the same validation/idempotency rules.
- [x] Admin and Operator can request and retry collection; Viewer cannot mutate collection state. HTTP/UI checks do not replace server-side RBAC, CSRF/session protections, or authorization revalidation.
- [x] A duplicate or concurrent request returns the existing active execution and creates no duplicate job or logical collection effect; failure between execution persistence and enqueue is rolled back or deterministically reconciled after restart.
- [x] Server validation rejects or safely reports inactive companies, paused flows, invalid/unavailable certificates, cooldowns, and blocked work; retry runs only when policy permits and cannot bypass cooldown, unblock terminal work, or mutate an existing job’s effective policy.
- [x] The valid-certificate initial handoff is consumed idempotently with a system origin, and replacement/repeated processing does not create duplicate active collection work.
- [x] Per-flow status safely distinguishes running, concluded, valid-empty, partial, retrying, cooldown, blocked, and failed outcomes; the UI shows only permitted state/actions and never asserts “Nenhum documento encontrado” before a valid fiscal result.
- [x] Collection commands, rejections/conflicts, retry, automatic initial processing, and outcomes produce append-only, redacted audit evidence with applicable actor, role, IP, company/flow, origin, correlation, result, and reason, and no certificate/PFX, XML, token, credential, or raw adapter/error content.
- [x] Bounded safe collection-command instrumentation is compatible with P3-04 without adding health/dashboard scope or unbounded identifiers, payloads, or error content as labels.
- [x] Unit, PostgreSQL integration, HTTP, and frontend/browser tests cover positive, negative, redaction, concurrency, restart/reconciliation, idempotency, policy/cooldown/block, RBAC, and synthetic no-network paths.
- [x] `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke` complete successfully with no regression to company/certificate lifecycle, audit integrity, job lease/policy behavior, configuration isolation, or existing health endpoints.
- [x] Completion synchronizes P3-05 in `IMPLEMENTATION_PLAN.md`, the canonical manual-collection spec, and `specs/README.md`; updates the collection documentation and this issue’s Resolution; refreshes Graphify; and is committed as one focused commit.

## References

- Implementation plan: `IMPLEMENTATION_PLAN.md` — P3-05, “Controle manual”.
- Canonical spec: `specs/p3-manual-collection-control.md` — P3-05, current version.
- Product requirements: `PRD.md` — FR-COLL-001, BR-COLL-001, BR-COLL-003 through BR-COLL-005, BR-COLL-008/009, AUD-005, AUD-008, AC-004, AC-006, and AC-017.
- Architecture: `ARCHITECTURE.md` — sections 10.1, 14, 19–22, 26, 27, 32, 36, and 37; ADR-005.
- Existing baseline: `backend/nfx/collection/models.py`, `backend/nfx/companies/`, `backend/nfx/certificates/services.py`, `backend/nfx/jobs/`, `backend/nfx/identity/policy.py`, `backend/nfx/audit/`, `backend/nfx/urls.py`, and `frontend/src/main.tsx`.
- Dependencies: P1-03 authentication/RBAC, P1-05 audit foundation, P3-01 durable jobs, and P3-02 policy handling are implemented (issues 0001–0003). P3-04 observability is separately covered by open issue 0004 and is not a blocker for this slice.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- Include files modified, tests added, edge cases handled, tracking updates, Graphify update, and focused commit. -->

Implemented P3-05 with additive migration `0012_companyflow_blocked_reason_and_more`. Added
`CollectionExecution`, per-family operational state on `CompanyFlow`, active-execution constraints,
safe summaries/errors, policy references, and audit-compatible correlation fields. The transactional
`request_collection` service handles complete, NF-e, NFS-e, retry, duplicate/concurrent requests,
RBAC, active company/flow/certificate checks, cooldown/blocking, policy selection, and rollback if
job enqueue fails. Certificate-created `InitialCollectionRequest` rows are consumed idempotently by
the scheduler through the same service with system origin.

Added protected collection list/status/request/retry endpoints and extended the company UI with
per-family state, safe corrective status, complete/family request controls, retry controls, and
Viewer read-only behavior. The synthetic worker handler reconciles valid-empty, concluded, partial,
retrying, cooldown, and blocked outcomes without fiscal transport or document content; all request,
conflict, rejection, retry, and automatic-origin operations use redacted append-only audit events.

Validation performed:

- `make lint`, `make build`, and `make smoke` passed; frontend TypeScript/ESLint, Django check,
  targeted mypy, and migration consistency checks also passed.
- Isolated Docker `scripts/test-integration.sh` initially found three migration-list assertions that
  omitted the new migration; after updating those expected lists, the integration suite passed with
  29 tests.
- The isolated Docker unit suite ran 131 tests: 130 passed, including all five new collection
  tests, and one pre-existing `test_environment_template_uses_external_secret_placeholders_once`
  failure remains because the test image does not contain `.env.example`; this is outside P3-05 and
  is tracked by the existing reproducible-build work.
- `graphify update .` completed after the final implementation and migration formatting.

No production credentials, fiscal endpoints, document/XML content, or non-ephemeral data were used.
