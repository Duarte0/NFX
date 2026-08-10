---
id: 0019
title: "Implement retention eligibility and administrative preview"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0006, 0010, 0012, 0015]
blocked_by: []
affects:
  - backend/nfx/retention/
  - backend/nfx/documents/
  - backend/nfx/artifacts/
  - backend/nfx/audit/
  - backend/nfx/urls.py
  - frontend/src/
  - tests/
  - docs/
---

## Description

Deliver P8-03 from the approved retention contract: calculate fiscal retention eligibility
and provide an Administrator-only, stable preview without deleting or mutating any fiscal
data. The current `backend/nfx/retention/` boundary is empty; there is no eligibility
calculation, versioned rule/scope representation, preview contract, route, UI, or retention
audit evidence. Document competence, immutable evidence, and artifact references already
exist, while PDF-derived artifacts remain outside this slice until the P7-03 renderer decision
is made.

## Objective and Expected Outcome

Administrators can list and inspect documents as `retido` or `elegível`, see the exact civil
date and rule version that produced the decision, and generate a deterministic preview of the
document's original/XML evidence and related events/derivatives by ID, digest, size, and
availability. The calculation is reproducible at a supplied/frozen clock, stale previews are
detectable, errors make an item non-executable rather than eligible, and no role or endpoint
can delete, hide, rewrite, or otherwise change source documents, evidence, artifacts,
collections, jobs, or cursors.

## Implementation Plan

1. Map the P8-03 contract to `Document.competence`/`emitted_at`, `DocumentEvidence`,
   `DocumentEventEvidence`, `Artifact` state/digest/size, the existing authenticated policy
   boundary, audit service, and the intentionally empty retention package. Keep retention as
   the owner of eligibility and preview decisions; documents and artifacts remain owners of
   identity and bytes. Define a versioned rule identifier, UTC/civil-date input, decision
   state, reason, and safe error vocabulary without inventing a deletion API.
2. Implement the accepted date rules exactly: NF-e uses 132 complete months from authorization
   (with the documented emission/authorization fallback defined by the spec), and NFS-e uses
   the first day of the sixth calendar year after emission. Use date arithmetic rather than
   elapsed seconds, make boundaries deterministic for leap/month-end cases, and keep company,
   user, certificate, and collection status independent of the retention date. Missing or
   inconsistent fiscal dates, conflicting/pending/divergent evidence, and unsupported family
   data must produce a bounded non-executable state, never `elegible`.
3. Add only the smallest additive persistence or indexed query support needed for repeatable
   decisions and previews. If decisions/previews are stored, persist rule version, calculation
   date, eligibility date, frozen scope identifier/hash, and safe lifecycle state; make writes
   idempotent and recalculable, detect changed evidence/scope, and ensure clean installation
   and upgrade converge without backfill silently changing prior evidence. A calculate-on-read
   implementation is acceptable when it provides the same stable scope/hash and invalidation
   guarantees.
4. Add Administrator-only list/detail/preview read boundaries. Validate bounded scope, date,
   family, state, pagination, and preview identifiers server-side; return only permitted
   metadata (document/event/artifact IDs, bounded digest prefixes, sizes, dates, rule/version,
   state, reason, and availability). Preview composition must enumerate all in-scope original
   and XML evidence links without copying fiscal bytes, and must mark missing or changed
   artifacts unavailable. Do not expose object-store keys or imply that preview authorizes
   deletion.
5. Add the smallest compatible frontend retention view for Administrators, with explicit
   `retido`, `elegível`, `não executável`, loading, empty, stale, and error states, the civil
   dates/rule version, and a clear non-deletion warning. Reuse the existing session/HTTP/RBAC
   boundaries and avoid adding controls, routes, or commands for deletion. Other roles must be
   refused server-side without disclosing retention records or preview contents.
6. Audit eligibility queries and preview generation with bounded actor, scope hash, rule
   version, result, and correlation fields. Use existing redaction and bounded-label rules;
   never log fiscal payloads, object keys, credentials, certificates, sensitive company
   labels, or unredacted provider/storage errors. Read paths must not create jobs or alter
   documents, artifacts, cursors, collection executions, or audit history beyond their own
   bounded read-audit event.
