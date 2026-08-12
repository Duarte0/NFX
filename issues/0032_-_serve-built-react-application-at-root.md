---
id: 0032
title: "Serve the built React application from the root route"
type: bug
status: closed
priority: high
phase: P0
created_at: 2026-08-11
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0008, 0011]
blocked_by: []
affects:
  - backend/nfx/urls.py
  - Dockerfile
  - frontend/
  - tests/
  - scripts/
  - docs/
---

## Description

Close the P0 follow-up for delivering the React application from the runtime image. The
committed baseline's `/` handler returns the literal `NFX INOV foundation` placeholder even
though the frontend build stage produces `frontend/dist`; the built `index.html` and its assets
therefore are not an evidenced runtime contract.

The current worktree contains an uncommitted route/static-serving delta that appears to address
part of this behavior, but it is not covered by an issue, focused tests, or runtime-image
verification. Treat that delta as implementation evidence to reconcile, not as completion
evidence. The root cause remains the missing verified connection between the image's built
artifact and the Django HTTP boundary.

**Reproduction on the tracked baseline:**

1. Build the frontend/runtime application image.
2. Request `GET /` from the web process.
3. Observe the placeholder text instead of the built HTML; no contract proves the referenced
   assets are served safely.

## Objective and Expected Outcome

The runtime image serves the built React `index.html` at `/` and serves only the assets that
belong to that build with their correct MIME types. A missing build is an explicit `503`, and an
unknown, missing, traversal, or outside-build asset is a `404`; none falls back to the
placeholder, succeeds with an unrelated file, or leaks filesystem details. Existing API,
health, authentication, and session URLs remain unchanged.

## In Scope

- The Django root/static delivery boundary for the built `index.html` and its published asset
  paths.
- Runtime-image assembly and read access for the frontend distribution produced by the existing
  TypeScript/Vite build stage.
- Path normalization and containment checks, including traversal and symlink escape handling,
  without turning the endpoint into a general filesystem server.
- Focused HTTP, build-artifact, and isolated runtime-image/smoke validation for success, MIME,
  absence, invalid paths, and compatibility behavior.
- Small runtime/development documentation updates that explain the verified root and asset
  delivery contract.

## Out of Scope

- A SPA router or fallback for arbitrary application paths.
- New frontend screens, design-system work, client-side authorization, API changes, cache policy,
  upload support, or serving source files and arbitrary static directories.
- Changes to authentication, session, health semantics, database schema, migrations, fiscal
  adapters, or deployment secrets.
- Browser-test infrastructure or unrelated frontend refactoring.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P0 follow-up “Rota raiz e build React” (item 2a).
- Canonical spec: `specs/p0-frontend-build-delivery.md`, v1.2. Its contract and acceptance
  checklist govern the root response, asset MIME/containment, missing-build failure, and
  compatibility requirements.
- Supporting specs: `specs/p0-project-foundation.md` and
  `specs/p1-authentication-sessions-and-rbac.md`; the latter owns the existing web shell and
  session contract. Related issue 0008 establishes the reproducible build contract, and issue
  0011 establishes the React composition boundaries; neither verifies runtime root delivery.
- Architecture references: `ARCHITECTURE.md` §§9, 10.4, 11, 33, 34, 37, and 41. The frontend
  is served internally by the application image; authorization remains server-side and static
  delivery must not expose sensitive or source content.
- Data/migration: none. The build artifact is deployment output, not application data.
- Security/compatibility: use a fixed distribution root from the image/repository layout, resolve
  requested paths before checking containment, reject escapes and symlinks outside the build,
  return safe status text without local paths, and preserve all existing API/health/session
  routes. Repeated or concurrent GETs must remain read-only and deterministic.
- Rollout: verify a clean frontend build and the app image before runtime smoke; no production
  credential, endpoint, or external asset source is introduced.

## Implementation Plan

1. Reconcile the current root and asset-serving delta with the v1.0 spec and the Docker frontend
   build stage. Establish one fixed distribution boundary that is present and readable in the
   runtime image, while retaining the existing React `App`/feature composition and API URL
   ordering.
2. Make `GET /` read the built `index.html` and return HTML only when that file exists. Serve
   published asset requests beneath the build's asset directory, derive MIME types from the
   actual asset, and reject an unresolved candidate unless it is a regular file whose resolved
   path remains inside the intended directory. Do not add a catch-all or SPA fallback.
3. Define and exercise the failure contract: absent build returns `503`; absent, malformed,
   repeated-prefix, traversal, symlink-escaped, or non-file asset requests return `404`; no
   response includes a local path, source file, or successful placeholder. Keep `/api/*`, health,
   authentication, and session routing behavior unchanged.
