---
id: 0039
title: "Modernize ZIP export UX and durable-state presentation"
type: feature
status: closed
priority: high
phase: P10
created_at: 2026-08-12
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0015, 0021, 0034, 0035]
blocked_by: [0034, 0035]
affects:
  - frontend/src/features/exports/
  - frontend/src/shared/ui/
  - frontend/scripts/
  - frontend/browser-tests/
  - tests/
  - docs/
---

## Description

Deliver the pending P10-06 export UX slice on top of the completed visual foundation and
authenticated shell. The durable P8-01 export owner already freezes the selection, composes a
bounded ZIP, records explicit completeness/failure/expiration state, rechecks ownership at
download, and cleans only temporary ZIP artifacts. The current `ExportsSection` is still a
minimal table: it hides prior rows when a refresh fails, exposes technical `safe_error` values,
does not distinguish all durable states or download eligibility, and leaves request, detail, and
download interactions without consistent loading, stale, retry, keyboard, or duplicate-action
feedback.

## Objective and Expected Outcome

Authenticated users can request, monitor, inspect, and download their authorized ZIP exports with
clear accessible presentation of pending/processing, complete/available, partial, failed, expired,
and unavailable states. Progress and completeness are shown only from the durable response; a
partial export never looks complete, an expired export never suggests source deletion, and a
download action is available only when the owner-provided URL and server authorization make it
eligible. Reloads and repeated actions remain safe, deterministic, and understandable without
changing the existing export API, job, storage, audit, or authorization contracts.

## In Scope

- Recompose `ExportsSection` with the P10-01 shared primitives for the export request action,
  list, detail, state badges, count/size context, expiration, safe feedback, loading, stale-last-
  read, retry, empty, partial, and unavailable presentation.
- Map every server export state to a user-facing semantic label and explanation: pending,
  processing, available/complete, partial, failed, expired, and excluded where returned. Keep
  partial, failed, expired, and unavailable visually and semantically distinct.
- Show only progress, produced/expected counts, bytes, timestamps, completeness, and safe action
  metadata returned by the export owner. Do not estimate percentage or completion when the response
  does not provide it.
- Preserve the existing `#exportacoes` destination, request scope/filter contract, list/detail
  ownership behavior, server-produced download URL, expiration window, and safe message semantics.
- Make request, refresh, detail, retry, and download interactions keyboard-accessible and
  interaction-idempotent. Refresh authoritative list/detail state after a request or retry result;
  do not simulate local job progress.
- Retain the last safe list or detail response during a refresh failure only with an explicit
  stale/loading/error state and retry path. Ensure an older concurrent list/detail response cannot
  overwrite a newer selection or state.
- Extend repository-native UI contract and browser fixtures with synthetic export responses for all
  roles and negative session contexts, every export state, reload during processing, partial versus
  failed, expiration, unauthorized/expired download, network failure, repeated request, focus, and
  keyboard behavior.

## Out of Scope

- Changes to `nfx.exports` selection, allowlisted filters, idempotency rules, job scheduling or
  retry, ZIP composition, item ordering, artifact storage, cleanup, expiration duration, audit,
  metrics, rate limits, or server-side authorization.
- New export filters, client-side document selection, progress polling, notifications, reports,
  snapshots/cache/materialized reads, local job state, or a second export route.
- Changes to the `/api/exports` list/create/detail/download payloads, HTTP status behavior, CSRF
  handling, ownership rules, download URL, or source-document retention semantics.
- Rendering XML/PDF bytes, object keys, archive paths, document contents, credentials, certificate
  material, raw adapter/enrichment payloads, internal exceptions, raw technical reason codes, or
  production/customer data in the UI or fixtures.
- Dashboard, documents, companies, certificates, collections, administration, retention, or
  cross-feature redesign beyond preserving the existing shell destination and any owner-provided
  export entry context. Issues 0036–0038 own their respective P10 slices.
- Mobile behavior below the approved desktop/notebook baseline, a client router, global state,
  new UI/framework dependencies, backend code, migrations, infrastructure, telemetry, flags, or
  rollout configuration.

## Dependencies and Notes

- **Plan item:** `IMPLEMENTATION_PLAN.md` — P10-06 “Exports UX — pending”, under “P10 Frontend
  UX & Visual System”. P10-03, P10-04, and P10-05 are separate open issues 0036–0038; they are
  not prerequisites for this independent export slice. P10-08 remains the later transversal
  validation slice.
- **Canonical spec:** `specs/p10-exports-ux.md`, v1.0. It requires faithful durable-state
  language, returned-only progress/completeness, authorized download/expiration handling, and
  distinct partial/failure/unavailable presentation.
- **Functional owner:** `specs/p8-zip-export.md` and issue 0021. Its `/api/exports` list/create,
  detail, and download behavior is authoritative for frozen selection, ownership, counts, safe
  errors, ZIP availability, and the 24-hour temporary artifact window.
