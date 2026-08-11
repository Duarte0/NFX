---
id: 0027
title: "Reconcile dashboard document cards with canonical archive filters"
type: feature
status: closed
priority: high
phase: P8
created_at: 2026-08-11
updated_at: 2026-08-11
closed_at: 2026-08-11
related_issues: [0010, 0015, 0018, 0026]
blocked_by: []
affects:
  - backend/nfx/operations/
  - backend/nfx/documents/
  - backend/nfx/urls.py
  - frontend/src/features/dashboard/
  - frontend/src/features/documents/
  - tests/
  - docs/
---

## Description

Close the document-card drill-down gap in the progressive P8-02 dashboard slice. The dashboard
already calculates document totals and NF-e/NFS-e direction/category counts from persisted
`Document` rows, but its links do not preserve the selected period, the document UI applies only
the family query parameter, and the NFS-e links currently use `tomado`/`prestado` while the
aggregation uses the canonical `tomada`/`prestada` values. A user can therefore open a list that
does not represent the card that was selected.

This is a document-specific follow-up to issue 0018. It reuses the completed P7 consultation
contract from issue 0015 and is separate from issue 0026, which covers collection-execution
cards. No new document metric, fiscal source, or persistence policy is required.

## Objective and Expected Outcome

For each document card, an authenticated user can open the canonical document archive with the
selected dashboard period and the exact allowlisted family/direction/category filter already
represented by that card. The archive reports a bounded persisted-document match count that
reconciles with the dashboard value, while retaining the existing safe collection-status and
quarantine semantics. Invalid, unavailable, or unauthorized reads fail safely without becoming a
successful zero or exposing fiscal payloads.

The verified gap is the unchecked “Todo card clicável abre lista com filtro equivalente e
contagem reconciliada” criterion in `specs/p8-dashboard-and-operational-health.md`, together with
the non-equivalent document URLs and incomplete filter hydration in the current implementation.

## In Scope

- The seven document cards: total, NF-e, NFS-e, NF-e entrada, NF-e saída, NFS-e tomada, and
  NFS-e prestada.
- Dashboard drill-down metadata that carries the exact current `[from,to)` period plus the
  canonical P7 filter mapping for each card.
- The document archive's existing bounded read contract, including a server-computed
  persisted-document match count for the active filters; existing page rows and collection
  status/quarantine behavior remain available and clearly distinguishable from that count.
- React navigation and URL hydration for period, family, NF-e direction, and NFS-e category,
  including loading, valid-empty, unavailable/degraded, and invalid-filter states.
- Reconciliation and regression coverage for filter composition, Brasília civil-date boundaries,
  authorization, redaction, and read-side effects; synthetic fixtures only.

## Out of Scope

- Collection-execution drill-downs covered by issue 0026, company/certificate/job cards, rendering,
  disk, backup, monetary-value cards, notifications, reports, or new dashboard metrics.
- Changes to document identity, ingestion, collection state, cursor ownership, artifact bytes,
  PDF generation, retention, deletion, exports, fiscal adapters, or P7 authorization semantics.
- A new dashboard-specific document owner, snapshot/cache, background job, migration, external
  source, or browser-test runner.
- Changing the public meaning of the existing P7 inclusive `emitted_from`/`emitted_to` filters;
  the dashboard's half-open period must be translated without including the selected end date.
- Returning XML/PDF content, object keys, certificate material, raw provider errors, or unbounded
  search/correlation data in a dashboard or archive response.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P8-02, “Dashboard e saúde operacional”, progressive
  dashboard expansion; P8 remains partial until its independently delivered capabilities satisfy
  the spec's drill-down and reconciliation criteria.
- Canonical specs: `specs/p8-dashboard-and-operational-health.md`, repository revision 2026-08-11
  (no explicit version field), and `specs/p7-document-consultation-and-individual-download.md`,
  whose P7-01/P7-02 contract is complete in repository revision 2026-08-11 (no explicit version
  field).
- Product/architecture references: `PRD.md` FR-DASH-001/002/003 and AC-013; `ARCHITECTURE.md`
  sections 14, 17, 18, 20, 32, 36, and 37. Documents remains the owner of archive selection;
  operations composes dashboard values and links.
