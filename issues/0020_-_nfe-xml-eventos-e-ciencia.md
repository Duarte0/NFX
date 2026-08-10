---
id: 0020
title: "Add simulator-backed NF-e Ciência, complete XML, and event ingestion"
type: feature
status: closed
priority: high
phase: P5
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0003, 0006, 0009, 0012, 0013, 0015]
blocked_by: [0013]
affects:
  - backend/nfx/adapters/
  - backend/nfx/collection/
  - backend/nfx/documents/
  - backend/nfx/jobs/
  - backend/nfx/audit/
  - tests/
  - docs/
---

## Description

Implement the next independently valuable P5 slice, P5-02: after NF-e distribution has
identified a document, the simulator-backed adapter must support Ciência da Operação,
complete XML retrieval, and event delivery through the existing P4 artifact/document
boundaries. The real Portal Nacional/SEFAZ transport, official endpoint/envelope/NSU
choices, and manifestation persistence remain outside this issue.

## Objective and Expected Outcome

Provide a worker-safe, deterministic contract that can schedule Ciência as its own job,
request complete XML only after a permitted Ciência result, and ingest event units while
preserving explicit parent links. Original responses must be durable before parsing or
classification; retries, restart, duplicate requests, and a response arriving before its
parent must be safe and observable without exposing XML, certificates, credentials, object
keys, or raw external errors.

The verified gap is the P5-01 baseline in issue 0013: `NFeDistributionAdapter` and
`NFeDistributionSimulator` currently cover bounded distribution pages and independent
received/issued positions, but explicitly do not provide XML retrieval, event handling,
Ciência jobs, or manifestation. Existing P4 document models can persist documents/events
and related evidence, but no NF-e-specific adapter contract connects these follow-up
operations to that owner.

## In Scope

- Simulator-only semantic contracts and deterministic fixtures for Ciência, complete XML,
  and NF-e events, reusing the P5-01 adapter/policy boundary.
- A distinct Ciência execution/job flow with authorization, certificate revalidation,
  bounded safe outcomes, retry/cooldown/block handling, and idempotent correlation.
- Complete XML retrieval only for a document whose Ciência result permits it, with original
  and XML evidence linked to the same document through the P4/artifact owners.
- Event ingestion with explicit parent identity/relationship, safe pending or quarantine
  handling when the parent is absent, replay/conflict behavior, and no competence mutation
  of the parent document.
- Bounded audit and metrics for start, completion, retry, blocked/invalid outcomes, XML
  retrieval, and event linking.
- Focused unit/integration coverage and contributor/operator documentation for the new
  simulator scenarios and ownership boundaries.

## Implementation Plan

1. Start from `NFeDistributionAdapter`, `NFeDistributionRequest`, and
   `NFeDistributionSimulator` delivered by issue 0013. Add typed, versioned semantic
   requests/results for Ciência, complete XML, and events while keeping official transport
   identifiers and limits behind policy. Validate company, NF-e flow, document identity,
   correlation, certificate handle, source, and bounded payload metadata at the boundary;
   reject wrong-family/wrong-flow, malformed, sensitive, over-limit, and production-target
   inputs without converting them to successful empty results.
2. Model Ciência as a separate job operation. Reuse P3 job leases/policy and P3-05 command
   authorization, revalidate the active company/flow/certificate at execution time, and
   make the operation idempotent by document plus manifestation-intent/correlation key.
   Only a result classified as permitting retrieval may issue a complete-XML request;
   denied, unavailable, retryable, cooldown, blocked, malformed, or unknown results must
   not request XML or advance unrelated collection positions.
3. Preserve every accepted original response in artifact storage before XML parsing,
   identity mapping, event classification, or status summary. Hand complete XML and event
   units to the existing P4 ingestion/document service rather than creating adapter-owned
   document, event, cursor, checkpoint, retry, or quarantine state. XML is additional
   evidence for the existing document; an event is linked only when its parent identity and
   company/family context are compatible.
4. Define recovery for out-of-order and partial work: an event without a resolvable parent
   remains pending/quarantined with a safe reason and can be replayed after the parent is
   ingested; it must never be silently discarded or attached to another parent. A failure
   after the remote/simulated operation but before local registration must query/replay by
   the same idempotency key, not submit blindly again. Duplicate XML, event, and concurrent
   requests return existing effects/evidence or a stable conflict, without duplicate rows,
   artifacts, jobs, or audit claims.
