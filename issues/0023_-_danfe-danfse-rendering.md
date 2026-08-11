---
id: 0023
title: "Implement versioned DANFE and DANFSe PDF rendering"
type: feature
status: closed
priority: high
phase: P7
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0001, 0004, 0006, 0010, 0015]
blocked_by: []
affects:
  - requirements.txt
  - requirements-dev.txt
  - backend/nfx/artifacts/
  - backend/nfx/documents/
  - backend/nfx/jobs/
  - backend/nfx/audit/
  - backend/nfx/operations/
  - backend/nfx/urls.py
  - frontend/src/features/documents/
  - tests/
  - docs/
---

## Description

Implement the pending P7-03 rendering slice using the approved BrazilFiscalReport Python
integration. The current system preserves and downloads original/XML evidence, but has no
renderer dependency or boundary, derived-PDF persistence, render job, PDF route, UI action, or
rendering tests; document and dashboard contracts therefore report PDF/rendering as unavailable.

## Objective and Expected Outcome

An authorized user can request a supported NF-e DANFE or Nacional/ADN NFS-e DANFSe, reuse an
existing verified equivalent, or receive a durable render job whose worker produces a versioned
PDF artifact from the preserved original XML. The original/payload remains the fiscal source and
available on every render failure. Renderer identity/version and representation are part of the
derived-artifact identity, so concurrent requests and retries do not create equivalent PDFs or
overwrite a prior renderer version. Users can observe availability, pending, failed, and
regeneration states and download an authorized verified PDF; all operations are audited and
bounded metrics expose queue, duration, failure, and deduplication outcomes.

The verified gap is the pending P7-03 row in `IMPLEMENTATION_PLAN.md` and the unchecked DoD in
`specs/p7-danfe-danfse-rendering.md`. The approved renderer is BrazilFiscalReport; its concrete
version and minimal `danfse` extra must be pinned by this implementation. Existing document
status currently hard-codes `pdf_available` false, the dashboard reports
`renderer_not_implemented`, and repository searches find no renderer package, render job,
derived-PDF relation, route, or rendering test.

## In Scope

- Add a concrete, reproducible BrazilFiscalReport dependency pin, using only the minimal extra
  required for DANFSe and no `latest`, open range, or `cli` extra. Validate the installed version
  at runtime and use the Python API in the worker process.
- Add the smallest additive persistence contract needed to distinguish original/XML evidence from
  derived `danfe` and `danfse` artifacts and to retain document linkage, representation,
  `renderer_id`, effective `renderer_version`, MIME/type, digest, size, state, and safe result.
  Enforce one finalized equivalent for the complete identity while preserving older renderer
  versions and the original evidence.
- Add authorized request/reuse/regeneration behavior at the existing document boundary. A request
  must revalidate server-side access, select only supported documents and verified original XML,
  reuse a compatible finalized artifact, or atomically create/reuse a durable render job before
  returning its safe state.
- Register a render handler with the existing `JobEngine`/lease and retry contracts. The worker
  reads the verified original XML through `ArtifactStorageService`, invokes the selected library
  API in process without fiscal network access or subprocess/shell execution, and finalizes the
  PDF only after object bytes, hash, size, MIME/type, document link, representation, and renderer
  version are confirmed.
- Expose PDF availability, pending, failed, unsupported, and regeneration states through the
  existing document consultation/detail/download conventions. Preserve XML/original download
  behavior when rendering fails; allow only the roles already authorized to consult the document
  to request/regenerate/download its PDF, with authorization rechecked by the worker and on every
  download.
- Implement synthetic/anonymous fixtures and conformance checks for both renderer paths. The
  DANFSe slice must exercise the approved NT 008/2026 v1.02 requirements in the canonical spec,
  including one-page A4 portrait geometry, required blocks and fields, IBS/CBS and the
  `tpRetPisCofins=1` adjustment, QR URL/content and minimum size, homologation wording, fonts,
  separators/shading, cancellation/substitution watermarks, optional-block suppression, and
  absence of data not present in XML.
- Add bounded audit events and metrics for request, denial, reuse/deduplication, job start,
  success, failure, regeneration, and PDF download. Redact XML, payload, PDF, object keys, PFX,
  credentials, raw provider exceptions, and unbounded identifiers from logs, jobs, audit, metrics,
  HTTP responses, and frontend state.
