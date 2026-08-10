---
id: 0008
title: "Make the clean-checkout build contract reproducible"
type: feature
status: open
priority: low
phase: P0
created_at: 2026-08-09
updated_at: 2026-08-09
closed_at: ~
related_issues: [0007]
blocked_by: []
affects:
  - Makefile
  - docs/
  - specs/p0-project-foundation.md
  - tests/
---

## Description

The P0 foundation is implemented and verified with configured commands, but the documented
`make build` contract is not reproducible from a clean checkout. The target calls Django's
configuration check without the mandatory `NFX_PROFILE` and external-secret inputs, so it fails
closed before reaching the frontend build even though the same check succeeds with the repository's
synthetic test profile. This is a build/documentation gap, not a reason to weaken boot validation.

The environment-template hygiene work in issue 0007 is related because both touch development
configuration documentation, but this issue owns only the build command's reproducible contract;
it must not restore or depend on versioned usable secrets.

## Objective and Expected Outcome

Give a fresh checkout one documented, deterministic `make build` path that supplies only safe,
synthetic test configuration for the non-network Django check and then builds the frontend. The
command must remain independent of PostgreSQL, MinIO, fiscal destinations, and versioned secrets,
while direct application boot and invalid configuration continue to fail closed.

## Implementation Plan

1. Compare the P0 foundation contract, the configuration loader's required inputs, and the existing
   `lint`/`test-unit` synthetic values. Choose the smallest repository convention that makes the
   `build` target self-contained or clearly requires an explicit equivalent invocation; keep the
   synthetic values local to the command path and do not introduce them into `.env.example`,
   Compose defaults, runtime configuration, or production settings.
2. Update the build command sequence so the Django check receives a valid test/development
   profile and only the synthetic secret/database/storage values needed for configuration parsing,
   then runs the existing frontend build. Preserve command ordering, fail-fast behavior, and the
   invariant that `make build` does not start services or open fiscal/database/object-storage
   connections.
3. Document the exact clean-checkout prerequisites and the distinction between the safe build
   profile and real web/worker/scheduler configuration. State that the application loader remains
   fail-closed for missing, placeholder, malformed, conflicting, or production-capable inputs;
   do not document any usable secret or imply that build settings are deployment credentials.
4. Add focused regression coverage at the command/documentation boundary only if the repository's
   existing test conventions provide a stable way to invoke it. Prove that the default build path
   succeeds without external services, that a deliberately invalid configuration still exits
   non-zero before the frontend step, and that no fiscal transport or service connection is made.
5. Run the focused checks plus the repository validation suite, including `make build`, `make lint`,
   `make test-unit`, `make test-integration`, and `make smoke`. Treat any failure caused by the
   existing dirty working tree as evidence to isolate and report, not as permission to relax the
   configuration guard.
6. On completion, synchronize the P0-01/P0-03/P0-05 evidence in `IMPLEMENTATION_PLAN.md` and the
   completion note/checkbox in `specs/p0-project-foundation.md` according to their existing
   conventions, update development documentation, refresh Graphify with `graphify update .`,
   update this issue's Resolution, and close the complete change in one focused commit.

## In Scope

- The `make build` target's safe synthetic configuration contract and fail-fast command behavior.
- Documentation of clean-checkout build prerequisites, isolation, and the boundary between build
  validation and application runtime configuration.
- Focused regression evidence for no external service/fiscal transport access and continued
  fail-closed invalid configuration.
- Completion evidence in the owning P0 spec and implementation plan.

## Out of Scope

- Changing `nfx.infrastructure.configuration`, redaction, transport guards, or any boot policy.
- Adding real credentials, production endpoints, secret-manager integration, or new configuration
  names/precedence rules.
- Changing `.env.example` or resolving the exposed values/duplicates owned by issue 0007.
- Starting PostgreSQL/MinIO, applying migrations, changing Compose topology, or changing the
  frontend build itself.
- Reworking `make lint`, `make test-unit`, integration setup, smoke orchestration, dependencies,
  or unrelated documentation.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P1 “Correção do contrato de build” (completed, low risk).
- Canonical spec: `specs/p0-project-foundation.md` — P0-01/P0-03/P0-05, current repository
  version; especially the command contracts and the completed `make build` contract.
- Related spec: `specs/p0-safe-configuration-and-test-isolation.md` — P0-02/P0-04; its
  fail-closed configuration and zero-network guarantees remain authoritative.
- Related issue: `issues/0007_-_remove_literal-secrets-from-env-example.md`; no blocking
  dependency, but coordinate documentation edits to avoid conflicting claims about external
  secrets.
