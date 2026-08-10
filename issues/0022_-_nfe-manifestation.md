---
id: 0022
title: "Add simulator-backed NF-e manifestation"
type: feature
status: closed
priority: high
phase: P5
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0003, 0005, 0006, 0012, 0013, 0020]
blocked_by: [0013]
affects:
  - backend/nfx/adapters/
  - backend/nfx/collection/
  - backend/nfx/jobs/
  - backend/nfx/audit/
  - tests/
  - docs/
---

## Description

Implement P5-03 as a simulator-only NF-e manifestation operation. The current P5-01
adapter supports bounded distribution and independent received/issued positions, while
issue 0020 deliberately leaves manifestation persistence/submission outside its scope.
There is no NF-e-specific operation that records a manifestation intent and bounded
official-like result without duplicating P3 job or P4 document ownership.

## Objective and Expected Outcome

Provide a worker-safe, deterministic contract for submitting and recording Ciência or
another supported manifestation result against one identified NF-e. A repeated or
concurrent request must resolve to the same effect, preserve the result and correlation,
and never duplicate a manifestation, fiscal document, event, artifact, job, cursor, or
audit claim. The operation must be authorized and revalidated at execution time, use the
existing P3 policy/job and P4 document boundaries, and expose only safe result metadata.

## In Scope

- Simulator-backed typed requests, bounded outcomes, policies, deterministic fixtures, and
  replay behavior for the manifestation operation.
- A distinct idempotent manifestation execution keyed by company, NF-e identity, flow,
  manifestation type, and caller correlation/idempotency reference.
- Persistence of the manifestation result and its relationship to the existing NF-e,
  including safe handling of a missing, incompatible, or conflicting parent.
- Authorization, active-company/flow/certificate revalidation, retry/cooldown/block
  handling, append-only audit, bounded metrics, and safe job results.
- Focused unit/integration tests and contributor/operator documentation for the simulator
  contract, ownership boundary, and recovery scenarios.

## Implementation Plan

1. Extend the semantic boundary delivered by issue 0013 with typed manifestation request,
   result, policy, and simulator contracts. Validate company, NF-e identity, received versus
   issued flow, supported manifestation type, source/policy, certificate handle, bounded
   correlation, and idempotency references before any transport call; reject wrong-family,
   wrong-flow, malformed, sensitive, over-limit, or production-target values.
2. Model manifestation as its own P3-compatible job operation. Reuse existing command
   authorization, leases, retry/backoff/cooldown/block states, and worker error mapping;
   revalidate the company, enabled flow, certificate, and document authority at execution
   time. The adapter must not own a second cursor, document store, retry policy, or
   quarantine model.
3. Preserve the simulator response and register the manifestation through the existing
   document/audit ownership. Link it only to a compatible NF-e identity and company/flow;
   retain a safe pending or quarantined result when the parent is absent, and preserve both
   sides on identity or content conflict. Do not change the parent competence or infer a
   fiscal situation from a manifestation result.
4. Make the remote/simulated side effect and local registration recoverable by the same
   idempotency key. A replay, restart, duplicate, or concurrent request must return the
   existing result or a stable conflict rather than submit blindly or create duplicate
   rows, jobs, relationships, artifacts, progress, or audit events. A failure after
   submission but before registration must query/replay before retrying.
5. Map only bounded result codes, manifestation type, flow, safe identifiers/prefixes,
   counts, timestamps, and correlation metadata into logs, audit, metrics, and job output.
   Redact XML, raw payloads, PFX/certificate material, tokens, object keys, and external
   exception text; retain the simulator-only destination guard.
6. Write tests before implementation for accepted and rejected manifestations, authorization
   and certificate revalidation, flow/identity isolation, missing and incompatible parents,
   retry/cooldown/block outcomes, replay/restart/concurrency, idempotency, conflict
   preservation, audit/metric redaction, and destination guards. Run focused P5/job/document
   tests plus the repository validation commands.
