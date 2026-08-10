---
id: 0007
title: "Remove literal secrets from the environment template"
type: bug
status: closed
priority: critical
phase: P0
created_at: 2026-08-09
updated_at: 2026-08-09
closed_at: 2026-08-09
related_issues: []
blocked_by: []
affects:
  - .env.example
  - docs/
  - tests/unit/
  - scripts/
---

## Description

The current working-tree version of `.env.example` contains literal values for `NFX_SECRET_KEY` and `NFX_CERTIFICATE_MASTER_KEY`, despite the safe-configuration contract requiring secrets to remain external to the repository. The template also duplicates existing configuration entries, increasing the chance that a copied environment silently uses the wrong value. The implementation and tests already enforce fail-closed configuration; this issue is limited to restoring the template/documentation contract and proving that no secret-like value is reintroduced.

This is the uncovered P0 “Higiene de template de ambiente” item in `IMPLEMENTATION_PLAN.md`, recorded there as a blocker for the current tree. If either value has been used outside local disposable testing, treat it as potentially compromised and rotate it through the external secret-management process; rotation itself is outside this repository change.

## Objective and Expected Outcome

Make the checked-in environment template safe to copy: it contains only non-secret examples, explicit placeholders/instructions for externally supplied secrets, and one authoritative entry per setting. A clean configuration setup continues to require `NFX_PROFILE`, `NFX_SECRET_KEY` or its mounted file alternative, and `NFX_CERTIFICATE_MASTER_KEY` or its mounted file alternative, while invalid or placeholder secrets still fail before boot or network access.

## Implementation Plan

1. Compare the template with the canonical configuration contract in `specs/p0-safe-configuration-and-test-isolation.md` and the current development setup. Remove literal secret material and duplicate/conflicting entries, retain safe local endpoints and simulator values, and use a clearly invalid placeholder plus concise external-secret instructions where a value is required. Do not weaken fail-closed validation or add a versioned certificate key.
2. Verify the resulting template against the configuration loader’s precedence and validation rules. The documented variable/file alternatives must remain mutually exclusive as specified, and copying the template must not make a development or test process appear configured with a usable secret unless the operator supplies one externally.
3. Add or adjust focused validation that scans the template for the known secret names and representative secret-like values, confirms required placeholders/instructions are present, and proves the existing boot-failure and no-network guarantees remain intact. Keep fixtures synthetic and avoid embedding a value that could be accepted as a real secret.
4. Update the development configuration instructions only where needed to match the corrected template and explain external secret provisioning and rotation responsibility. Do not change application configuration behavior, Compose exposure, fiscal destinations, migrations, or production credentials.
5. On completion, synchronize the P0 hygiene item’s evidence/status in `IMPLEMENTATION_PLAN.md` according to its existing conventions, update the relevant safe-configuration documentation/spec evidence only as appropriate, refresh Graphify with `graphify update .`, update this issue’s Resolution, and close the work in one focused commit.

## In Scope

- Removal of literal `NFX_SECRET_KEY` and `NFX_CERTIFICATE_MASTER_KEY` values from the checked-in environment template.
- Reconciliation of duplicate template settings and safe placeholder/instruction text.
- Focused regression checks for secret absence, fail-closed configuration, and zero fiscal-network access on invalid setup.
- Small, directly related development-documentation corrections and completion evidence.

## Out of Scope

- Rotating or revoking any secret outside the repository.
- Changing the typed configuration loader, redaction implementation, boot guards, Compose networking, fiscal adapters, or transport allowlists.
- Introducing a secret manager, changing secret names or precedence, weakening placeholder rejection, or adding real credentials.
- P3/P4 implementation, migrations, frontend changes, or unrelated cleanup.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P0 “Higiene de template de ambiente” (completed by this issue).
- Canonical spec: `specs/p0-safe-configuration-and-test-isolation.md` — P0-02/P0-04, current repository version; especially the secret-exclusion, fail-closed, and no-network contracts.
- Related implementation baseline: `backend/nfx/infrastructure/configuration.py`, the central redaction/transport guards, and their existing safe-configuration tests. Do not alter these contracts unless a focused regression demonstrates that the template change exposes a defect.
- Data/migration: none.
- Security: assume exposed literal values may be compromised and document external rotation responsibility; never print or reproduce them in test output, logs, docs, or the issue resolution.
- Rollout: update local/development environment provisioning after the template is corrected; no production rollout is performed by this issue.

## Tests

- **Focused unit/configuration:** template secret absence, safe placeholders/instructions, duplicate-setting detection, placeholder/absence boot rejection, and external-file/variable precedence.
- **Security regression:** redaction fixtures remain free of the template’s literal values and invalid configuration performs zero fiscal transport calls.
- **Repository validation:** run the focused tests, `make lint`, `make test-unit`, the configured `make build`, and `make smoke`; use the repository’s required test-profile variables rather than committing secrets.

## Acceptance Criteria

- [x] `.env.example` contains no literal or usable value for `NFX_SECRET_KEY` or `NFX_CERTIFICATE_MASTER_KEY`, and no duplicate/conflicting definition of either setting.
- [x] The template documents external provisioning for both secrets, including the supported variable-versus-mounted-file contract, without exposing secret material.
- [x] Safe simulator, local endpoint, and profile examples remain usable for development/test setup, while no example enables a production fiscal destination or transport.
- [x] Configuration tests prove absent, placeholder, malformed, and mutually conflicting secret inputs fail closed before network access or state persistence.
- [x] Configuration tests prove valid synthetic secrets supplied through each supported external mechanism continue to pass, with no secret values emitted in errors, logs, snapshots, or test reports.
- [x] A regression check detects reintroduction of literal secret-like template values and duplicate configuration entries without depending on the currently exposed values.
- [x] `make lint`, `make test-unit`, configured `make build`, and `make smoke` pass without weakening existing safe-configuration, redaction, or zero-fiscal-network guarantees.
- [x] Development documentation and the P0 plan/spec evidence are synchronized according to repository conventions, and `graphify update .` completes with the issue represented in the repository graph as required.
- [x] The issue is closed only after its Resolution records the evidence, `IMPLEMENTATION_PLAN.md` is synchronized, and the complete change is committed as one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P0 environment-template hygiene and safe-configuration decisions.
- Spec: `specs/p0-safe-configuration-and-test-isolation.md` — P0-02/P0-04.
- Documentation: `docs/DEVELOPMENT.md` — secure configuration and isolated fiscal setup.

---

## Resolution

<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- What was done, decisions made, and why. -->

Implemented the P0 environment-template hygiene correction without changing the fail-closed
configuration loader. Removed the duplicated settings block containing the exposed secret-like
values from `.env.example`, leaving one invalid external placeholder per secret, the mounted-file
alternatives, and the simulator-only local fiscal settings. Added regression coverage for template
uniqueness/placeholders, missing and malformed inputs, valid environment/file sources, conflicting
sources, and the existing zero-network rejection boundary. Updated the development guide, safe
configuration spec, specs index, and implementation plan; no migration was needed. Ran `graphify
update .` successfully.

Validation completed:

- `python -m pytest tests/unit/test_safe_configuration.py` — 28 passed.
- `make lint` — Ruff, mypy, TypeScript, and ESLint passed.
- `make test-unit` — 121 passed.
- Configured synthetic-profile `make build` — Django check and Vite build passed.
- `make smoke` — isolated PostgreSQL/MinIO smoke and web/worker/scheduler startup passed.

The change preserves the documented external rotation responsibility for any value used outside
disposable local testing.
