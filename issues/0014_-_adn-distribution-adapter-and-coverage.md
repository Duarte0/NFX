---
id: 0014
title: "Implement simulator-backed ADN distribution adapter and coverage contract"
type: feature
status: closed
priority: high
phase: P6
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0003, 0009, 0012, 0013]
blocked_by: []
affects:
  - backend/nfx/adapters/
  - backend/nfx/collection/
  - backend/nfx/companies/
  - backend/nfx/audit/
  - frontend/src/
  - tests/
  - docs/
---

## Description

Deliver the first independently valuable P6 capability: a semantic, simulator-only ADN
distribution boundary that models coverage and collects by actor, flow, and NSU. The current
baseline has a generic `AdnSimulator`, safe synthetic `FiscalRequest`/`FiscalResponse` types,
and the durable P4 ingestion service, but no ADN-specific contract that distinguishes covered
and uncovered companies, preserves actor/flow ownership, or hands ADN results into P4 with
their continuation semantics.

The Portal Nacional/ADN transport, official endpoint/layout/limit values, and municipal
integrations remain intentionally open and must not be invented in this slice.

## Objective and Expected Outcome

Allow a worker-facing ADN adapter to request a bounded synthetic distribution page for a
company, actor, and flow, report an explicit coverage snapshot, classify comprovable tomada,
prestada, event, and substitution units, and hand original units plus the next NSU to the
existing P4 ingestion owner. Covered and uncovered companies remain distinguishable; valid
empty, no coverage, unavailable, partial, and unknown outcomes do not collapse into one
message; repeated requests and restarts are deterministic and safe; and no official network,
municipal endpoint, credential, or real fiscal payload is required.

## Implementation Plan

1. Trace the P6 contract to the existing `FiscalRequest`/`FiscalResponse` port,
   `AdnSimulator`, `IngestionContext`, `FiscalIngestionService`, company coverage boundary,
   P3 collection/job execution, and audit/observability services. Define the smallest typed
   ADN request/response contract for company, actor/interested party, ADN flow, source, NSU,
   policy, bounded units, coverage snapshot, continuation, and safe outcome. Keep endpoint,
   layout, limit, and NSU rules behind a versioned adapter policy; do not put them in generic
   collection or document code.
2. Extend the ADN adapter boundary and deterministic simulator with independent actor/flow
   histories and NSU positions. Validate family, actor, flow, company coverage, request
   position, bounded fixture metadata, and allowed unit kinds at the boundary. Generate
   replayable synthetic cases for covered valid-empty, no-coverage, paginated success,
   unavailable/retryable, partial, malformed/unknown, event-without-parent, substitution,
   and restart/replay outcomes. A company with no coverage remains representable and
   collectable without being treated as an empty successful query.
3. Connect the semantic response to the existing P4 ingestion and job boundaries. Preserve
   original-before-classification ordering and delegate unit identity, quarantine, conflict,
   checkpoint, NSU advancement, and recovery semantics to P4. Pass only safe continuation,
   coverage, classification, and outcome metadata; do not create a second cursor, received
   unit, retry policy, page state machine, or document identity owner. A partial, failed,
   unknown, or unresolved page must not advance NSU; a valid empty page may advance only under
   the P4 rules. Remain compatible with issue 0012's P4-03 matrix as it is implemented.
4. Persist or expose the minimum coverage snapshot required by the approved contract through
   the existing company/collection ownership boundary, using bounded source, status,
   verification time, and safe evidence references. Keep coverage history/versioning
   explicit enough for policy rollback without rewriting prior collection outcomes; if schema
   changes are required, make them additive and ensure clean install and upgrade converge.
5. Add safe collection/status mappings for coverage, empty, unavailable, partial, unknown,
   quarantine, and retryable outcomes, plus bounded audit events and metrics for distribution
   start/completion, coverage, NSU progress, retry, and blocked/degraded results. Redact
   certificates, raw XML/payloads, object keys, tokens, credentials, CNPJ-sensitive labels,
   and unredacted external errors. Keep the existing authenticated role behavior: Admin and
   Operator control collection, while Viewer only receives the permitted safe status.
