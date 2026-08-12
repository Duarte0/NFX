---
id: 0033
title: "Allow secure external bootstrap administrator provisioning"
type: bug
status: closed
priority: high
phase: P0
created_at: 2026-08-11
updated_at: 2026-08-12
closed_at: 2026-08-12
related_issues: [0007]
blocked_by: []
affects:
  - backend/nfx/infrastructure/configuration.py
  - backend/nfx/management/commands/bootstrap_admin.py
  - backend/nfx/identity/
  - tests/unit/
  - tests/integration/
  - docs/
---

## Description

The approved bootstrap service is implemented and its direct Django tests cover idempotency,
Argon2id, rerun behavior, and non-echoed output, but the command cannot currently be used from a
fresh process. `backend/nfx/management/commands/bootstrap_admin.py` reads
`NFX_BOOTSTRAP_ADMIN_PASSWORD`, while Django imports `nfx.settings` and calls
`load_settings()` before dispatching the command; `load_settings()` rejects that variable as an
unknown `NFX_*` setting. The result is an operational P0 failure at the configuration/command
boundary, not a missing identity model or authentication contract.

## Objective and Expected Outcome

Make `python backend/manage.py bootstrap_admin` accept one valid externally supplied bootstrap
secret in the bootstrap process, create the approved initial Administrator when the user base is
empty, and remain safe and idempotent on rerun. The global NFX configuration allowlist remains
fail-closed, and the bootstrap secret is never part of public settings or accepted by web, worker,
or scheduler processes.

## In Scope

- The process-boundary contract between Django configuration loading and the `bootstrap_admin`
  management command.
- Validation of the external bootstrap secret for absence, empty values, placeholders, and
  unsupported or ambiguous configuration, with safe non-zero failures.
- Preservation and verification of the existing approved administrator identity, Argon2id
  password storage, empty-user-base guard, idempotent rerun, and concurrent first-run behavior.
- Focused fresh-process/configuration tests, bootstrap command tests, redaction checks, and
  regression coverage proving ordinary process boot and authentication contracts remain intact.
- Small runtime/development documentation updates describing how the secret is supplied for the
  one-time command and that it is not a runtime application setting.

## Out of Scope

- Changing the secret name, adding a versioned secret, secret-manager integration, a new admin API,
  user email/name/role, password hashing policy, sessions, cookies, RBAC, audit policy, or login
  behavior.
- Weakening rejection of unknown `NFX_*` variables, placeholder rejection, external-secret
  precedence, redaction, or fail-closed boot for ordinary processes.
- Accepting the bootstrap secret in web, worker, or scheduler configuration, persisting it in
  `Settings`, the database, audit records, logs, HTTP responses, tracebacks, fixtures, or tracked
  documentation.
- New migrations, changes to identity schema, fiscal transports, deployment topology, frontend
  behavior, or unrelated configuration cleanup.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — **Bootstrap de Administrador**, the remaining P0
  configuration/operational gap. The plan records this as an independently prioritized follow-up;
  it is not covered by the P0 frontend delivery issue `0032`.
- Canonical spec: `specs/p0-bootstrap-admin-provisioning.md`, v1.1. Its contract and four
  acceptance statements govern the command-only secret, global allowlist, safe failures, and
  bootstrap idempotency/uniqueness.
- Supporting specs: `specs/p0-safe-configuration-and-test-isolation.md` (P0, completed) and
  `specs/p1-authentication-sessions-and-rbac.md` (P1, completed; its 2026-08-11 delta identifies
  this exact fresh-process incompatibility). Issue `0007` is related because it establishes the
  external-secret/template boundary; it does not block this issue.
- Verified current gap: `KNOWN_NFX_KEYS` in `backend/nfx/infrastructure/configuration.py` does
  not include the bootstrap variable, `load_settings()` rejects unknown `NFX_*` names before the
  command runs, and the existing `test_bootstrap_command_reads_external_secret_without_echoing_it`
  invokes the command only inside an already initialized Django test process.
- Data/migration: none expected. The change must use the existing identity tables and constraints;
  no secret, bootstrap marker, or new durable state is introduced.