5. Add safe audit/metric mappings for Ciência and follow-up retrieval/linking. Emit only
   permitted IDs, flow, bounded reason codes, outcome, counts, and digest/cursor prefixes;
   redact XML, PFX/certificate material, tokens, raw payloads, object keys, and external
   exception text. Keep destination guards closed so no real endpoint or production secret
   can be selected by these contracts or fixtures.
6. Add tests before implementation for permitted/denied Ciência, XML gating, independent
   received/issued behavior, event-before-parent, compatible/incompatible parent,
   pagination-independent replay, retry/cooldown/block, malformed/unknown payloads,
   duplicate and concurrent requests, crash/restart boundaries, original-before-parse,
   artifact/document/event integrity, redaction, authorization, certificate revalidation,
   and destination guards. Run focused tests plus the repository lint, unit, integration,
   build, and smoke commands.
7. Document the P5-02 contract and simulator scenarios, run `graphify update .`, update
   this issue’s Resolution and the P5 evidence/status in `IMPLEMENTATION_PLAN.md` and the
   owning spec/index according to repository conventions, then close the work in one
   focused implementation commit. Do not mark P5-03 manifestation complete.

## Out of Scope

- Portal Nacional/SEFAZ SOAP/HTTPS transport, official endpoints, envelopes, NSU/sequence
  selection, homologation, production credentials, or real fiscal payloads.
- Manifestation persistence/submission beyond the simulator result needed to gate XML;
  P5-03 remains a separate follow-up.
- NFC-e/CT-e, ADN/NFS-e, manual upload, PDF/DANFE/DANFSe, ZIP, retention, deletion,
  dashboard, or unrelated frontend refactoring.
- Replacing P4 identity, artifact, event, quarantine, checkpoint, cursor, or recovery
  ownership, or duplicating P3 retry/cooldown/block policy.
- New business rules or official legal/status mappings not defined by the canonical spec.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P5 NF-e, P5-02 (Ciência/XML/eventos); P5-01 is
  complete in issue 0013 and P5-03 remains pending.
- Canonical spec: `specs/p5-nfe-distribution-and-manifestation.md`, current repository
  revision, especially “Decisões e contratos”, “Estado e comportamento”, “UI, autorização,
  segurança e auditoria”, “Falhas, testes e recovery”, and the P5-01 evidence section.
- Direct dependency: `issues/0013_-_nfe-distribution-adapter-and-simulator.md` provides the
  NF-e semantic boundary and deterministic simulator. P4 identity/artifact/ingestion and
  P3 jobs/policy are owned by issues 0006, 0009, 0012, and the completed job issues.
- Related read-side contract: issue 0015 exposes event links and XML availability; this
  issue only supplies the missing P5 source-side evidence and must preserve that contract.
- Data/migration: prefer existing `Document`, `DocumentEvent`, evidence, artifact, job, and
  audit models. If inspection proves an additive persisted operation/idempotency field is
  necessary, it must be upgrade-safe, non-destructive, constrained, and covered by migration
  forward/rerun tests; do not create a parallel document/event store.
- Security/rollout: simulator is the only runnable transport. Enforce size/MIME/XML/XXE and
  redaction constraints before parsing or logging, and retain the existing fail-closed
  destination/configuration guard.

## Tests

- **Unit:** typed request/result validation, Ciência outcome gating, flow and identity
  isolation, bounded XML/event fixture validation, idempotency keys, safe result mapping,
  redaction, and simulator replay/order.
- **Integration:** job authorization and certificate revalidation, original-before-parse,
  XML evidence attachment, event parent linking/quarantine/conflict, retry/cooldown/block,
  crash/restart, duplicate/concurrent requests, audit/metrics safety, and destination guard
  enforcement.
- **Validation commands:** focused P5/document/job tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] Ciência has a typed, bounded, simulator-backed contract and distinct idempotent job
  operation; unauthorized, inactive, invalid-certificate, wrong-flow, and invalid-document
  requests are rejected without a fiscal side effect.
- [x] Complete XML is requested only after a permitted Ciência result, and denied,
  unavailable, retryable, cooldown, blocked, malformed, or unknown results never trigger
  XML retrieval or unrelated cursor/checkpoint advancement.
- [x] Accepted original responses are durably stored before parsing/classification; XML is
  stored as linked evidence for the existing document and is not treated as a replacement
  for the immutable original.