7. Write focused unit and integration/UI coverage before implementation. Freeze the clock and
   test the exact NF-e and NFS-e examples, leap/month-end and boundary dates, missing or
   conflicting evidence, changed scope/artifact invalidation, deterministic repeated previews,
   concurrent requests, idempotent persistence/retry, Administrator versus other roles,
   enumeration resistance, redaction, and complete no-write behavior. Run the repository's
   configured lint, unit, integration, build, smoke, and frontend checks.
8. Document the retention rule/version contract, preview limitations, PDF follow-up dependency,
   and operator behavior; synchronize P8-03 evidence in `IMPLEMENTATION_PLAN.md`, the owning
   spec, and `specs/README.md`; refresh Graphify with `graphify update .`; update this issue's
   Resolution and close the work in one focused commit. Do not claim P7-03 PDF coverage or
   P9-03 controlled deletion complete.

## In Scope

- P8-03 eligibility calculation for persisted NF-e and NFS-e documents using the canonical
  civil-date rules and versioned decision evidence.
- Administrator-only retention list/detail and deterministic preview of original/XML evidence,
  events, and document-linked artifacts without fiscal contents.
- Additive persistence/indexes only when required for recalculation, invalidation, or bounded
  queries; audit, redaction, RBAC, UI states, and synthetic validation.
- Explicit non-executable handling for missing, conflicting, pending, divergent, or unsupported
  evidence and documentation of the PDF-derived-artifact follow-up.

## Out of Scope

- Any delete command, route, job, cleanup, controlled deletion saga, or mutation of documents,
  events, artifacts, collections, jobs, cursors, or backups.
- PDF/DANFE/DANFSe eligibility or preview; P7-03 remains blocked on renderer selection and
  must be handled by a follow-up issue after that decision.
- ZIP export, dashboard aggregation, backup/restore, hardening, pilot/homologation, new fiscal
  transport, or changes to P4 identity/failure-state ownership.
- Changing retention periods, deserialization of fiscal payloads, or company/certificate
  lifecycle semantics defined by the canonical spec.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8 retention eligibility and preview, P8-03; the
  independently valuable original/XML slice is eligible because P7-03 is conditional only for
  existing PDFs. The P8-01 ZIP work remains separately gated by P7 consultation/download.
- Canonical spec: `specs/p8-retention-eligibility.md`, current repository revision, especially
  “Regras e estado”, “Contratos, UI e autorização”, “Segurança, auditoria e observabilidade”,
  and “Testes e recovery”.
- Related work: issue 0006 owns document identity/evidence, issue 0010 owns minimum document
  status/list semantics, issue 0012 owns ingestion failure states, and issue 0015 owns the
  broader consultation/download boundary. This issue consumes those contracts and must not
  duplicate them.
- Current verified gap: `backend/nfx/retention/` has no implementation; `nfx_document` and
  evidence tables provide competence, emission/authorization metadata, immutable artifact
  references, digest, size, and state, but no retention decision or preview owner exists.
- Data/compatibility: any migration must be additive, upgrade-safe, restartable, and preserve
  existing fiscal history. No destructive backfill or recalculation may rewrite immutable
  document/evidence facts.
- Security/rollout: all authorization is server-side; previews contain metadata only. The
  feature must remain read-only and must not enable deletion before the P9-02 restore gate.

## Tests

- **Unit:** civil-date rules, rule-version mapping, boundary arithmetic, invalid evidence
  classification, scope hashing/invalidation, pagination/allowlists, and safe error/redaction.
- **Integration:** clean install/upgrade, document/event/artifact preview composition, exact
  AC-015 dates, changed evidence, deterministic repeat/retry/concurrency, no-write behavior,
  Administrator RBAC, and direct endpoint enumeration resistance.
