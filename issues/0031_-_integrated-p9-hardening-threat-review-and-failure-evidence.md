---
id: 0031
title: "Complete integrated P9 hardening and failure-recovery evidence"
type: feature
status: closed
priority: high
phase: P9
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0001, 0002, 0003, 0004, 0005, 0006, 0009, 0010, 0012, 0013, 0014, 0015, 0016, 0017, 0018, 0019, 0020, 0021, 0022, 0023, 0024, 0025, 0026, 0027, 0028, 0029, 0030]
blocked_by: [0001, 0002, 0003, 0004, 0005, 0006, 0009, 0010, 0012, 0013, 0014, 0015, 0016, 0017, 0018, 0019, 0020, 0021, 0022, 0023, 0024]
affects:
  - backend/nfx/identity/
  - backend/nfx/artifacts/
  - backend/nfx/adapters/
  - backend/nfx/collection/
  - backend/nfx/documents/
  - backend/nfx/exports/
  - backend/nfx/jobs/
  - backend/nfx/backup/
  - backend/nfx/retention/
  - backend/nfx/operations/
  - backend/nfx/infrastructure/
  - docker-compose.runtime.yml
  - deploy/nginx/
  - tests/
  - scripts/
  - docs/
---

## Description

Deliver the pending P9-04 hardening pass for the integrated MVP baseline through P9-03. The
repository has component-level security, durability, backup, runtime, and recovery tests, but
no implementation issue or completion evidence for the cross-boundary threat matrix, the full
architecture failure/recovery set, or the synthetic approximately-200-company exercise required
by the hardening spec. This is the next planned high-risk increment; P9-05 remains dependent on
its result.

The result is a traceable threat-and-failure review, automated and operational evidence, and
bounded corrective changes for critical findings. Existing safe-state invariants remain the
contract: unauthorized access fails closed, originals and durable progress are preserved, a
failed or partial operation is never reported as success, retries/replays are idempotent, and
diagnostics do not disclose restricted data.

## Objective and Expected Outcome

Establish whether the delivered MVP can be released to the internal pilot from a security,
durability, recovery, observability, and approximate-capacity perspective. Every threat and
trust-boundary result has a severity, redacted reproduction, owner/spec, control, test or
exercise evidence, decision, and residual risk. A critical finding is corrected in this slice or
explicitly blocks only the affected pilot/release scope; it is not silently accepted.

The synthetic exercise demonstrates the current runtime and persistence design with approximately
200 companies, multiple fiscal flows, jobs, users, and bounded concurrency. It measures the
environment rather than introducing an unapproved throughput SLA or artificial product limit.

## In Scope

- Review the integrated delivered surface for session and CSRF controls, RBAC and direct URLs,
  uploads/XML and parser limits, MIME/size enforcement, SSRF/redirect/DNS and destination
  allowlists, secrets, object integrity, jobs/leases/cursors, individual and ZIP downloads,
  PDF failures, retention/deletion recovery, backup validation, and runtime isolation.
- Build the required threat matrix for the architecture security boundaries and threats,
  including asset, trust boundary, control, test/evidence, severity, owner/spec, decision, and
  residual risk.
- Exercise the required fault cases: database, MinIO/object storage, fiscal source, disk space,
  web/worker/scheduler restart or death, expired/lost lease, unknown payload, conflict,
  interrupted renderer/ZIP, delayed backup, and failed isolated restore.
- Add or extend synthetic unit/integration/operational tests and runbooks where current evidence
  is missing, reusing the existing simulators, isolated object stores, backup validation target,
  durable job engine, ingestion recovery states, and bounded observability contracts.
- Apply only corrective implementation changes required by verified critical or release-blocking
  findings, preserving canonical ownership of jobs, ingestion, documents, artifacts, retention,
  audit, backup, and dashboard read models.
- Run the approximately-200-company synthetic capacity exercise with multiple users and flows,
  bounded concurrency, the P9-01 runtime limits, and evidence that no commercial or functional
  user/company limit is configured.

## Out of Scope

- P9-05 pilot or homologation execution, real fiscal endpoints, official transport adapters,
  production credentials, production data, or a penetration test against a live environment.