- [x] Events with a compatible parent preserve explicit parent, company, family, flow,
  relationship, and evidence links; an absent or incompatible parent is retained as a safe
  pending/quarantined outcome and never attached implicitly.
- [x] Received and issued NF-e operations remain isolated, and no adapter-owned cursor,
  document/event identity, quarantine, retry, or recovery state duplicates P4/P3 ownership.
- [x] Timeout/unavailable/retryable responses retry under the existing policy, cooldown and
  permanent certificate failures map to their existing states, and partial/unknown work
  cannot falsely report success or progress.
- [x] Replay, restart, duplicate, and concurrent Ciência/XML/event requests are idempotent:
  they do not duplicate jobs, artifacts, documents, events, evidence, or progress; a
  post-operation/pre-registration failure can recover by query/replay.
- [x] Parent competence and fiscal situation are not inferred or rewritten from an event;
  event/document identity conflicts preserve both evidence and a safe conflict state.
- [x] Logs, audit events, metrics, and job results contain no XML, raw payload, certificate,
  token, credential, object key, or unredacted external error, and metrics use bounded labels.
- [x] XML/event payload and parser handling enforce configured size/type/XXE/destination
  constraints; no production endpoint or credential is reachable from simulator fixtures.
- [x] Unit and integration tests cover expected, negative, retry, idempotency, concurrency,
  ordering, security, and data-integrity behavior, and `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke` pass.
- [x] Contributor/operator documentation, Graphify metadata, the P5 status/evidence in
  `IMPLEMENTATION_PLAN.md` and the owning spec/index, this issue’s Resolution, and one
  focused implementation commit are synchronized; P5-03 remains explicitly pending.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P5-02 Ciência/XML/eventos; P5-01 complete, P5-03 pending.
- Spec: `specs/p5-nfe-distribution-and-manifestation.md` — canonical P5 contract, current
  repository revision.
- Product/architecture authority: `PRD.md` FR-NFE-001/002/003/004, BR-NFE-001/002/003,
  BR-INT-003/004/005/006/007/008, AUD-005, AC-005–AC-009; `ARCHITECTURE.md` ADR-006/007
  and sections 10.2, 14, 19, 22, 23, 25, 28, 32, 33, 37, 38, and 40.
- Related issues: `issues/0003_-_deterministic-fiscal-simulators-and-fixtures.md`,
  `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0009_-_durable-ingestion-pipeline-and-cursor.md`,
  `issues/0012_-_fiscal-ingestion-failure-state-matrix.md`,
  `issues/0013_-_nfe-distribution-adapter-and-simulator.md`, and
  `issues/0015_-_document-consultation-and-secure-individual-download.md`.

---

## Resolution

Implemented issue 0020 as the P5-02 simulator-only follow-up slice. Added bounded semantic
contracts and deterministic scenarios for Ciência, complete XML, and NF-e events in
`backend/nfx/adapters/nfe.py`; Ciência is a distinct idempotent job and only a permitted result
creates the complete-XML job. Worker registration reuses the P3 lease/policy boundary and
revalidates the active company, NF-e document/flow, and current certificate at execution time.

Complete XML persistence stores and links the accepted original response before XML validation,
then stores XML as additional `fiscal_xml` evidence. Event delivery delegates to the existing P4
ingestion/document owners, preserves explicit parent relationships, isolates follow-up page scope
from distribution cursors, quarantines missing/incompatible parents, and retries missing parents
through reconciliation. No manifestation persistence, official transport, production endpoint, or
credential was added.

Tests and validation:

- `pytest tests/unit/test_nfe_followup.py` — 9 passed.
- Isolated PostgreSQL/MinIO `tests/integration/test_nfe_followup.py` — 2 passed.
- `make lint` — passed (backend/frontend lint, Ruff, and mypy).
- `make test-unit` — 225 passed.
- `TEST_RUN_ID=build0020-final make test-integration` — 67 passed.
- `make build` — passed; `make smoke` — passed.
- No migration was required.

Documentation synchronized in `IMPLEMENTATION_PLAN.md`, `specs/README.md`,
`specs/p5-nfe-distribution-and-manifestation.md`, and `docs/DEVELOPMENT.md`. Graphify was refreshed;
P5-03 manifestation and real Portal Nacional/SEFAZ transport remain explicitly pending/Open.