- **Prerequisites:** P10-01 shared tokens/primitives are verified by issue 0034 and P10-02 shell
  composition by issue 0035. Issue 0015 remains the completed owner of the document filters and
  individual-download context that export requests may reuse; this issue must not create a second
  filter contract.
- **Verified gap:** `frontend/src/features/exports/ExportsSection.tsx` renders a plain table and
  appends raw `safe_error` text to state labels. A failed `listExports()` sets `error` and hides
  the previously retained rows instead of marking them stale; request, refresh, detail, and
  download controls have no consistent in-flight guard; `requestExport()` generates a new
  timestamp key per click; detail responses are not ordered against a newer selection; and the
  UI does not explicitly explain partial, expired, unavailable, or returned-only progress and
  download eligibility. Existing `frontend/scripts/ui-contract.mjs` and the shell browser matrix
  verify navigation only, not this export state/action matrix.
- **Data/migration/compatibility:** no persisted data or migration is expected. Preserve same-
  origin credentials, CSRF behavior for creation, `no-store` responses, pt-BR labels, Brasília
  timestamp semantics, the `#exportacoes` anchor, the owner-provided filters/scope, and the
  server-provided download URL without decoding or synthesizing it.
- **Security/observability/rollout:** the UI is not an access-control boundary. Render only safe
  owner-provided metadata and mapped messages; never infer authorization from a hidden download
  control. The server must remain the authority for ownership, availability, expiration, and
  audit. Do not add logs, metrics, audit events, flags, or rollout settings.

## Implementation Plan

1. Inventory the current export response types, list/create/detail/download calls, P8 state and
   ownership contracts, P10-01 primitives, shell role composition, and existing synthetic test
   harness. Define export-owned presentation maps for states and safe error categories without
   changing the response contract or treating a missing value as success, zero, or completion.
2. Recompose the export section into an accessible request/action area, list, and selected detail
   panel. Present server-provided counts, bytes, timestamps, completeness, expiration, and
   download eligibility with distinct labels for pending/processing, available/complete, partial,
   failed, expired, excluded, and unavailable. Do not display archive paths, document IDs, raw
   reason codes, or any byte content.
3. Preserve the current export scope/filter and idempotency contract. Guard duplicate clicks only
   while the current request/detail/retry/download interaction is active, keep controls usable by
   keyboard, and never announce success or enable download before the authoritative response
   confirms it. A repeated intent must not create a client-side second success or invent a new
   durable state.
4. Make list/detail loading deterministic: retain the last safe response during refresh only with
   visible stale/loading context; keep safe prior rows on retryable failure; map failure to a
   retry path; and prevent an older list or detail response from replacing a newer request, filter,
   selected export, or state. Reload must observe the durable server state rather than local
   progress or an estimated percentage.
5. Bind the download action strictly to the owner-provided authorized URL and current eligible
   state. Expired, failed, partial, excluded, unavailable, unauthorized, and expired-session
   responses must not expose a download action or imply that source documents were removed;
   download failures must remain safe and retryable without exposing response internals.
6. Extend `frontend/scripts/ui-contract.mjs` and the existing browser fixture/matrix with synthetic
   exports covering all three authenticated roles, anonymous/expired sessions, each durable state,
   processing reload, counts with and without progress, partial versus failed, expiration, safe
   errors, unauthorized/expired download, repeated actions, stale/error/retry retention, detail
   ordering, focus/keyboard semantics, and redaction. Run focused and repository validation with
   synthetic data only.
7. Update export/development documentation and Graphify metadata through the repository workflow,
   synchronize P10-06 evidence in `specs/p10-exports-ux.md`, `specs/README.md`, and
   `IMPLEMENTATION_PLAN.md`, fill this issue's Resolution, and close only after the plan sync and
   one focused commit are recorded.

## Tests

- **Focused frontend contract:** `npm --prefix frontend run test:ui-contract`, extended with
  export state labels, returned-only progress/completeness, stale/error/retry retention, request
  idempotency, detail ordering, download eligibility, expiration, keyboard/focus, role/session,
  and safe-redaction assertions using synthetic payloads.
- **Browser validation:** `npm --prefix frontend run test:browser` or the existing Docker browser
  target for Chrome, Firefox, and Edge desktop at the approved widths; cover Administrator,
  Operador, Visualizador, anonymous/expired sessions, direct `#exportacoes`, reload during
  processing, partial/failed/expired states, repeated actions, keyboard focus, and failed
  downloads without network access to real services.
