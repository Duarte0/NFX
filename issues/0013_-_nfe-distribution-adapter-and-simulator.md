---
id: 0013
title: "Implement simulator-backed NF-e distribution adapter for independent flows"
type: feature
status: closed
priority: high
phase: P5
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0003, 0009, 0012]
blocked_by: []
affects:
  - backend/nfx/adapters/
  - backend/nfx/collection/
  - backend/nfx/jobs/
  - backend/nfx/audit/
  - tests/
  - docs/
---

## Description

Deliver the first independently valuable P5 capability: a semantic NF-e distribution
adapter contract and deterministic simulator for received/entrada and emitted/saída flows.
The current baseline has generic fiscal scenarios and the P4 durable ingestion service, but
no NF-e-specific distribution boundary that carries flow, source, cursor, consumption and
safe outcome semantics into that pipeline. The real Portal Nacional/SEFAZ transport remains
intentionally open and must not be invented in this slice.

## Objective and Expected Outcome

Allow a worker-facing NF-e adapter to request a bounded distribution page for either flow,
validate and interpret its safe envelope, and hand the resulting original units and
continuation position to the existing P4 ingestion owner. Received and emitted collection
state must remain independent; repeated requests and restarts must be deterministic and
safe; and the simulator must exercise empty, paginated, retryable, unavailable, malformed,
unknown, and blocked outcomes without network access or production credentials.

## Implementation Plan

1. Trace the P5 distribution requirements to the existing adapter protocol, `NFeSimulator`,
   `FiscalResponse`, `IngestionContext`, `FiscalIngestionService`, job handler, certificate
   validation boundary, and audit/observability services. Define the smallest typed semantic
   request/response contract for company, NF-e flow (`received`/entrada or `issued`/saída),
   source, cursor, bounded page units, continuation, consumption/cooldown hint, and safe
   outcome. Keep transport-specific endpoint, envelope, NSU, limit, and sequencing values
   behind the adapter policy rather than constants in collection or document code.
2. Extend the adapter boundary and deterministic simulator to produce both flows with
   independent request histories and continuation positions. Validate flow/family and
   cursor invariants at the boundary, reject mixed NF-e/ADN positions and malformed or
   sensitive fixture context, and return explicit typed outcomes for valid empty,
   unavailable, retryable, blocked, malformed/unknown, and successful pages. Every fixture
   remains synthetic, bounded, replayable, and network-free.
3. Connect the semantic result to the existing P4 ingestion service and job execution
   boundary. Preserve original-before-classification ordering, delegate unit identity,
   quarantine, conflict, checkpoint, and cursor advancement to P4, and pass only the
   adapter’s safe continuation/outcome metadata. Do not add a second cursor, received-unit,
   retry-policy, or state machine in the adapter. A failed, partial, unknown, or unresolved
   page must not advance progress; a valid empty page may advance only under the P4 rules.
4. Add bounded audit, safe result, and metric mappings for distribution start, completion,
   retry, unavailable, blocked, and malformed outcomes. Redact certificates, XML/raw
   payloads, object keys, tokens, credentials, and unredacted external errors; preserve only
   permitted identifiers, flow, reason codes, cursor prefixes, and digest prefixes.
5. Write focused unit and integration tests before implementation for the two independent
   flows, pagination/restart/replay, valid empty versus unavailable/no coverage, retryable
   versus blocked outcomes, malformed/unknown envelopes, wrong-family and wrong-flow
   positions, ingestion handoff, no false cursor progress, safe logging/audit, destination
   guards, and concurrent duplicate requests. Run the repository’s configured lint, unit,
   integration, build, and smoke validation.
6. Document the simulator-backed NF-e distribution contract and flow ownership, refresh
   Graphify metadata with `graphify update .`, synchronize this issue’s Resolution and the
   P5 evidence in `IMPLEMENTATION_PLAN.md` plus the owning spec/index according to repository
   conventions, and close the work in one focused commit.

## In Scope

- A semantic NF-e distribution adapter boundary and deterministic, simulator-only
  implementation.
- Independent received/entrada and emitted/saída flow requests, histories, continuation
  positions, outcomes, and P4 ingestion handoff.
- Safe bounded policy/result mapping, audit/observability integration, and fault/replay/
  concurrency tests.
- Contributor/operator documentation for the distribution contract and simulator scenarios.

## Out of Scope

- Portal Nacional/SEFAZ SOAP/HTTPS transport, endpoint/envelope/NSU/limit selection,
  homologation, production credentials, or real fiscal payloads.
- Ciência da Operação, manifestation persistence, complete XML retrieval, event linking, or
  their jobs; these are follow-up P5 slices and must consume this adapter boundary.
- Replacing P4 document identity, page/unit/checkpoint/cursor ownership, failure-state
  semantics, or P3 job retry/cooldown/block policy.
- ADN/NFS-e distribution, NFC-e/CT-e, manual upload, PDF/DANFE, search/download, ZIP,
  retention, deletion, dashboard, or broad frontend refactoring.
- Unrelated cleanup or changes to completed P0–P4 behavior.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P5 NF-e, first slice of the specified distribution
  capability; P4-02, P2-03, and P3-02/03 are the recorded prerequisites. P4-03 remains
  separately covered by open issue 0012 and is not duplicated here.
- Canonical spec: `specs/p5-nfe-distribution-and-manifestation.md`, current repository
  revision (no explicit version field), especially “Decisões e contratos”, “Estado e
  comportamento”, “UI, autorização, segurança e auditoria”, and “Falhas, testes e recovery”.