4. Add focused tests that use synthetic temporary/build artifacts and the real Vite output where
   appropriate. Parse the built HTML to request its referenced asset, compare returned bytes and
   MIME, cover all negative paths, and assert repeated/concurrent reads do not mutate application
   state. Add an isolated image/runtime smoke that proves the artifact survives image assembly
   and is readable by the runtime process.
5. Update the relevant runtime/development documentation and Graphify metadata, synchronize the
   P0 follow-up evidence in `IMPLEMENTATION_PLAN.md`, `specs/p0-frontend-build-delivery.md`, and
   `specs/README.md`, fill this issue's Resolution, and close the work in one focused commit.

## Tests

- **Unit/HTTP:** root response, build absence, asset lookup, MIME mapping, path containment,
  traversal/symlink escape, non-file handling, safe error bodies, and unchanged API/health/session
  routes using synthetic artifacts and Django's test client.
- **Build/runtime:** `npm --prefix frontend run build`, the configured synthetic-profile
  `make build`, and an isolated application-image probe for `/`, a referenced asset, missing
  build, and invalid asset paths.
- **Regression/smoke:** repeated and concurrent read requests with no database, audit, or file
  writes outside the build; existing `make lint`, focused tests, `make test-unit`,
  `make test-integration`, and `make smoke` must remain green.

## Acceptance Criteria

- [x] `GET /` serves the built `index.html` from the runtime image and never returns the
  `NFX INOV foundation` placeholder.
- [x] Every asset URL emitted by the built HTML is served from the same build, with bytes matching
  the artifact and a correct MIME type; source files and arbitrary paths are not served.
- [x] A missing or unreadable build returns `503` with a safe body, while missing, malformed,
  non-file, traversal, and symlink-escaped asset paths return `404` without filesystem details.
- [x] The distribution root is fixed by deployment layout, path resolution rejects escapes before
  reading, and no request can select an alternate directory or sensitive file.
- [x] Existing API, health, authentication, and session endpoints retain their current status,
  response, authorization, and URL behavior after root/asset delivery is enabled.
- [x] Repeated and concurrent root/asset reads are deterministic and side-effect free; no
  database row, audit event, session, job, or unrelated file is created or changed.
- [x] Tests cover successful delivery, MIME, missing-build and invalid-path failures, traversal
  and symlink containment, image assembly, compatibility, redaction, and no-write behavior with
  synthetic data only.
- [x] `npm --prefix frontend run build`, configured `make build`, `make lint`, `make test-unit`,
  `make test-integration`, and `make smoke` pass, plus the focused root/asset and runtime-image
  checks.
- [x] Runtime/development documentation, Graphify metadata, `IMPLEMENTATION_PLAN.md`, the P0
  spec/index, and this issue's Resolution are synchronized before closure.
- [x] The issue is closed only after the implementation-plan sync is recorded and all changes
  are committed in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P0 follow-up “Rota raiz e build React”.
- Spec: `specs/p0-frontend-build-delivery.md` — v1.0.
- Supporting specs: `specs/p0-project-foundation.md` and
  `specs/p1-authentication-sessions-and-rbac.md`.
- Architecture: `ARCHITECTURE.md` §§9, 10.4, 11, 33, 34, 37, and 41.
- Related issues: `issues/0008_-_reproducible-clean-checkout-build.md` and
  `issues/0011_-_frontend-architecture-refactor.md`.

---

## Resolution

Implemented the runtime React delivery contract in `backend/nfx/urls.py`. The root now reads the
fixed `frontend/dist/index.html`, returns a safe `503` when the build cannot be read, and serves
only canonical `/assets/` files whose resolved regular file remains inside the non-symlinked build
boundary. MIME types come from the resolved asset, traversal/repeated-prefix/malformed paths and
symlink escapes return `404`, and existing API, health, authentication, and session routes remain
ordered and unchanged.

Added synthetic Django HTTP coverage for build success/absence, referenced assets and MIME, safe
negative paths, symlink containment, compatibility, concurrent reads, and no-write behavior.
Extended `scripts/smoke.sh` to compare runtime responses against the image's `/app/frontend/dist`
artifacts, and documented the deployment boundary. No migration or dependency change was needed.
Graphify was refreshed with `graphify update .` after the code and documentation changes.

Validation included the focused Docker test suite (10 passed), frontend lint/build, Ruff, shell
syntax validation, configured build/image assembly, and the isolated runtime smoke. The P0 spec,
spec index, and implementation plan record the completed evidence.