- Security: the accepted secret exists only in the environment/secret manager of the process that
  invokes the command. Safe errors must identify the rejected field/class without reproducing its
  value. A typo such as another unknown `NFX_*` name must still fail closed.
- Compatibility/rollout: `web`, `worker`, and `scheduler` retain their current configuration
  contract and must not become dependent on the bootstrap secret. Runtime provisioning should run
  the command once against the existing database before starting normal application processes.

## Implementation Plan

1. Trace the current management-command boot path through `nfx.settings` and
   `load_settings()` and establish a command-only way for the approved bootstrap variable to be
   recognized at the boundary without adding it to `PublicSettings`, `SecretSettings`, or any
   ordinary process configuration. Preserve the existing global unknown-NFX rejection and do not
   infer a bootstrap mode from a missing or invalid profile.
2. Enforce the v1.1 bootstrap input contract: a valid externally supplied value is available only
   to `bootstrap_admin`; absent, empty, placeholder, unsupported, or ambiguous input exits
   non-zero with a stable safe message. Keep the secret out of command output, configuration
   representations, logging/audit paths, HTTP responses, tracebacks, fixtures, and test reports.
3. Reuse the existing `bootstrap_first_administrator` owner and preserve its invariants: only the
   approved initial Administrator may be created while the user table is empty; reruns return the
   existing account without changing its password; a pre-existing different user base is not
   modified; and simultaneous first runs cannot create more than one account or report a false
   successful creation. Do not broaden this issue into identity or RBAC changes.
4. Add process-level tests with a clean synthetic environment that distinguish the successful
   bootstrap command from normal web/worker/scheduler startup. Cover the allowlist matrix, safe
   missing/placeholder/ambiguous failures, output/traceback/log redaction, first run, rerun,
   existing-user rejection, and concurrent first run. Keep all credentials and identities
   synthetic except for the command contract's already approved target, and avoid external fiscal
   or service calls.
5. Update the runtime/development provisioning instructions and the P0 spec/index evidence only
   as needed to describe the verified command-only secret boundary. On completion, refresh
   Graphify, synchronize the bootstrap status in `IMPLEMENTATION_PLAN.md`, update this issue's
   Resolution, and close the work in one focused commit.

## Tests

- **Focused configuration/command:** `tests/unit/test_safe_configuration.py` and
  `tests/unit/test_identity.py`, extended or supplemented with a subprocess/fresh-settings test
  for `bootstrap_admin` and the ordinary process matrix.
- **Persistence/concurrency:** PostgreSQL-backed synthetic tests for first-run uniqueness,
  idempotent rerun, existing-user protection, and concurrent invocations; no new migration is
  expected, so verify the current schema remains sufficient.
- **Security/isolation:** assert the secret is absent from stdout/stderr, exception text, logs,
  audit records, settings objects, fixtures, and reports; assert ordinary process startup remains
  fail-closed or unaffected according to its existing configuration and makes no fiscal/network
  call.
- **Repository validation:** run the focused tests plus `make lint`, `make test-unit`,
  `make test-integration`, the configured `make build`, and `make smoke` with synthetic test
  configuration only.

## Acceptance Criteria

- [x] A fresh-process invocation of `python backend/manage.py bootstrap_admin` succeeds with one
  valid externally supplied `NFX_BOOTSTRAP_ADMIN_PASSWORD` and is not rejected as an unknown NFX
  setting.
- [x] The bootstrap secret is command-only: it is not represented in public/ordinary settings,
  persisted, logged, audited, returned over HTTP, exposed in tracebacks, or accepted as a required
  input by web, worker, or scheduler processes.
- [x] Unknown or misspelled `NFX_*` variables remain rejected fail-closed, and absent, empty,
  placeholder, unsupported, or ambiguous bootstrap input fails with a non-zero result and a safe
  message that contains neither the supplied value nor secret-derived data.
- [x] The first successful bootstrap creates only the approved Administrator with the existing
  Argon2id contract; it creates no duplicate, fiscal call, unrelated audit/state record, or new
  migration artifact.