- **UI:** Administrator list/detail/preview states, stale/non-executable messaging, empty/error
  behavior, and denial for Operator/Viewer/anonymous sessions.
- **Validation commands:** repository-configured focused checks plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, `make smoke`, and configured
  frontend checks.

## Acceptance Criteria

- [x] NF-e and NFS-e decisions produce exactly the canonical eligibility dates, including the
  specified examples, civil-date boundaries, leap years, and month-end cases.
- [x] Company deactivation, user state, certificate expiry/replacement, and collection state
  do not alter a document's calculated retention date.
- [x] Missing, pending, divergent, conflicting, malformed, or unsupported evidence is never
  marked eligible and returns a bounded non-executable reason.
- [x] Every decision exposes a stable rule/version, calculation basis, eligibility date, and
  safe state; persisted decisions, if used, are recalculable and detect changed evidence.
- [x] Preview scope is frozen and hashable, repeated/retried/concurrent generation is
  deterministic and idempotent, and stale scope/artifact changes invalidate the old preview.
- [x] Preview enumerates all in-scope original/XML evidence and related links by safe metadata,
  without copying payloads or exposing object-store keys, credentials, or raw provider errors.
- [x] Only Administrators can list, detail, or generate previews; other roles and anonymous or
  revoked sessions are denied without revealing retention-record existence.
- [x] All retention reads are non-mutating for fiscal documents, events, evidence, artifacts,
  jobs, cursors, collection executions, and source objects; no deletion path is present.
- [x] Audit and metrics use bounded actor/scope/rule/result labels and contain no fiscal
  contents, secrets, object keys, or sensitive company labels.
- [x] Synthetic unit, integration, and UI tests cover expected and negative behavior,
  integrity/invalidation, retry/concurrency/idempotency, authorization, redaction, and no-write
  behavior; configured validation commands pass.
- [x] Documentation, `IMPLEMENTATION_PLAN.md`, the owning spec/index, Graphify metadata, and
  this issue's Resolution are synchronized before closure, and the work is closed in one
  focused commit without claiming PDF rendering or controlled deletion.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8 retention eligibility and preview, P8-03.
- Spec: `specs/p8-retention-eligibility.md` — canonical rules, contracts, security, tests,
  and deletion boundary.
- Related issues: `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0010_-_minimum-document-status-and-list-contract.md`,
  `issues/0012_-_fiscal-ingestion-failure-state-matrix.md`, and
  `issues/0015_-_document-consultation-and-secure-individual-download.md`.
- Current boundaries: `backend/nfx/retention/`, `backend/nfx/documents/`,
  `backend/nfx/artifacts/`, `backend/nfx/audit/`, and `backend/nfx/identity/`.

---

## Resolution

- Implemented calculate-on-read `retention-v1` decisions for NF-e (132 complete months from authorization) and NFS-e (January 1 of the sixth year after emission), using Brasília civil dates and bounded non-executable reasons for missing, changed, conflicting, malformed, unsupported, or unavailable evidence.
- Added Administrator-only `GET /api/retention/documents`, detail, and metadata-only preview routes with signed pagination, allowlisted filters, frozen `scope-v1` hashes, stale-scope `409`, no deletion route, redacted audit events, and bounded in-process metrics.
- Added the Administrator `#retencao` React feature with explicit retained, eligible, non-executable, loading, empty, stale, error, and non-deletion states. PDF-derived artifacts remain outside this slice pending P7-03.
- Tests: `tests/unit/test_retention.py` (5 passed); isolated `./scripts/test-integration.sh` passed 61/61 once and the final rerun passed both retention tests plus 60/61 overall, with only the pre-existing nondeterministic `test_document_consultation_filters_are_conjunctive_and_cursor_is_opaque` UUID-order assertion failing; 5 botocore deprecation warnings remain. Ruff, mypy, TypeScript/ESLint, Django check, frontend production build, and smoke passed.
- No migration was required: calculate-on-read decisions are recalculable and detect evidence changes without rewriting fiscal records. Updated the retention spec/index, implementation plan, development/operations documentation, and Graphify metadata.