6. Write focused unit and integration tests before implementation for actor/flow isolation,
   coverage distinctions, empty versus no coverage/unavailable, pagination and NSU monotonicity,
   classification and substitution links, event-before-parent handling, malformed/unknown
   input, restart/replay/idempotency, concurrent duplicate requests, P4 handoff, no false
   progress, authorization, redaction, destination guards, and the no-network constraint.
   Run the repository's configured lint, unit, integration, build, and smoke validation.
7. Document the simulator-backed ADN contract, coverage meanings, actor/flow ownership, and
   recovery actions; refresh Graphify metadata with `graphify update .`; synchronize this
   issue's Resolution and the P6 evidence in `IMPLEMENTATION_PLAN.md`, the owning spec, and
   `specs/README.md` according to repository conventions; and close the work in one focused
   commit.

## In Scope

- A semantic ADN adapter boundary and deterministic, simulator-only implementation.
- Company coverage snapshots and explicit covered/no-coverage semantics.
- Independent actor/flow requests, NSU continuation, paginated units, classification, event
  and substitution relationships, and P4 ingestion handoff.
- Safe outcome, audit, metric, authorization, redaction, replay, concurrency, and recovery
  behavior required by the P6 contract.
- Contributor/operator documentation and synthetic unit/integration validation.

## Out of Scope

- Portal Nacional/ADN HTTP/SOAP transport, official endpoint/layout/limit selection,
  homologation, production credentials, or real fiscal payloads.
- Direct municipal integrations, coverage inferred from municipalities, or any source outside
  the Portal Nacional/ADN boundary.
- Replacing P4 identity, original-artifact, page/unit/checkpoint/NSU, failure-state, or
  reconciliation ownership; issue 0009 and issue 0012 remain authoritative.
- NF-e distribution/manifestation, document search/download, PDF/DANFSe, ZIP, retention,
  deletion, dashboard, or broad frontend architecture refactoring.
- New user-facing fiscal detail/search behavior or unrelated cleanup.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P6 NFS-e/ADN, P6-01/P6-02; implemented in this
  issue. The recorded direct prerequisites P4-02, P2-03, and P3-02/03 are complete.
- Canonical spec: `specs/p6-nfse-adn-distribution-and-coverage.md`, current repository
  revision (no explicit version field), especially “Contratos e estado Proposed”, “Regras e
  comportamento visível”, “Segurança, auditoria e observabilidade”, and “Falhas, testes e
  recovery”.
- Related work: issue 0003 supplies the deterministic simulator safety baseline; issue 0009
  owns durable P4 page/unit/checkpoint/NSU ingestion; issue 0012 owns the P4 failure/recovery
  matrix; issue 0013 establishes the separate NF-e adapter slice and must not be copied into
  ADN state ownership.
- Implemented gap: `backend/nfx/adapters/adn.py` now owns the semantic actor/flow/NSU and
  coverage contract over the generic simulator; `backend/nfx/collection/ingestion.py` remains
  the sole P4 owner of artifacts, identity, recovery, checkpoints, and NSU advancement.
- Data/migration/compatibility: prefer existing company coverage, collection, document, audit,
  artifact, and P4 indexes. Any new persistence must be additive, non-destructive, safe to
  upgrade, and must preserve immutable originals, independent ADN positions, and existing job
  idempotency. Do not choose unapproved official endpoint or coverage values.
- Security/rollout: the existing destination/configuration guards must continue to make the
  simulator the only runnable transport in this issue. No external source is enabled as a
  shortcut; safe logs and responses contain only bounded identifiers, reason codes, coverage
  status, and permitted digest prefixes.

## Tests

- **Unit:** semantic request/response validation, actor/flow isolation, coverage state mapping,
  safe fixture bounds, classification/link rules, policy versioning, redaction, and simulator
  replay/order.
- **Integration:** company coverage persistence/upgrade if needed, P4 handoff, independent NSU
  progress, pagination/restart/replay, empty/no-coverage/unavailable/partial/unknown outcomes,
  event/substitution handling, duplicate/concurrent requests, audit/metrics safety, RBAC, and
  destination guard enforcement.
- **Validation commands:** focused ADN/ingestion tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] The ADN adapter accepts only bounded, safe company/actor/flow/NSU/policy references and
  returns a typed coverage, unit, continuation, and outcome contract.