- [x] Rerunning bootstrap is idempotent: it reports the existing account without replacing its
  password or changing unrelated user state.
- [x] A non-empty user base that does not contain the approved bootstrap account is rejected
  without mutation, and concurrent first-run attempts leave at most one approved Administrator
  with no false success or leaked database error.
- [x] Existing authentication, session, cookie, RBAC, redaction, and fail-closed configuration
  behavior remains unchanged and is covered by the relevant regression tests.
- [x] Tests use synthetic secrets/fixtures, cover positive and negative process boundaries,
  idempotency, concurrency, redaction, and no-network behavior, and pass without relying on a
  production endpoint or credential.
- [x] `make lint`, `make test-unit`, `make test-integration`, configured `make build`, and
  `make smoke` pass, together with the focused bootstrap/configuration checks.
- [x] Runtime/development documentation, the P0 bootstrap spec/index, `IMPLEMENTATION_PLAN.md`,
  and Graphify metadata are synchronized before closure.
- [x] The issue is closed only after its Resolution records the evidence, the implementation-plan
  sync is recorded, and all changes are committed in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — “Bootstrap de Administrador”.
- Canonical spec: `specs/p0-bootstrap-admin-provisioning.md` — v1.1.
- Supporting specs: `specs/p0-safe-configuration-and-test-isolation.md` and
  `specs/p1-authentication-sessions-and-rbac.md` (especially the documented 2026-08-11 delta).
- Related issue: `issues/0007_-_remove_literal-secrets-from-env-example.md`.
- Current components: `backend/nfx/infrastructure/configuration.py`,
  `backend/nfx/management/commands/bootstrap_admin.py`,
  `backend/nfx/identity/services.py`, and the existing configuration/identity tests.

---

## Resolution

Implemented the command-only bootstrap configuration boundary and closed the fresh-process gap.
`load_settings()` keeps the normal `KNOWN_NFX_KEYS` allowlist fail-closed and accepts
`NFX_BOOTSTRAP_ADMIN_PASSWORD` only when Django is importing settings for the explicit
`bootstrap_admin` management command; the password is not stored in `Settings` or process
configuration. The command now rejects missing, blank, and `CHANGE_ME` placeholder values with
safe errors and rejects unsupported `*_FILE`/misspelled NFX variables through the normal allowlist.

The existing `bootstrap_first_administrator` service remains the owner of identity invariants and
now serializes the empty-user check with a PostgreSQL transaction advisory lock. Integrity races
are converted to an idempotent unchanged result or a fixed safe failure, so first-run concurrency
cannot create duplicates or expose a database traceback. No migration, schema, authentication,
session, cookie, RBAC, audit, or fiscal transport behavior changed.

Files added/updated for this issue:

- `backend/nfx/infrastructure/configuration.py`, `backend/nfx/settings.py`, and
  `backend/nfx/management/commands/bootstrap_admin.py` implement the boundary and safe command
  validation.
- `backend/nfx/identity/services.py` adds the concurrency guard and safe race handling.
- `tests/unit/test_bootstrap_process.py`, `tests/unit/test_safe_configuration.py`, and
  `tests/unit/test_identity.py` cover fresh processes, ordinary process rejection, redaction,
  invalid inputs, rerun/password preservation, existing-user protection, and concurrent first run.
- `docs/DEVELOPMENT.md`, `docs/RUNTIME.md`, `specs/p0-bootstrap-admin-provisioning.md`,
  `specs/README.md`, and `IMPLEMENTATION_PLAN.md` document and index the completed contract.

Validation completed with synthetic configuration in the pinned test environment:

- `make lint`: Ruff, mypy across 111 files, TypeScript, and ESLint passed.
- `make test-unit`: 307 passed (5 existing botocore deprecation warnings).
- `make build`: Django system check and Vite build passed.
- `make test-integration`: 108 passed; `make smoke`: passed with all three runtime processes.
- `graphify update .`: completed with 3,417 nodes and 9,035 edges; Graphify reported two existing
  zero-node files (`hooks.json`, `pyproject.toml`) and refreshed the code graph.
