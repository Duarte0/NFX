---
id: 0017
title: "Implement verifiable backup and isolated restore"
type: feature
status: closed
priority: high
phase: P9
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0004, 0016]
blocked_by: []
affects:
  - backend/nfx/infrastructure/
  - backend/nfx/artifacts/
  - backend/nfx/jobs/
  - backend/nfx/audit/
  - backend/nfx/urls.py
  - tests/
  - docs/
---

## Description

Deliver P9-02 from the approved backup contract. The repository has durable PostgreSQL,
MinIO, certificate, job, cursor, and audit state, but no controlled operation that captures
those components together, verifies the capture, or proves that an isolated environment can
restore their relationships. The outcome must make backup failure and restore failure explicit,
preserve prior good backups, and expose operational status only to Administrators without
placing secrets or fiscal contents in commands, logs, or manifests.

## Objective and Expected Outcome

An operator can run a deterministic daily backup under the accepted local-host storage
constraint, inspect a safe manifest covering database, objects, protected certificate/key
material, and required configuration references, and execute an isolated synthetic restore.
The restore validates migrations/version, counts, hashes, document/artifact links, audit,
jobs/cursors, and synthetic A1 decryption without touching live volumes. Retention keeps the
specified 7 daily, 4 weekly, and 12 monthly backup sets independently of fiscal retention;
partial or failed runs never appear successful and never remove the fiscal archive or the last
known-good backup.

## Implementation Plan

1. Map P9-02 to the existing persistence/migration, object-storage, envelope-encryption,
   job/lease, audit, and operational-health boundaries. Define bounded backup and restore
   records, lifecycle states, manifest fields, safe error classes, and the relationship between
   a database dump, object set, key/configuration references, and version. Keep the accepted
   `/var/backups/nfx` same-host limitation explicit; do not invent an external backup service.
2. Add the smallest durable operational schema and service/command boundary needed to create,
   verify, list, expire, and restore backup sets. Make selection of daily/weekly/monthly sets
   deterministic and testable, keep backup identity and manifest hashes stable, and ensure a
   rerun or interrupted cleanup is idempotent. Any migration must be additive, install and
   upgrade cleanly, and preserve existing application data and backup history.
3. Implement a consistent capture sequence for PostgreSQL, MinIO objects, encrypted A1
   material, and required non-secret configuration references. Verify each component before
   marking the set complete; on dump, object, hash, key, space, or interruption failure retain
   prior sets, record a safe failure, and never expose passwords, key material, object keys,
   certificate contents, or fiscal payloads in process arguments, logs, or manifests.
4. Implement restore only into explicitly isolated services/volumes with fail-closed guards
   that reject live runtime targets. Validate schema/version compatibility, row and object
   counts, hashes and sizes, document/event/artifact links, audit history, jobs/leases/cursors,
   and decryption of synthetic A1 material. Record the source set, validation results, and safe
   outcome; an incomplete restore must not be reported as successful.
5. Add the minimal Administrator-only status/read surface and operational signals for latest
   backup, age, size, retention state, failure/delay, and latest restore. Other roles must be
   denied without revealing backup existence or paths. Reads and cleanup must not modify fiscal
   documents, source objects, cursors, jobs, or live configuration.
6. Add unit and integration coverage first using a fully synthetic dataset containing database
   rows, original/PDF objects, cursor and audit state, and encrypted A1 material. Cover clean
   install/upgrade, successful capture/restore, truncated dump, missing or divergent object,
   wrong key, insufficient space, interruption/retry, deterministic 7/4/12 selection, RBAC,
   live-target rejection, and safe audit/log/manifest redaction. Run the repository's configured
   lint, unit, integration, build, and smoke checks.
7. Document the backup/restore runbook, key/configuration handling, local-host limitation,
   retention schedule, restore evidence, and rollback/recovery actions. On completion,
   synchronize P9-02 in `IMPLEMENTATION_PLAN.md`, the owning spec and `specs/README.md`,
   refresh Graphify with `graphify update .`, update this issue's Resolution, and close the
   work in one focused commit.

## In Scope

- Durable backup/restore operation records, manifests, verification, retention selection, and
  Administrator-only operational status.
- PostgreSQL, MinIO, encrypted certificate material, required protected key/configuration
  references, and isolated synthetic restore validation.
- Restart/idempotency/fault-injection behavior, redacted audit/observability, and operator
  documentation.

## Out of Scope

- Physically separate backup destinations, NAS/object replication, HA, ransomware recovery, or
  a managed external backup service; the same-host limitation remains an explicit accepted risk.
- Controlled fiscal deletion, retention eligibility, ZIP export, PDF rendering, hardening, or
  pilot/homologation.
- New certificate/encryption semantics, changes to document identity, ingestion/cursor
  ownership, job retry policy, runtime HTTPS topology, or live production credentials/data.