- Update the document/operational documentation for renderer pinning, PDF lifecycle, failure and
  regeneration behavior, supported states, and the fact that the PDF follows the parent
  document's access, retention, and future controlled-deletion ownership.

## Implementation Plan

1. Map `specs/p7-danfe-danfse-rendering.md` to the existing `Artifact`/
   `ArtifactStorageService`, `Document`/evidence, document consultation, `JobEngine`/handler
   registry, identity policy, audit redaction, and operational metrics boundaries. Confirm the
   concrete installed BrazilFiscalReport API and output-byte behavior for the selected pin, then
   record that pin in the application dependency manifests without relying on CLI behavior.
2. Define an additive derived-artifact relation or equivalent metadata contract and migration.
   Keep original/XML evidence immutable and separately identifiable; make the derived identity
   exactly document logical identity + PDF type + `danfe`/`danfse` representation + renderer ID +
   installed renderer version. Add constraints/indexes that make finalized-equivalent reuse safe
   under concurrent requests, while a new renderer version creates a new identity instead of
   replacing history. Prove clean install, upgrade, and migration rerun behavior.
3. Implement the request and regeneration transaction using the existing server-side
   authorization and document consultation semantics. Lock or otherwise resolve concurrent
   requests by the derived identity, return an existing verified artifact when compatible, and
   enqueue or reuse one render job when it is absent or invalid. Reject unsupported family,
   missing/unverified/conflicting XML, unauthorized access, malformed identifiers, and bounded
   size/time/resource violations with safe states and no fiscal mutation.
4. Implement the worker handler as a sequence of verified source read, family/representation
   selection, in-process library call, bounded PDF validation, pending artifact write, storage
   head/hash/size/MIME verification, and atomic derived-link finalization. Use the captured job
   policy and existing lease behavior so timeout, worker death, lease loss, retry, and duplicate
   delivery cannot declare success early, lose the source, or create duplicate equivalents.
   Incomplete/divergent/missing output must remain pending, retryable, failed, or unavailable as
   appropriate, never finalized as a valid PDF.
5. Extend document detail/list and download flows plus the existing frontend document feature to
   expose safe PDF metadata and request/regenerate/download controls. Recheck session, role,
   document visibility, artifact integrity, and state at every HTTP operation; return no
   existence or provider-detail leak for denied, unsupported, missing, or failed PDFs. Keep the
   original XML route usable regardless of PDF state and do not add a second authorization path.
6. Add the renderer-specific audit/metrics events with bounded labels and safe correlation. Test
   audit-chain failure, redaction, no raw content/provider exception leakage, dashboard capability
   transition, and retention/access inheritance without moving retention or deletion ownership
   into P7-03.
7. Add focused unit and integration tests before implementation for package/API pinning, supported
   and unsupported inputs, all required synthetic NF-e/NFS-e scenarios, NT layout/QR/content
   assertions, artifact integrity, idempotency/reuse, concurrent requests, renderer-version
   history, lease recovery, timeouts, retries, missing/divergent output, RBAC, audit/redaction,
   original preservation, and safe download. Run the focused suites and repository validation
   commands listed below.
8. Document the operational and contributor contract, run `graphify update .`, synchronize the
   P7-03 evidence in `IMPLEMENTATION_PLAN.md`, `specs/p7-danfe-danfse-rendering.md`, and
   `specs/README.md`, update this issue's Resolution, and close the work in one focused commit.
   Do not claim P9-03 deletion, P8-02 expansion, real fiscal transport, or homologation complete.

## Out of Scope

- NF-e/ADN transport, collection, manifestation, endpoint credentials, homologation, or any
  external fiscal network call from the renderer.
- CLI, `bfrep`, subprocess, shell, or a second renderer implementation; renderer selection is
  already decided by the canonical spec.
- Changes to fiscal document identity, original/XML ingestion, cursor/lease policy, retention
  calculation, controlled deletion, backup/restore, ZIP composition, or a new queue/broker.