- Completed prerequisites: issues 0010 and 0015 provide the bounded archive/list contract;
  issue 0018 provides the dashboard period/card contract. Issue 0026 is adjacent but independent
  because it owns collection-execution rows, not document rows.
- Current baseline: dashboard aggregation filters persisted documents by `emitted_at` in the
  Brasília-local `[from,to)` interval, while the public consultation parser accepts inclusive
  emission dates. Preserve both contracts and adapt the upper boundary explicitly.
- No migration is expected: use the existing document query/index ownership and add only additive
  response metadata if the count is not already present. Existing P7 consultation audit behavior
  remains the only audit path; dashboard navigation must not create a second audit event.
- Rollout: a document query/count failure must degrade only document cards and the archive view;
  unrelated dashboard cards and Admin-only operational/backup health remain readable. Never fall
  back to an unfiltered list or report zero when the source is unavailable.

## Implementation Plan

1. Define one canonical mapping from the seven dashboard card IDs to P7 filters. Include the
   selected dashboard dates in the drill-down contract, use `tomada` and `prestada` exactly as the
   persisted NFS-e categories, and reject any unsupported or repeated dashboard filter instead of
   silently broadening the query.
2. Reuse `DocumentListParams`/`scoped_documents` as the archive selection owner. Translate the
   dashboard's half-open civil-date interval to the existing emission-date contract so records on
   the start date are included and records on the `to` date are excluded. Compute a bounded,
   server-side persisted-document match count from the same queryset used for the page, while
   keeping quarantine/status rows and their existing P4 semantics explicit rather than counting
   them as persisted documents.
3. Extend dashboard links and the document section's URL hydration so every supported filter is
   sent to the server and visibly represented in the archive state. Keep pagination, detail,
   download, PDF, and existing collection-status behavior unchanged; the browser must not
   recompute counts or authorize access.
4. Add focused unit/integration/frontend-contract tests for all seven mappings, current and
   previous periods, start/end boundaries, the two NFS-e categories, combined filters, zero versus
   unavailable, invalid/repeated parameters, anonymous/revoked sessions, response redaction, and
   count/page consistency. Prove repeated and concurrent reads do not mutate fiscal, artifact,
   job, cursor, or collection state; retain only the existing bounded P7 consultation audit.
5. Update the dashboard/document contributor or operator documentation and refresh Graphify
   metadata for the new relationship. On completion, synchronize the P8-02 evidence in
   `IMPLEMENTATION_PLAN.md`, `specs/p8-dashboard-and-operational-health.md`, and `specs/README.md`,
   fill this issue's Resolution, and close the work in one focused commit.

## Tests

- **Unit:** card-to-filter mapping; canonical NFS-e category values; half-open dashboard-to-P7
  date translation; bounded parsing; count/status mapping; and safe unavailable/error handling.
- **Integration:** seven card/count reconciliations with synthetic persisted documents; current and
  previous periods; Brasília boundary timestamps; NF-e direction and NFS-e category filters;
  quarantine/conflict/status preservation; deterministic pagination; roles; invalid/repeated and
  revoked-session requests; redaction; source failure isolation; and no fiscal-state mutation on
  repeated/concurrent reads.
- **Frontend:** dashboard link construction, URL hydration for every supported filter, visible
  period/filter state, and loading, empty, unavailable, degraded, invalid, and count branches under
  the existing TypeScript/ESLint/Vite contract. Do not add a browser-test runner.