- Related work: `issues/0003_-_deterministic-fiscal-simulators-and-fixtures.md` supplies the
  simulator safety baseline; `issues/0009_-_durable-ingestion-pipeline-and-cursor.md` owns
  P4 ingestion and cursor/checkpoint invariants; `issues/0012_-_fiscal-ingestion-failure-state-matrix.md`
  owns the P4 state/recovery matrix.
- Current gap: `backend/nfx/adapters/simulation.py` exposes generic `FiscalResponse` and
  `NFeSimulator` scenarios, while `backend/nfx/collection/ingestion.py` consumes generic
  pages; no NF-e semantic distribution contract yet distinguishes the two NF-e flows at the
  adapter boundary or carries P5 distribution outcomes into the existing pipeline.
- Data/migration/compatibility: no schema migration is expected unless inspection proves a
  bounded persisted distribution execution field is necessary; preserve existing P4 models,
  constraints, cursors, artifacts, and P3 job idempotency. Any migration must be additive,
  upgrade-safe, and non-destructive.
- Security/rollout: production transport remains disabled by the existing destination and
  configuration guards. The simulator is the only runnable transport in this issue; no
  external endpoint or secret may be enabled as a shortcut.

## Tests

- **Unit:** semantic request/response validation, flow isolation, safe outcome classification,
  bounded fixture validation, policy defaults, redaction, and simulator replay/order.
- **Integration:** P4 handoff for both flows, independent cursor/checkpoint progress,
  pagination and restart, empty/degraded/blocked/malformed outcomes, fault boundaries,
  duplicate/concurrent requests, audit/metrics safety, and destination guard enforcement.
- **Validation commands:** focused adapter/ingestion tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A typed NF-e distribution contract accepts only the two NF-e flows and exposes bounded
  source, position, page, continuation, consumption/cooldown, and safe outcome data.
- [x] Received/entrada and emitted/saída use independent adapter histories and P4
  cursor/checkpoint scopes; activity in one flow cannot change the other.
- [x] The deterministic simulator covers paginated success, valid empty, unavailable,
  retryable, blocked, malformed, and unknown outcomes with stable replay and no network
  socket or production credential access.
- [x] Wrong-family, wrong-flow, malformed, over-bounded, sensitive, and invalid-position
  requests fail explicitly and cannot be converted into a successful empty page.
- [x] Successful pages hand original units to the existing P4 ingestion boundary before
  classification and cursor advancement; no second ingestion or cursor state machine is
  introduced.
- [x] Failed, partial, unknown, unresolved, or blocked pages do not falsely advance P4
  cursor/checkpoint progress, while valid empty advancement follows the P4 contract.
- [x] Replay, restart, duplicate, and concurrent distribution requests are deterministic and
  do not duplicate units, artifacts, documents, events, checkpoints, jobs, or progress.
- [x] Audit, logs, metrics, and safe job results contain only bounded permitted identifiers,
  flow/reason codes, and safe cursor or digest prefixes; raw payloads, XML, certificates,
  tokens, credentials, object keys, and unredacted external errors are absent.
- [x] Destination/configuration guards prevent any real NF-e transport from being enabled,
  and all focused and repository validation commands pass.
- [x] Contributor/operator documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the
  owning P5 spec/index evidence, this issue’s Resolution, and one focused implementation
  commit are synchronized before closure; manifestation, XML, events, and production
  transport are not claimed complete.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P5 NF-e, P5-01 implemented; P5-02/P5-03 remain pending.
- Spec: `specs/p5-nfe-distribution-and-manifestation.md` — distribution contract, independent
  flows, safety, audit, and recovery; current repository revision.
- Product/architecture authority: `PRD.md` FR-NFE-001/002/003/004 and BR-NFE-001/002/003;
  `ARCHITECTURE.md` sections 23, 28, 32, 33, 37, 38, and 40.
- Related issues: `issues/0003_-_deterministic-fiscal-simulators-and-fixtures.md`,
  `issues/0009_-_durable-ingestion-pipeline-and-cursor.md`, and
  `issues/0012_-_fiscal-ingestion-failure-state-matrix.md`.

---

## Resolution

Implemented issue 0013 as the P5-01 simulator-backed increment. Added
`nfx.adapters.nfe` with typed `NFeFlow`, flow-scoped `NFePosition`, bounded policy/request/
result contracts, safe outcome interpretation, audit/metrics hooks, and the sole P4
`ingest_page` handoff. Added `NFeDistributionSimulator` with independent received/issued
histories and correlation/position replay protection for duplicate/concurrent requests.
Extended synthetic fixtures with an explicit unknown outcome; no production transport,
credentials, endpoints, XML, events, or manifestation behavior was added.

Tests and validation:

- `python -m pytest tests/unit/test_fiscal_simulators.py -q` — baseline 33 passed.
- Focused NF-e tests — 14 passed after the final envelope/concurrency coverage; the existing simulator-focused suite remained green at 33 tests.
- `make lint` — Ruff, mypy (82 files), TypeScript, and ESLint passed.
- `make test-unit` — 175 passed.
- `TEST_RUN_ID=build0013-make make test-integration` — isolated migrations and 50 integration tests passed (5 existing botocore deprecation warnings).
- `make build` — Django check and frontend production build passed.
- `make smoke` — isolated web, worker, and scheduler liveness/startup checks passed.
- `graphify update .` — code graph refreshed; Graphify reported `hooks.json` and `pyproject.toml` as zero-node files, with no impact on this code graph.

Documentation synchronized in `specs/p5-nfe-distribution-and-manifestation.md`,
`specs/README.md`, `IMPLEMENTATION_PLAN.md`, and `docs/DEVELOPMENT.md`. P5-02/P5-03 and
real Portal Nacional/SEFAZ transport remain explicitly pending and Open.