- Provisioning a physically separate backup destination or automating disaster recovery after
  host loss. The known same-host backup limitation and missing OPS-BKP-002/006 evidence must be
  recorded as residual risk and remain a P9-05 gate, not hidden or solved by this issue.
- Completing the unavailable P5–P7, rendering, or disk-backed dashboard capabilities that P8-02
  has explicitly left unavailable. Hardening may verify the delivered capability-aware behavior,
  but must not claim unavailable sources as exercised successfully.
- New features, public API surface, microservices, broker/HA, horizontal scaling, cache or
  snapshot policy, schema redesign, or unapproved performance targets.
- Replacing existing domain states, retry/lease/cursor semantics, retention policy, audit
  ownership, renderer/export contracts, or backup/restore safety boundaries.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P9-04 Hardening, the next high-risk pending increment
  after P9-03. P8-02 expansion remains parallel and partial; this issue covers the currently
  delivered baseline and must preserve explicit unavailable-capability states.
- Canonical spec: `specs/p9-hardening.md`, repository revision 2026-08-11 (the spec has no
  explicit version field). It defines the threat matrix, mandatory security tests, fault
  injection set, observability checks, synthetic capacity exercise, five DoD items, and
  Proposed measurement/threshold assumption.
- Supporting contracts: `specs/p9-runtime-and-https.md`, `specs/p9-backup-and-restore.md`,
  `specs/p9-controlled-deletion.md`, `specs/p3-durable-jobs-leases-and-policy-engine.md`,
  `specs/p4-fiscal-document-ingestion-and-integrity.md`, `specs/p7-zip-export.md`, and
  `specs/p8-dashboard-and-operational-health.md`.
- Product/architecture references: `PRD.md` SEC-001..009, OPS-001..006, NFR-003..008,
  AC-004, AC-006, AC-007, AC-009, AC-010, AC-012, AC-014, AC-016, AC-017, AC-024, and AC-025;
  `ARCHITECTURE.md` sections 8, 21, 22, 33, and 36–41.
- Completed prerequisites are the closed issues listed in `blocked_by`, including P9-01,
  P9-02, P9-03, and the delivered P8 dashboard slices. Issues 0025–0030 are related evidence
  slices, not a second hardening implementation.
- Known decision boundaries remain unchanged: same-host backup is not physical separation;
  auto-signed TLS is an accepted MVP limitation; CA, broker, HA, and detailed capacity
  thresholds are deferred or Proposed and must be reported as such.

## Implementation Plan

1. Inventory the delivered contracts and test evidence by component, then map every architecture
   section-33 threat and relevant trust boundary to an asset, control, severity, owner/spec,
   reproducible redacted scenario, evidence source, decision, and residual risk. Mark missing
   evidence separately from a failed control; do not infer production compliance from a unit test.
2. Add the missing negative and boundary tests around the existing contracts: brute force and
   user enumeration, CSRF/cookie/session theft and revocation, direct-URL/RBAC denial, MIME and
   size limits, XXE/XML-bomb and unsafe parser input, SSRF redirect/DNS/allowlist rejection,
   traversal/ZIP handling, secret redaction, object hash/size divergence, replay and cursor
   monotonicity, stale lease completion, retention confirmation, and runtime port exposure.
   Assert safe errors and absence of restricted content in logs, errors, audit context, backup
   manifests, and API/UI output.
3. Exercise the architecture-40 failures using existing fault-injection seams and isolated
   synthetic dependencies. For each scenario, prove the invariant that durable progress only
   advances after durable treatment, the original is retained on unknown/conflict/failure, a
   failed or partial operation is not successful, an expired lease can recover while an old
   owner cannot finalize, backup validation cannot write live volumes, and unrelated health
   surfaces remain isolated. Record restart, retry, idempotency, and concurrent-attempt results.
4. Run the synthetic capacity scenario against the configured P9-01 topology with approximately
   200 companies, multiple users and flows, durable jobs, document/artefact states, retries,
   dashboard reads, and bounded concurrency. Capture measured resource behavior, failures,
   recovery, and any threshold as Proposed; verify no artificial company/user cap is configured
   and do not turn a measurement into an SLA.