7. Document the P5-03 simulator scenarios and ownership boundary, run `graphify update .`,
   synchronize the P5 evidence/status in `IMPLEMENTATION_PLAN.md` and the owning spec/index,
   update this issue’s Resolution, and close the work in one focused implementation commit.
   Keep official transport and homologation pending.

## Out of Scope

- Portal Nacional/SEFAZ SOAP/HTTPS transport, official endpoints/envelopes/NSUs, legal
  status mappings, homologation, production credentials, or real fiscal payloads.
- Complete XML retrieval, event ingestion, or other P5-02 work owned by issue 0020, except
  for the stable manifestation result needed as a caller-visible contract.
- NFC-e/CT-e, NFS-e/ADN, manual upload, PDF/DANFE/DANFSe, ZIP, retention, deletion,
  dashboard, or unrelated frontend refactoring.
- Replacing P3 authorization/retry/job ownership or P4 document, artifact, identity,
  cursor, checkpoint, conflict, and quarantine ownership.
- New business rules or unsupported manifestation types not defined by the canonical spec.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P5 NF-e, P5-03 manifestation; P5-01 is complete,
  P5-02 is tracked by issue 0020, and P5-03 is otherwise uncovered.
- Canonical spec: `specs/p5-nfe-distribution-and-manifestation.md`, current repository
  revision; especially “Decisões e contratos”, “Estado e comportamento”, “UI, autorização,
  segurança e auditoria”, “Falhas, testes e recovery”, and the acceptance/DoD section.
- Product/architecture authority: `PRD.md` FR-NFE-001/002/003/004, BR-NFE-001/002/003,
  BR-INT-003/004/005/006/007/008, AUD-005, AC-005–AC-009; `ARCHITECTURE.md` ADR-006/007
  and sections 10.2, 14, 19, 22, 23, 25, 28, 32, 33, 37, 38, and 40.
- Direct dependency: `issues/0013_-_nfe-distribution-adapter-and-simulator.md` supplies
  the NF-e semantic boundary and deterministic transport substitute. Reuse P3/P4 owners
  from issues 0005, 0006, 0009, 0012, and the result contract of issue 0020 without making
  issue 0020’s XML/event slice a duplicate dependency.
- Data/migration: prefer existing document/event, job, audit, and artifact models. If an
  additive manifestation or idempotency record is necessary, make it constrained,
  upgrade-safe, non-destructive, and covered by forward/rerun tests; do not create a
  parallel fiscal store.
- Security/rollout: simulator is the only runnable transport. Enforce bounded input,
  destination, certificate, and redaction constraints before calls or logging.

## Tests

- **Unit:** typed request/result and policy validation, manifestation-type bounds, flow and
  identity isolation, idempotency keys, simulator replay, safe result mapping, and redaction.
- **Integration:** job authorization and certificate revalidation, parent linking/pending/
  quarantine/conflict, retry/cooldown/block, crash/restart, duplicate/concurrent requests,
  audit/metrics safety, and destination guard enforcement.
- **Validation commands:** focused P5/job/document tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A typed, bounded, simulator-backed manifestation request/result supports only the
  canonical supported types and rejects invalid family, flow, identity, authorization,
  certificate, sensitive, malformed, over-limit, and production-target inputs without a
  fiscal side effect.
- [x] Manifestation runs as a distinct idempotent job operation using existing leases and
  retry/cooldown/block policy; worker execution revalidates company, flow, certificate, and
  document authority.
- [x] A successful result is linked to exactly one compatible NF-e and preserves type,
  flow, company, source, result, certificate reference, timestamp, and correlation without
  changing parent competence or inferring unsupported fiscal status.
- [x] Missing or incompatible parents are retained as safe pending/quarantined or conflict
  outcomes and are never silently discarded or attached to another document.