- **Validation commands:** focused dashboard/document tests plus `make lint`, `make test-unit`,
  `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] All seven document cards carry the exact selected dashboard period and their canonical,
  allowlisted family/direction/category filter; no link uses `tomado`/`prestado` when the stored
  category is `tomada`/`prestada`.
- [x] The server applies the filters through the canonical P7 archive contract, uses Brasília
  `[from,to)` semantics for dashboard periods, includes the start boundary, excludes the end
  boundary, and rejects malformed, repeated, reversed, overlong, or unsupported values without
  falling back to an unfiltered query.
- [x] The archive exposes a bounded persisted-document match count derived from the same selection
  as its page, and synthetic data proves each document card value equals that count for the same
  period/filter, including zero-result periods and boundary records.
- [x] Existing P4 collection-status, quarantine, conflict, pagination, detail, download, and PDF
  behavior remains compatible; quarantine/status rows are not silently treated as persisted-card
  matches and no document identity, artifact, cursor, or ingestion data is rewritten.
- [x] Anonymous, revoked, and unauthorized requests are rejected server-side; permitted roles
  receive only the existing safe archive metadata, with no XML/PDF payload, object key,
  certificate, raw provider error, or unbounded correlation data.
- [x] A document database/audit/source failure is reported as unavailable or degraded and never as
  a successful zero; unrelated dashboard cards and Admin-only operational/backup health remain
  intact.
- [x] Repeated and concurrent identical reads are deterministic and do not create dashboard
  records, jobs, cursor advances, collection transitions, or artifact mutations; any consultation
  audit remains bounded and follows the existing P7 policy without duplicate dashboard auditing.
- [x] Synthetic unit, integration, and frontend-contract tests cover expected and negative behavior,
  boundaries, reconciliation, status preservation, RBAC, redaction, failure isolation, and
  repeatability, and all listed validation commands pass.
- [x] Documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the P8-02 spec/index, this
  issue's Resolution, and one focused implementation commit are synchronized before closure.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P8-02 dashboard and operational-health expansions.
- Spec: `specs/p8-dashboard-and-operational-health.md` — period, card, drill-down, degradation,
  and reconciliation contract.
- Spec: `specs/p7-document-consultation-and-individual-download.md` — canonical bounded archive
  filters, safe rows, pagination, authorization, and consultation behavior.
- Product: `PRD.md` — FR-DASH-001/002/003 and AC-013.
- Architecture: `ARCHITECTURE.md` — document/artifact ownership, safe read boundaries, and
  dashboard composition.
- Related issues: `issues/0010_-_minimum-document-status-and-list-contract.md`,
  `issues/0015_-_document-consultation-and-secure-individual-download.md`,
  `issues/0018_-_initial-dashboard-and-operational-health.md`, and
  `issues/0026_-_dashboard-collection-drilldown-reconciliation.md`.

---

## Resolution

Implemented the P8-02 document-card drill-down slice.

- Added one canonical seven-card P7 filter mapping shared by dashboard aggregation and archive
  selection; dashboard links preserve the exact civil `[from,to)` period and use `tomada`/`prestada`.
- Extended the authenticated read-only document archive with bounded server-side `total`, stable
  page metadata, normalized dashboard filter/boundary data, and half-open Brasília period
  translation without counting quarantine rows as persisted documents.
- Added safe source-failure `503` handling, server-side period/filter validation, URL-hydrated React
  controls for dates/family/direction/category, and explicit loading, empty, invalid, unavailable,
  degraded, and reconciled-total states. Existing P4/P7 rows, pagination, detail, downloads, PDF,
  authorization, and audit behavior remain unchanged.
- No migration, cache, job, lease, cursor advance, artifact mutation, or dashboard-specific audit
  event was introduced.

Validation performed:

- `python -m pytest tests/unit/test_document_consultation.py tests/unit/test_document_status.py tests/unit/test_dashboard.py` — 43 passed.
- `python -m ruff check ...` on changed backend/tests — passed.
- Targeted `mypy` for changed backend modules — passed.
- `npm --prefix frontend run lint` — passed.
- `TEST_RUN_ID=0027-targeted-2 ./scripts/test-integration.sh` — migration/schema validation and all 85 integration tests passed; 7 pre-existing botocore deprecation warnings.
- Full unit suite, `make build`, `make lint`, `make test-integration`, and `make smoke` were run in final verification.
- `graphify update .` — completed.

Documentation synchronized in `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md`,
`specs/p8-dashboard-and-operational-health.md`, `specs/README.md`, and `IMPLEMENTATION_PLAN.md`.

Status: closed.