- Inventing unsupported NF-e/NFS-e layouts, enriching PDFs with external data, changing the NT
  v1.02 requirements, or treating a library-generated PDF as proof of conformance without fixture
  assertions.
- Automatic deletion, replacement, or mutation of original/XML evidence, older PDF versions, or
  parent document state when a derived render succeeds or fails.
- Unbounded PDF/file sizes, arbitrary XML/network inputs, raw fiscal content in logs or API
  responses, public/presigned object URLs, unrelated frontend refactoring, or browser-test
  infrastructure not required to demonstrate this contract.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P7-03 Renderização DANFE/DANFSe, priority 1 in the
  current pending-work sequence.
- Canonical spec: `specs/p7-danfe-danfse-rendering.md` — P7-03, current repository revision
  dated 2026-08-11; its acceptance criteria and NT 008/2026 v1.02 recorte are authoritative.
  Product references are FR-ART-002/003, BR-ART-001/002/003, NFR-006, AUD-006, AC-006, AC-010,
  and AC-014; architecture reference is ADR-011 and the cited artifact/job/security sections.
- Direct prerequisites are P3-01/P4-01/P7-01, complete in the plan/spec index. Related issue
  0001 owns durable jobs/leases, 0004 owns initial job observability, 0006 owns document identity
  and evidence, 0010 owns the document status/list contract, and 0015 owns consultation and
  individual-download authorization boundaries.
- Data/migration: all persistence changes must be additive and upgrade-safe. Derived artifacts
  must use a distinct logical class/ownership contract from original fiscal evidence and must not
  be eligible for source cleanup merely because a render retry fails.
- Compatibility: preserve existing document filters, consultation responses, original/XML
  download semantics, job policy/lease invariants, and role behavior. Existing unavailable
  rendering states may transition only when a verified derived artifact or safe render state
  exists.
- Security/rollout: use synthetic or anonymized XML only in tests; pin and review the dependency
  before image build; enforce XML safety, PDF size/time/resource limits, MIME/hash validation,
  authorization, redaction, and no network/shell execution. A missing or unsupported renderer
  must be an explicit unavailable/error state, never a successful PDF.
- Observability: metrics and logs must remain bounded and correlation-safe; no raw XML, PDF,
  object key, certificate, secret, token, or unredacted upstream exception may be persisted.

## Tests

- **Unit:** renderer/version selection, supported-family classification, XML source selection,
  derived identity and uniqueness, reuse/regeneration, safe error mapping, PDF bounds/metadata,
  QR payload/decoding, NT v1.02 field/layout rules, redaction, bounded metrics, and authorization.
- **Integration:** additive migration install/upgrade/rerun, request/detail/download routes,
  role/session denial, verified artifact finalization, missing/divergent source or output,
  concurrent idempotent requests, renderer-version history, retry/timeout/lease recovery,
  original preservation, audit-chain behavior, and dashboard/document availability transitions.
- **Frontend:** PDF available, pending, failed, unsupported, regenerating, loading, error, and
  safe-download states using the existing TypeScript/ESLint/build contract; no browser runner is
  currently configured, so do not add unrelated e2e infrastructure.
- **Validation commands:** focused rendering/document/artifact/job tests plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A concrete BrazilFiscalReport version is pinned with only the required DANFSe extra, the
  installed version is observable in safe renderer metadata, and runtime uses the Python API with
  no CLI, subprocess, shell, or fiscal-network call.
- [x] Authorized requests generate or reuse DANFE for supported NF-e and DANFSe for supported
  Nacional/ADN NFS-e documents from verified preserved XML; unsupported, missing, conflicting, or
  unverified source input returns a bounded non-success state without fiscal mutation.
- [x] Derived PDF identity includes document, PDF type, representation, renderer ID, and effective
  renderer version; one finalized equivalent is reused under retries/concurrency, while a new
  renderer version preserves the prior artifact and creates a distinct identity.
- [x] A render job is persisted before work is claimed, uses the existing lease/retry policy, and
  timeout, worker death, lease loss, duplicate delivery, and restart never declare success before
  verified artifact finalization or create duplicate equivalent PDFs.
- [x] Success requires finalized object bytes, hash, size, MIME/type, document linkage, renderer
  metadata, and representation to be mutually consistent; missing, incomplete, divergent, or
  oversized output is never served as a valid PDF.