- **Frontend quality:** `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- **Repository regression:** `make lint`, `make test-unit`, `make build`, and `make smoke`; no
  real fiscal service, customer data, certificate, XML/PDF, ZIP bytes, or production credential
  is permitted.

## Acceptance Criteria

- [x] Pending/processing, available/complete, partial, failed, expired, excluded, and unavailable
  export states have distinct accessible pt-BR labels and presentation; no raw API state or error
  code is the only user-facing meaning.
- [x] Counts, bytes, timestamps, completeness, and progress are displayed only when returned by
  the durable export response; no percentage, completion, total, or local job state is inferred.
- [x] Partial remains distinct from complete/available and failed, preserves the authorized count
  and scope context, and never enables a download that the owner did not authorize.
- [x] Expired removes only the download action, clearly communicates expiration, and never implies
  that the source documents or fiscal archive were removed.
- [x] Refresh, reload, request, detail, retry, and download failures retain prior safe context only
  with explicit stale/loading/error feedback and a retry path; raw technical reasons and response
  internals are not exposed.
- [x] Repeated request, refresh, detail, retry, and download interactions are guarded at the
  interaction boundary; an older concurrent response cannot overwrite a newer export selection
  or state, and no duplicate listener/request is introduced by rendering or navigation.
- [x] Request scope/filter, server totals/counts, ownership, CSRF/session behavior, `#exportacoes`,
  expiration semantics, and the server-provided download URL remain unchanged; no client-side
  authorization or ZIP business rule is added.
- [x] Administrator, Operador, and Visualizador retain the existing role-appropriate export
  visibility and ownership behavior; anonymous and expired sessions remain on the existing
  authentication/denial flow, including direct `#exportacoes` access.
- [x] Download is offered only for an authorized, current owner-provided URL and eligible state;
  unauthorized, unavailable, failed, partial, excluded, expired, and expired-session cases do not
  reveal whether another user's export exists.
- [x] The UI and all synthetic fixtures contain no XML/PDF/ZIP bytes, archive paths, document
  contents or identifiers, credentials, certificate/key material, customer data, or internal
  exceptions.
- [x] Focused UI and browser tests cover every listed state, returned/missing progress, partial vs
  failed, reload during processing, expiration, ownership/session negatives, safe errors,
  duplicate-action guards, stale/error/retry retention, concurrency ordering, keyboard/focus, and
  redaction using synthetic data.
- [x] `npm --prefix frontend run test:ui-contract`, the applicable browser matrix, frontend
  lint/build, `make lint`, `make test-unit`, `make build`, and `make smoke` pass without backend,
  migration, dependency, or HTTP-contract changes.
- [x] Export/development documentation, P10-06 spec evidence, `specs/README.md`,
  `IMPLEMENTATION_PLAN.md`, and Graphify metadata are synchronized before closure.
- [x] The Resolution records implementation and validation evidence, the implementation-plan
  sync, and closure in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “P10 Frontend UX & Visual System”, P10-06.
- Canonical spec: `specs/p10-exports-ux.md` — v1.0.
- Functional owner: `specs/p8-zip-export.md` — P8-01, completed in issue 0021.
- Export behavior: `docs/EXPORTS.md` and the existing `/api/exports` list/create/detail/download
  contract.
- Related document scope: `specs/p7-document-consultation-and-individual-download.md`, issue
  0015.
- UI baseline: issues 0034 and 0035; neighboring P10 domain slices are issues 0036–0038.
- Architecture: `ARCHITECTURE.md` — `App → features → shared`, server-side authorization, and
  safe fiscal-data boundaries.

---

## Resolution

Implemented the P10-06 export UX slice in `ExportsSection` using the existing shared primitives.
All durable export states now have distinct accessible pt-BR presentation, owner-returned metrics
only, safe redaction, explicit stale/loading/error/retry context, ordered list/detail responses,
interaction guards, and download eligibility restricted to an owner-provided URL in the eligible
state. The `/api/exports` contract, scope/filter behavior, ownership, CSRF/session handling,
expiration semantics, `#exportacoes` anchor, and server-side authorization were preserved.

Tests/validation: `npm --prefix frontend run test:ui-contract`, frontend lint/build, the Docker
browser matrix (234/234 synthetic tests across Chrome/Firefox/Edge at 1024/1280/1440 px), `make
lint`, `make test-unit`, `make build`, and `make smoke` all passed. The browser fixtures cover all
durable states, missing/returned metrics, stale/retry retention, request/detail/download guards,
ordering, roles/sessions, redaction, focus, and keyboard behavior.

Migrations: none. No backend, HTTP contract, dependency, storage, job, ZIP, or authorization
changes were required.

Docs/Graphify: synchronized `docs/EXPORTS.md`, `docs/DEVELOPMENT.md`,
`specs/p10-exports-ux.md`, `specs/README.md`, and `IMPLEMENTATION_PLAN.md`; Graphify was updated
through the repository workflow.

Key decisions: partial, failed, expired, excluded, and unavailable remain distinct; missing server
metadata is not synthesized; raw error codes, identifiers, paths, content, and exceptions are not
rendered. No specialized frontend skill/plugin was installed or applicable; the implementation
used the repository's shared design system and native UI/browser validation workflow.