- Data/migration: none. No persistent state, schema, cursor, job, or artifact may be created by
  the build target.
- Security: synthetic values must be clearly non-production and must not be copied into tracked
  templates, logs, error output, or deployment instructions. The build must not broaden any
  allowlist or fiscal transport capability.
- Observability/rollout: command failures remain non-sensitive and non-zero; rollout is limited to
  developer/CI invocation documentation and the Make target.

## Tests

- **Focused:** invoke `make build` from a clean environment with no required external services and
  verify Django check plus frontend artifact creation; invoke the underlying check with missing or
  invalid required configuration and verify it fails before the frontend step.
- **Isolation/security:** use a spy or existing test boundary to prove no PostgreSQL, MinIO, DNS,
  HTTP, SOAP, or fiscal transport call occurs; scan changed documentation and command definitions
  for usable secret material and production destinations.
- **Repository validation:** run `make build`, `make lint`, `make test-unit`, `make test-integration`,
  and `make smoke` with the repository's existing synthetic test-profile setup.

## Acceptance Criteria

- [x] A clean checkout can run the documented `make build` command successfully with only the
  documented safe synthetic prerequisites, without manually exporting a usable secret.
- [x] The build command supplies no versioned secret, deployment credential, production endpoint,
  or newly invented configuration precedence rule.
- [x] `make build` performs the Django configuration/import check and frontend build in the stated
  order, fails fast on either step, and does not start services or apply migrations.
- [x] The build path makes no PostgreSQL, MinIO, DNS, HTTP/SOAP, or fiscal transport calls; no
  database, object, job, cursor, audit, or artifact state is created.
- [x] Missing, placeholder, malformed, conflicting, or otherwise invalid required configuration
  still fails closed with a non-zero result before any frontend build or external access.
- [x] Documentation distinguishes the synthetic build profile from runtime web/worker/scheduler
  configuration and keeps external secret provisioning/rotation requirements explicit.
- [x] Focused regression coverage proves the success, negative, ordering, and no-network
  behaviors without exposing synthetic values in logs, snapshots, or reports.
- [x] `make build`, `make lint`, `make test-unit`, `make test-integration`, and `make smoke` pass
  without weakening P0 configuration, redaction, isolation, or transport-guard guarantees.
- [x] `IMPLEMENTATION_PLAN.md`, `specs/p0-project-foundation.md`, development documentation,
  and Graphify are synchronized according to repository conventions.
- [ ] The issue is closed only after its Resolution records the implementation/evidence,
  `IMPLEMENTATION_PLAN.md` is synchronized, and all changes are committed in one focused commit.

## References

- Spec: `specs/p0-project-foundation.md` — command contracts and the completed `make build`
  contract.
- Spec: `specs/p0-safe-configuration-and-test-isolation.md` — fail-closed configuration,
  synthetic profiles, redaction, and zero-network guarantees.
- Plan: `IMPLEMENTATION_PLAN.md` — “Correção do contrato de build”.
- Current baseline: `Makefile` `build`, `lint`, and `test-unit` targets; `docs/DEVELOPMENT.md`
  command contract.

---

## Remaining Work

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- What was done, decisions made, and why. -->
<!-- Include: files modified, tests added, edge cases handled. -->

The implementation is complete in the working tree. `Makefile` now runs the Django
configuration/import check with the existing local synthetic `test` profile and hidden recipe-scoped
values, then runs the frontend build in fail-fast order. No services, migrations, external secrets,
production destinations, or fiscal transports were added.

Added `tests/unit/test_build_contract.py` covering a successful service-free build with Python socket
I/O blocked, invalid ambient configuration failing before a fake frontend command is reached, and
absence of synthetic values from normal build output. Updated `docs/DEVELOPMENT.md`,
`specs/p0-project-foundation.md`, `specs/README.md`, and `IMPLEMENTATION_PLAN.md` with the completed
contract and runtime-secret boundary.

Validation commands and results:

- `make build` — passed.
- `make lint` — passed.
- `make test-unit` — passed.
- `make test-integration` — passed.
- `make smoke` — passed.
- test-profile `python -m pytest tests/unit/test_build_contract.py` — 2 passed.

No migration was required. Graphify was refreshed with `graphify update .`.

The issue remains open because `IMPLEMENTATION_PLAN.md` and the P0 specification contain
substantial pre-existing uncommitted rewrites. Git cannot isolate the completion hunks from those
changes safely, so creating the required focused commit would also commit unrelated user work.
The next action is to commit this implementation and its directly related documentation from a
cleanly separated diff, then close the issue.