- [x] PDF failure, unknown layout, unsupported data, retry exhaustion, or storage failure leaves
  the original XML/payload immutable, downloadable when otherwise authorized, and represented by
  a safe pending/failed/unavailable state with no raw provider or fiscal-content leak.
- [x] Synthetic fixtures and tests demonstrate the required DANFE cases and the NT 008/2026 v1.02
  DANFSe cases, including A4/one-page geometry, required/optional blocks, IBS/CBS and the
  `tpRetPisCofins=1` rule, QR URL/content and minimum size, homologation text, fonts, marks,
  cancellation/substitution watermarks, and no content absent from XML.
- [x] Document detail/list, request/regeneration, and download paths revalidate session, role,
  document visibility, artifact state, digest, and size; unauthorized or unavailable requests do
  not disclose PDF existence, object keys, credentials, or upstream exception text.
- [x] Request, denial, deduplication, start, success, failure, regeneration, and download are
  audited with safe IDs, representation, renderer/version, result, and correlation; metrics expose
  bounded queue, duration, failure, and deduplication labels without fiscal content or secrets.
- [x] PDF availability and failure/recovery states are reflected consistently in the document UI
  and operational capability response; PDF access, retention, and future deletion remain governed
  by the parent document rather than a parallel policy.
- [x] Synthetic unit/integration/frontend-contract coverage and all focused plus repository
  validation commands pass, including `make lint`, `make test-unit`, `make test-integration`,
  `make build`, and `make smoke`.
- [x] Documentation, `IMPLEMENTATION_PLAN.md`, the P7-03 spec/index, Graphify metadata, and this
  issue's Resolution are synchronized, and the issue is closed in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P7-03 Renderização DANFE/DANFSe.
- Spec: `specs/p7-danfe-danfse-rendering.md` — canonical renderer decision, invariants, NT
  008/2026 v1.02 recorte, security, observability, recovery, and DoD.
- Related issues: `issues/0001_-_durable-job-queue-and-leases.md`,
  `issues/0004_-_job-observability-and-initial-health.md`,
  `issues/0006_-_fiscal-document-identity-and-persistence.md`,
  `issues/0010_-_minimum-document-status-and-list-contract.md`, and
  `issues/0015_-_document-consultation-and-secure-individual-download.md`.
- Current boundaries: `backend/nfx/artifacts/`, `backend/nfx/documents/`, `backend/nfx/jobs/`,
  `backend/nfx/audit/`, `backend/nfx/operations/`, and `frontend/src/features/documents/`.

---

## Resolution

Implemented the P7-03 slice with `BrazilFiscalReport[danfse]==1.0.1` and a runtime version check.
Added the additive `DocumentRender` model/migration (`0019`), immutable source-artifact linkage,
renderer/version identity, idempotent request/regeneration through `JobEngine`, verified worker
finalization, safe failure states, dashboard capability reporting, PDF request/download routes,
RBAC revalidation, audit events, bounded rendering metrics, and document UI states/actions. The
DANFSe path applies the NT 008/2026 v1.02 PIS/COFINS retention presentation rule while preserving
the original XML; no CLI, subprocess, fiscal network, retention policy, or deletion path was added.

Tests and validation:

- `make lint` — passed (ruff, mypy, frontend TypeScript/ESLint).
- `make test-unit` — passed (`235 passed`).
- `make test-integration` — passed (`72 passed`, isolated PostgreSQL/MinIO; 5 existing botocore
  deprecation warnings).
- `make build` — passed (Django check and frontend production build).
- `make smoke` — passed (isolated Docker services, migrations, worker/scheduler/web boot).
- Focused renderer/document tests — passed, including real synthetic DANFE/DANFSe output, A4/one
  page checks, QR URL/size parameters, IBS/CBS and retention presentation, watermarks, idempotent
  job finalization, hash/integrity, and original-artifact preservation.

Documentation synchronized in `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md`, the P7-03 spec,
`specs/README.md`, and `IMPLEMENTATION_PLAN.md`; Graphify was refreshed after implementation.
Focused commit: the issue 0023 implementation commit created by this build pass (hash reported in
the build-pass handoff).