5. Correct verified critical or release-blocking defects within the existing component contracts.
   Keep changes minimal and additive where possible, preserve backward-compatible API and
   persisted-state behavior, avoid destructive migrations, and explicitly leave deferred or
   external gaps as scoped residual risks with an owner and release impact.
6. Publish the redacted hardening report, test/runbook evidence, and residual-risk decision in
   the repository's operator/developer documentation. Update the P9-04 DoD and evidence in
   `specs/p9-hardening.md`, synchronize its status and traceability in `IMPLEMENTATION_PLAN.md`
   and `specs/README.md`, refresh Graphify metadata for the changed relationships, fill this
   issue's Resolution, and close the work in one focused commit.

## Data, Compatibility, Security, and Rollout Notes

- Use synthetic fixtures only. Never use real CNPJ, XML, PDF, certificate, credential, token,
  endpoint response, or production log content in tests, reports, manifests, or committed
  evidence.
- No migration is expected. Preserve existing persisted states, ownership boundaries, API
  contracts, cursor/lease/retry idempotency, audit redaction, and the explicit P8 unavailable or
  degraded response semantics. Any unavoidable additive migration requires separate evidence of
  compatibility and must not delete or rewrite fiscal data.
- Security checks remain server-side and fail closed. Do not weaken allowlists, cookie/CSRF
  settings, runtime private networking, object verification, authorization, backup isolation, or
  safe error mapping to make an exercise pass.
- Metrics and logs must use bounded labels and safe identifiers only. Evidence must retain
  correlation and outcome information without payloads, secrets, lease ownership, raw provider
  errors, or unbounded user/company identifiers.
- Hardening completion is an evidence gate for the affected pilot/release, not a claim that the
  known physical-backup, trusted-CA, real-transport, or unavailable-dashboard gaps are closed.

## Tests

- **Unit:** security and parser boundaries, safe error/redaction helpers, state/recovery
  invariants, replay/idempotency/concurrency guards, lease ownership, retention confirmation,
  ZIP/path handling, and configuration/allowlist checks.
- **Integration:** PostgreSQL/MinIO fault injection, ingestion/cursor replay, job lease loss and
  restart, unknown/conflicting payloads, renderer/ZIP interruption, deletion recovery, backup
  manifest/hash/decrypt validation, RBAC/direct URL/session revocation, and runtime port/HTTPS
  isolation.
- **Operational/capacity:** synthetic approximately-200-company exercise with bounded
  concurrency, web/worker/scheduler restart, dependency outages, disk/backup/restore failure,
  measured resource evidence, and a redacted recovery report/runbook.