- [x] Covered, no-coverage, valid-empty, unavailable, partial, and unknown/quarantine results
  remain distinct in persistence/status/UI mappings; no-coverage is never reported as valid
  empty and a valid empty result never claims absolute absence.
- [x] Collection ownership is independent per company + ADN + actor + flow, and NSU advances
  monotonically only after the P4 durable treatment allowed by the state contract.
- [x] Tomada, prestada, event, and substitution units are linked only when required identity
  evidence is present; insufficient evidence preserves the original and does not claim a
  complete successful classification.
- [x] Original synthetic units are preserved before classification; unknown layouts, events
  without parents, partial pages, and source failures retain safe recoverable outcomes without
  false NSU progress.
- [x] Retry, restart, replay, and reconciliation converge idempotently without duplicating or
  overwriting units, documents, events, artifacts, coverage history, or NSU checkpoints.
- [x] Concurrent duplicate requests and retry races resolve deterministically through existing
  leases/constraints, without crossing actor/flow state or resurrecting blocked work.
- [x] Admin/Operator mutation and Viewer read behavior remain server-authorized; anonymous,
  revoked, wrong-company, wrong-actor, wrong-family, and wrong-flow requests are rejected or
  safely scoped without leaking existence or coverage details.
- [x] Audit, logs, metrics, persisted fields, and responses exclude raw XML/payloads,
  certificates, secrets, credentials, object keys, sensitive CNPJ labels, and unredacted
  external errors, while retaining bounded reason/coverage/NSU evidence.
- [x] No direct municipal or official ADN network call is made; destination guards and a
  network-socket test prove the slice is simulator-only.
- [x] Synthetic unit/integration tests cover positive and negative coverage, actor/flow,
  classification, recovery, authorization, integrity, idempotency, concurrency, and no-write/
  no-false-progress paths; all configured validation commands pass.
- [x] Required documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the owning P6
  spec/index evidence, this issue's Resolution, and one focused implementation commit are
  synchronized before closure; P5/P7 or real transport behavior is not claimed complete.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P6 NFS-e/ADN distribution and coverage.
- Spec: `specs/p6-nfse-adn-distribution-and-coverage.md` — coverage, actor/NSU contract,
  state distinctions, security, recovery, and simulated DoD.
- Architecture: `ARCHITECTURE.md` sections 3–5, 10.2, 10.3, 14, 32, 33, 37, and 38.
- Related issues: `issues/0003_-_deterministic-fiscal-simulators-and-fixtures.md`,
  `issues/0009_-_durable-ingestion-pipeline-and-cursor.md`,
  `issues/0012_-_fiscal-ingestion-failure-state-matrix.md`, and
  `issues/0013_-_nfe-distribution-adapter-and-simulator.md`.

---

## Resolution

- Implemented `nfx.adapters.adn` with bounded typed requests, actor/flow-scoped `AdnPosition`,
  versioned synthetic policy, safe coverage/outcome result mapping, audit/metrics, deterministic
  replay, concurrent duplicate protection, and simulator-only destination behavior.
- Added additive migration `0015_adn_coverage_snapshot` plus `record_adn_coverage`; collection
  status/UI exposes the latest safe ADN coverage snapshot. P4 remains the single owner of original
  artifacts, identity, event/substitution links, recovery, checkpoints, and NSU advancement;
  actor+flow is encoded in the P4 ADN flow scope.
- Extended synthetic fixtures for parent-backed events/substitutions and updated P4 to accept
  terminal pages without continuation and reject numeric non-monotonic NSUs. No official or
  municipal network behavior was added.
- Tests: focused ADN/simulator/NF-e unit tests passed (`60 passed`); isolated Compose integration
  suite passed (`53 passed` after the terminal-page and migration expectation fixes); `make lint`,
  `make build`, and frontend lint/build passed. The host-only database runs were initially blocked
  by PostgreSQL refusal; validation completed through the disposable Compose workflow.
- Docs synchronized in `specs/p6-nfse-adn-distribution-and-coverage.md`, `specs/README.md`,
  `IMPLEMENTATION_PLAN.md`, and `docs/DEVELOPMENT.md`; Graphify was refreshed as required.