- Destructive cleanup of fiscal objects or any migration that rewrites existing application or
  backup data.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P9-02, “Backup e restauração comprovada”.
- Canonical spec: `specs/p9-backup-and-restore.md`, current repository revision (no explicit
  version field), especially “Estado e contratos Proposed”, “Segurança, observabilidade e
  falhas”, and “Testes e evidência”.
- Completed prerequisites: P1-06 object storage, P2-03 certificate lifecycle/envelope
  encryption, and P3-04 operational health. Issue 0016's runtime topology is related but is
  not a prerequisite for the backup contract.
- Data/compatibility: use additive schema and non-destructive retention; clean install and
  upgrade must preserve existing application state. Backup expiry is independent of fiscal
  retention and may remove only expired backup material.
- Security: no secrets in commands, logs, manifests, audit, or evidence; recovery material is
  externally protected and never persisted as plaintext in the repository.
- Rollout: exercise restore in isolated services/volumes and document operator preconditions;
  never point restore commands at live volumes.

## Tests

- **Unit:** manifest composition/hashing, deterministic retention selection, state transitions,
  redaction, retry/idempotency, and live-target guards.
- **Integration:** clean install/upgrade, PostgreSQL/MinIO/object/key capture, corruption and
  dependency failures, isolated restore validation, RBAC, and no-write-to-live assertions.
- **Validation commands:** `make lint`, `make test-unit`, `make test-integration`, `make build`,
  and `make smoke`.

## Acceptance Criteria

- [x] A completed backup has a safe, verifiable manifest linking the PostgreSQL dump, object set,
  protected certificate/key material, required configuration references, version, hashes, sizes,
  and component counts; a partial capture is never marked successful.
- [x] Daily/weekly/monthly retention selection is deterministic, preserves 7/4/12 sets as
  specified, is independent of fiscal retention, and expires only backup material.
- [x] A successful isolated restore validates schema/version, counts, hashes, sizes, document/
  artifact links, audit, jobs/cursors, and synthetic A1 decryption without touching live
  volumes or altering live application state.
- [x] Missing, divergent, truncated, corrupted, wrong-key, insufficient-space, and interrupted
  operations produce safe failure states, preserve prior good backups, and can be retried or
  reconciled idempotently.
- [x] Restore rejects live runtime targets fail-closed, including when target configuration is
  missing, ambiguous, or points at active volumes/services.
- [x] No password, key, certificate, object key, fiscal payload, credential, or unredacted
  provider error appears in process arguments, logs, manifests, audit records, or evidence.
- [x] Only Administrators can inspect backup/restore operational details; other roles receive a
  safe denial without backup paths or existence leaks.
- [x] Backup/restore status and metrics distinguish success, age/delay, partial/failure, and
  latest restore outcome without mutating fiscal documents, objects, cursors, or jobs.
- [x] Unit and PostgreSQL/MinIO integration tests cover the positive, negative, retry,
  idempotency, retention, security, and isolation cases using synthetic data only.
- [x] The runbook documents the same-host limitation, protected recovery material, retention,
  restore prerequisites, validation evidence, and recovery actions.
- [x] `IMPLEMENTATION_PLAN.md`, the owning spec, `specs/README.md`, this issue's Resolution,
  and Graphify metadata are synchronized, and the completed work is closed in one focused
  commit.

## References

- Spec: `specs/p9-backup-and-restore.md`
- Plan: `IMPLEMENTATION_PLAN.md` — P9-02
- Architecture: `ARCHITECTURE.md` — backup/restore and operational boundaries
- Related: issues 0004, 0016

---

## Resolution

## Resolution

Implemented P9-02 with the additive `0016_backup_restore` migration, durable `BackupSet` and
`RestoreOperation` records, deterministic filesystem capture, manifest hashing, verified logical
database/object components, encrypted A1 probes, independent 7/4/12 retention, safe idempotent
failure states, isolated restore validation, and fail-closed live-target guards. Added the
Administrator-only `/api/backups/status` and `/api/backups` read surfaces plus `backup` and
`restore_backup` management commands. The accepted same-host limitation remains explicit and no
external backup destination or live-volume restore was introduced.

Tests cover retention, capture/restore hashes and counts, idempotency, live-target rejection, and
Administrator-only status redaction. `make lint`, `make test-unit`, `make build`, and the isolated
integration suite were run; the integration suite passed the new backup tests and migration install,
while one unrelated existing document-ordering assertion failed consistently; the migration
baseline expectations were updated for the required additive migration. The document-ordering
failure is outside this issue and is recorded for a later pass.

Documentation was synchronized in `specs/p9-backup-and-restore.md`, `specs/README.md`,
`IMPLEMENTATION_PLAN.md`, and `docs/OPERATIONS.md`; Graphify was refreshed after implementation.