- [x] Replay, restart, duplicate, concurrent, and post-submission/pre-registration failure
  paths are recoverable by the same idempotency key and do not duplicate manifestations,
  documents, events, artifacts, jobs, progress, or audit events.
- [x] Timeout/unavailable/retryable results retry under the existing policy; cooldown and
  permanent certificate failures map to existing operational states; partial or unknown
  results never report false success or progress.
- [x] Logs, audit events, metrics, and job results contain no XML, raw payload, certificate,
  token, credential, object key, or unredacted external error and use bounded labels.
- [x] Unit and integration tests cover expected, negative, retry, idempotency, concurrency,
  ordering, security, and data-integrity behavior; `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke` pass.
- [x] Contributor/operator documentation, Graphify metadata, the P5 status/evidence in
  `IMPLEMENTATION_PLAN.md` and the owning spec/index, this issue’s Resolution, and one
  focused implementation commit are synchronized; P5 official transport remains pending.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P5-03 manifestation.
- Spec: `specs/p5-nfe-distribution-and-manifestation.md` — canonical P5 contract, current
  repository revision.
- Product/architecture authority: `PRD.md` FR-NFE-001/002/003/004, BR-NFE-001/002/003,
  BR-INT-003/004/005/006/007/008, AUD-005, AC-005–AC-009; `ARCHITECTURE.md` ADR-006/007
  and the NF-e, audit, XML, error, security, testing, and simulation sections.
- Related issues: `issues/0003_-_deterministic-fiscal-simulators-and-fixtures.md`,
  `issues/0005_-_manual-collection-control.md`,
  `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0012_-_fiscal-ingestion-failure-state-matrix.md`,
  `issues/0013_-_nfe-distribution-adapter-and-simulator.md`, and
  `issues/0020_-_nfe-xml-eventos-e-ciencia.md`.

---

## Resolution

Implemented P5-03 as a simulator-only NF-e manifestation slice. Added bounded
`NFeManifestationRequest`/`NFeManifestationResult` contracts, the supported Ciência da Operação
type, deterministic outcomes, redacted adapter audit, and replay-safe
`NFeManifestationSimulator`. Added the durable `NFeManifestation` record and migration
`0017_nfe_manifestation`; it retains the target UUID for missing parents and links successful
results only to a compatible NF-e without changing competence or fiscal situation.

Registered `nfe.manifestation` with the existing P3 worker lease/policy/retry/cooldown/block
boundary. Enqueue authorization and worker execution revalidate active company, enabled NF-e flow,
current certificate, and parent authority. The same bounded idempotency key is used for the job,
record, and simulator effect; replay returns the existing job/result and missing or incompatible
parents are quarantined without a transport call. No official endpoint, credential, XML, cursor,
event, artifact, or parallel document store was added.

Tests and validation:

- `pytest tests/unit/test_nfe_followup.py` — 11 passed.
- `TEST_RUN_ID=build0022-integration2 make test-integration` — 69 passed, 5 pre-existing botocore deprecation warnings.
- `make lint` — passed (Ruff, mypy, TypeScript, ESLint).
- `make test-unit` — 227 passed.
- `make build` — passed (Django check and Vite production build).
- `make smoke` — passed (isolated PostgreSQL/MinIO, web/worker/scheduler readiness).

An additional isolated rerun exposed a pre-existing nondeterministic assertion in
`tests/integration/test_document_status.py::test_document_consultation_filters_are_conjunctive_and_cursor_is_opaque`
(1 pass, then 2 failures with random UUID ordering); this issue does not touch consultation or
ordering. The complete integration run above passed before that unrelated check was rerun.

Documentation synchronized in `docs/DEVELOPMENT.md`, `IMPLEMENTATION_PLAN.md`,
`specs/README.md`, and `specs/p5-nfe-distribution-and-manifestation.md`. Graphify was refreshed
after the implementation. Official Portal Nacional/SEFAZ transport and homologation remain Open.