- **Validation commands:** focused hardening/security/operations tests, `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] The hardening matrix covers every threat named by `ARCHITECTURE.md` section 33 and every
  relevant trust boundary, with asset, control, test/evidence, severity, owner/spec, decision,
  and residual-risk fields.
- [x] The architecture-40 failure set has exercised evidence for DB/MinIO/source outage, disk
  full, web/worker/scheduler death or restart, lost lease, unknown payload, conflict,
  interrupted renderer/ZIP, delayed backup, and failed isolated restore.
- [x] Fault and concurrency tests prove no unsafe cursor/progress advance, no duplicate logical
  result, no stale-lease completion, no false success for partial work, preserved originals and
  recovery state, and safe retry/restart behavior.
- [x] Security tests reject brute force/enumeration, CSRF/session theft or revoked sessions,
  unauthorized direct URLs, unsafe MIME/size/XML input, SSRF redirects/DNS/unknown destinations,
  traversal/unsafe ZIP entries, and runtime port exposure without weakening the existing
  fail-closed controls.
- [x] Synthetic canaries and restricted fiscal content are absent from logs, errors, audit
  payloads, API/UI responses, backup manifests, and committed evidence; observability labels
  remain bounded and non-sensitive.
- [x] The synthetic exercise covers approximately 200 companies, multiple users and flows, and
  bounded concurrent jobs under the P9-01 runtime limits, with measured resource/recovery
  results and no artificial company or user limit.
- [x] Each critical finding is corrected and retested, or is explicitly recorded as blocking
  only the affected pilot/release scope with an owner, severity, evidence, and residual-risk
  decision; no known same-host-backup or other external/deferred gap is misreported as closed.
- [x] Existing API/persisted-state contracts, RBAC, job/lease/retry/cursor semantics, audit
  redaction, object integrity, backup validation isolation, dashboard degradation, and
  capability-aware P8 behavior remain backward compatible.
- [x] Tests use only synthetic data and cover expected, negative, error, retry, idempotency,
  concurrency, data-integrity, security/configuration, observability, and recovery behavior;
  focused tests plus all listed validation commands pass.
- [x] The redacted hardening report, runbook/evidence, P9-04 spec/index, `IMPLEMENTATION_PLAN.md`,
  Graphify metadata, this issue's Resolution, and one focused implementation commit are
  synchronized before closure.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P9-04 Hardening.
- Spec: `specs/p9-hardening.md` — threat review, mandatory tests, fault injection, capacity,
  acceptance criteria, and DoD.
- Supporting specs: `specs/p9-runtime-and-https.md`, `specs/p9-backup-and-restore.md`,
  `specs/p9-controlled-deletion.md`, `specs/p3-durable-jobs-leases-and-policy-engine.md`,
  `specs/p4-fiscal-document-ingestion-and-integrity.md`, `specs/p8-zip-export.md`, and
  `specs/p8-dashboard-and-operational-health.md`.
- Product: `PRD.md` — SEC-001..009, OPS-001..006, NFR-003..008, and the listed ACs.
- Architecture: `ARCHITECTURE.md` — security boundaries, observability, failure matrix,
  deployment limits, and acceptance invariants in sections 33, 36–41, and 46.
- Related issues: completed prerequisite issues 0001–0024 as applicable and P8 evidence slices
  0025–0030; no existing issue covers the P9-04 outcome.

---

## Resolution

Implemented and validated the P9-04 integrated hardening increment.

### Implementation

- Added `docs/P9_HARDENING.md` with the redacted threat/trust-boundary matrix,
  Architecture §40 fault evidence, canary/observability checks, measured-capacity
  contract, residual-risk decisions, and operator runbook.
- Added `tests/integration/test_p9_hardening.py`, which persists 200 synthetic
  companies, three users, 400 flows, and 400 jobs, drains them with four bounded
  workers through the durable `JobEngine`, and asserts one logical result per
  target. It also verifies object-store outage and disk-full backup behavior
  preserve safe recovery states.
- Added `scripts/p9_hardening.sh` for an ephemeral PostgreSQL/MinIO evidence run,
  including web/worker/scheduler health and restart checks. It uses only the test
  Compose project and removes only its own temporary volumes.
- No production API, migration, credential, transport, or persisted-state
  contract was changed. No new critical implementation defect was found.

### Tests, migrations, and docs

- Focused unit baseline: `make test-unit` — 286 passed, 1 pre-existing
  `botocore` deprecation warning.
- Focused P9 test: `bash scripts/p9_hardening.sh` — exit 0; 2 tests passed,
  `P9_CAPACITY_EVIDENCE companies=200 users=3 flows=400 jobs=400 workers=4
  elapsed_ms=1271 company_limit=none user_limit=none
  threshold_classification=proposed`; ephemeral service restart checks passed.
- Full validation: `make lint` passed (ruff, mypy 111 files, TypeScript/ESLint),
  `make test-integration` passed (108 tests, 7 existing botocore deprecation
  warnings), `make build` passed, and `make smoke` passed. Docker reported only
  the local missing-Buildx warning.
- Full validation commands are listed in `docs/P9_HARDENING.md`; migrations are
  unchanged and the ephemeral script applies them only to its disposable test
  database.
- Updated `specs/p9-hardening.md`, `specs/README.md`, and `IMPLEMENTATION_PLAN.md`.

### Key decisions and residual risk

- Capacity thresholds remain Proposed measurements, not an SLA or artificial
  company/user limit.
- Same-host backup, host-loss recovery, auto-signed TLS, real fiscal transports,
  and unavailable P8 source capabilities remain explicit residual/deferred scope;
  they are not misreported as closed and continue to gate the affected P9-05 or
  production scope.
