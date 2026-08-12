# P9-04 hardening evidence and recovery runbook

This document is the redacted evidence record for issue `0031` and the P9-04
hardening slice. It covers the delivered simulator-only MVP baseline. It does not
claim production transport, a trusted CA, physical backup separation, disaster
recovery after host loss, or the unavailable P8 dashboard capabilities.

All identifiers and payloads in this document are synthetic references. No
credential, CNPJ, XML, PDF, certificate, endpoint response, or production log is
included.

## Evidence contract

Each matrix row records the asset or boundary, control, reproducible evidence,
severity, owner/spec, decision, and residual risk. `Pass` means the delivered
control was exercised by the cited test or ephemeral runbook. `Residual` means a
known limitation was deliberately retained and assigned to the affected pilot or
production decision; it is not treated as a successful control.

### Trust boundaries

| ID | Boundary and asset | Required control | Evidence and owner | Decision / residual risk |
|---|---|---|---|---|
| TB-01 | User/browser → HTTPS proxy; sessions, credentials, downloads | HTTPS, secure cookies, CSRF, throttling, server-side authorization | `tests/unit/test_identity.py`, `tests/unit/test_runtime_topology.py`; identity/runtime owners; SEC-001..006 | Pass. The MVP certificate is self-signed; trusted CA remains deferred. |
| TB-02 | Proxy → web process; HTTP request and error surface | Private application network, bounded forwarding, safe errors, no direct service exposure | `tests/unit/test_runtime_topology.py`, `scripts/p9_hardening.sh`; runtime owner; SEC-006/008 | Pass in the ephemeral topology. No external bind is used. |
| TB-03 | Web/worker/scheduler → PostgreSQL; jobs, leases, cursors, audit state | Durable transactions, row locks, lease ownership, monotonic cursor rules, bounded fields | `tests/unit/test_job_engine.py`, `tests/integration/test_jobs.py`, `tests/integration/test_ingestion.py`; jobs/collection owners; OPS-001/003/005 | Pass. PostgreSQL remains the MVP queue; HA/broker are deferred. |
| TB-04 | Application → MinIO/object store; originals and derived artifacts | Verified size/digest/MIME, pending-before-finalized lifecycle, reconciliation, no live-volume restore | `tests/integration/test_artifact_storage.py`, `tests/integration/test_backup_restore.py`; artifacts/backup owners; SEC-007/009, AC-016 | Pass for logical/object corruption and isolated validation. Same-host backup remains a residual. |
| TB-05 | Fiscal/OpenCNPJ response → application | Simulator-only allowlist, redirect validation, timeouts, bounded XML/MIME/payload handling | `tests/unit/test_safe_configuration.py`, `tests/unit/test_fiscal_simulators.py`, `tests/unit/test_nfe_followup.py`; adapters/configuration owners; SEC-008 | Pass for the simulator boundary. Real fiscal endpoints are out of scope. |
| TB-06 | Operator/backup set → isolated restore target | Restricted backup status, manifest/hash/decrypt checks, target guards, manual recovery | `tests/integration/test_backup_restore.py`, `docs/OPERATIONS.md`; backup owner; OPS-BKP-001..006 | Pass for isolated validation. Physical separation and host-loss recovery block the corresponding P9-05 evidence. |
| TB-07 | Role and job identity → document, ZIP, retention, and operations read/write paths | Re-authorize direct URLs and worker actions; audit bounded outcomes | `tests/integration/test_documents.py`, `tests/integration/test_exports.py`, `tests/integration/test_retention.py`, `tests/integration/test_dashboard_endpoint.py`; domain owners; SEC-005, AUD-006..010 | Pass. Future unavailable sources remain explicitly unavailable. |

### Threat matrix

| ID / threat | Asset / boundary | Control and evidence | Severity / decision | Owner / spec | Residual risk |
|---|---|---|---|---|---|
| THR-01 brute force, weak credential, and user enumeration | Identity / TB-01 | Equal invalid/unknown login response, keyed throttle, Argon2, and bootstrap tests in `test_identity.py` | High / Pass | Identity / `p1-authentication-sessions-and-rbac.md`, SEC-001/002 | No external identity provider or MFA in MVP. |
| THR-02 session theft, CSRF, insecure cookie, and HTTP interception | Session / TB-01/TB-02 | CSRF enforcement, opaque Secure/HttpOnly/SameSite cookie, expiry/revocation, HTTPS-only runtime topology | High / Pass | Identity/runtime / P1, P9-01, SEC-003/004/006 | Auto-signed certificate requires operator trust and remains an accepted MVP limitation. |
| THR-03 unauthorized direct URL, job, or download abuse | Documents, ZIPs, retention, operations / TB-01/TB-07 | Central RBAC and server-side reauthorization tests for documents, exports, retention, users, backups, and dashboard | High / Pass | Domain owners / P7, P8, P9-03, SEC-005 | No browser interaction runner is configured; HTTP contracts are the current evidence boundary. |
| THR-04 malicious upload, unsafe MIME/size, XML bomb, and external entities | XML/artifacts / TB-04/TB-05 | Bounded artifact stream, MIME/size checks, defused XML rendering, unsafe declaration rejection, synthetic fixtures | High / Pass | Artifacts/adapters/rendering / P1, P4, P7-03, SEC-007 | New parser/library versions require the same boundary tests. |
| THR-05 SSRF, redirect/DNS abuse, and unknown destination | Outbound transport / TB-05 | Fail-closed destination parser, explicit allowlist, every redirect revalidated, sender not called on rejection | High / Pass | Configuration/adapters / P0, SEC-008 | Real DNS/transport behavior is intentionally not exercised. |
| THR-06 altered payload, object hash/size divergence, and corruption | Original/derived object / TB-04 | Finalization verifies digest/size/MIME; read and reconciliation reject missing/divergent objects without deleting evidence | Critical / Pass | Artifacts / P1, AC-004/016 | Physical storage media integrity is delegated to MinIO/host operations. |
| THR-07 replay, lost cursor, stale lease, and duplicate logical result | Jobs, cursor, document identity / TB-03 | Idempotency keys, `SKIP LOCKED`, owner-bound leases, cursor advancement only after treatment, replay/conflict state tests | Critical / Pass | Jobs/collection/documents / P3/P4, AC-006/007/017/024 | Cross-host clock/DB failure remains an operational concern covered by the runbook. |
| THR-08 certificate or secret leakage | A1 material, logs, errors, audit, backup / all boundaries | Envelope encryption, external secret files, recursive redaction, safe job/audit payload validation, backup probe validation | Critical / Pass | Identity/certificates/audit/backup / P1/P2/P9-02, SEC-007/009 | Master key custody is external to the repository and backup archive. |
| THR-09 traversal, unsafe ZIP entry, archive overflow, and download abuse | ZIP and filenames / TB-01/TB-04/TB-07 | Bounded filters/items/bytes, deterministic safe filenames, verified source before archive, partial/failure states preserve origin | High / Pass | Exports/documents / P8-01, AC-012 | ZIP browser UX is not separately automated. |
| THR-10 source outage, timeout, cooldown, unknown payload, and conflict | Fiscal state and originals / TB-05/TB-03 | Explicit unavailable/retry/cooldown/unknown/quarantine/conflict states; original and evidence preserved; no false empty result | High / Pass | Adapters/collection/documents / P4/P5/P6, AC-004/006/018/024 | Official endpoints and homologation are external blockers. |
| THR-11 ransomware, delayed backup, and host loss | Backup set and live volumes / TB-04/TB-06 | Verifiable manifest, independent retention, isolated target guard, manual restore procedure, safe delayed/failure status | Critical / Residual by design | Backup/operations / P9-02, OPS-BKP-001..006, AC-016 | Backup is same-host in the MVP; physical separation and host-loss recovery remain a P9-05/production gate. |

## Architecture §40 failure evidence

| Failure | Safe invariant | Evidence / result |
|---|---|---|
| Web restart | Sessions expire/revoke; durable jobs remain | `tests/unit/test_runtime_topology.py`, `scripts/p9_hardening.sh`; ephemeral web restart and health check pass. |
| Worker death/restart | Lease expiry allows recovery; old owner cannot complete | `test_claim_renew_complete_and_stale_owner_rejection_are_atomic`, `test_expired_lease_is_reclaimed...`, `test_idempotent_handler_effect_survives_worker_death...`; pass. |
| Scheduler death/restart | Persisted schedule/recovery remains separate from fiscal execution | `test_scheduler_loop_stops_without_touching_a_fiscal_handler`, runtime ephemeral restart; pass. |
| Database unavailable | No cursor/progress or job success is reported | `test_database_error_does_not_report_unsafe_progress`, ingestion failure matrix; pass. |
| MinIO/object store unavailable | Pending/original state is retained; no false finalization | `test_limit_interrupted_upload_and_outage_leave_a_retryable_pending_reference`, new P9 outage test; pass. |
| Fiscal source unavailable | Unavailable/retry/cooldown is not valid empty | collection execution and ingestion failure matrix tests; pass. |
| Invalid certificate | Flow blocks without an unbounded retry loop | certificate lifecycle and policy tests; pass. |
| Unknown payload | Original/quarantine/result-incomplete evidence remains | document and ingestion unknown/quarantine tests; pass. |
| Conflict | Existing evidence is preserved and no overwrite occurs | document replay/conflict and artifact conflict tests; pass. |
| Interrupted PDF renderer | XML/source remains available; derived state is explicit and retryable | document rendering failure/idempotency tests; pass. |
| Interrupted ZIP | Partial/failed state is explicit and source remains intact | `test_export_missing_source_is_explicit_partial_and_never_complete`; pass. |
| Disk full | Backup is failed/partial, prior set remains, and health reports failure | new P9 disk-full test using synthetic `insufficient_space`; pass. |
| Backup delayed/failed | Admin sees failure/age; no secret or path disclosure | backup status integration tests and new failed-capture assertion; pass. |
| Host lost | Recovery is limited to the local backup and is not overstated | P9-02 runbook and architecture decision; residual, intentionally not closed by P9-04. |

## Security and observability canaries

The tests use synthetic values such as `synthetic-secret-canary` and
`synthetic-original`. Assertions cover the JSON formatter, audit context, job
payload/result validation, backup manifest, API safe errors, and UI/operations
responses. The committed evidence contains only safe error codes, opaque IDs,
bounded counts, hashes, and proposed measurements. Metric labels are finite
state/outcome values; company and user identifiers are not metric dimensions.

## Synthetic capacity exercise

`tests/integration/test_p9_hardening.py` persists 200 synthetic companies, three
synthetic users, 400 enabled flows, and 400 durable jobs. Four bounded worker
threads claim and complete the jobs through the production `JobEngine` boundary.
The test asserts that all jobs complete, every logical target has one result, and
no artificial company or user cap is configured. The output is a measured
`P9_CAPACITY_EVIDENCE` line with elapsed milliseconds.

The measurement is **Proposed**, environment-specific evidence, not an SLA. It
does not add a product limit. P9-01 resource limits remain the configured
runtime values in `docker-compose.runtime.yml`.

## Ephemeral runbook

Run the focused persistence/fault evidence in an isolated PostgreSQL/MinIO
project:

```sh
bash scripts/p9_hardening.sh
```

The script uses only `docker-compose.test.yml`, a unique synthetic bucket, and
temporary Compose volumes. It migrates the ephemeral database, runs the
capacity/fault tests, starts web/worker/scheduler, checks liveness/readiness,
restarts each process, and checks process evidence. It removes only that
ephemeral project on exit.

For the broader contract suites, run:

```sh
make lint
make test-unit
make test-integration
make build
make smoke
```

If the runner lacks Docker or its ephemeral services, record the command as
unavailable rather than substituting a production database, MinIO bucket, secret,
or endpoint.

## Findings and release decision

No new critical implementation defect was found in the delivered contracts.
The two material residuals are known and explicitly bounded: same-host backup
does not prove physical separation/host-loss recovery, and the runtime uses an
auto-signed certificate. They block only the corresponding P9-05 or production
scope and are not reported as closed here. Official fiscal transports and the
unavailable P8 source capabilities remain outside this hardening increment.

## Validation record

Observed on 2026-08-11 in the repository workspace:

| Command | Result |
|---|---|
| `bash scripts/p9_hardening.sh` | Pass. Focused P9 tests `2 passed`; capacity `companies=200 users=3 flows=400 jobs=400 workers=4 elapsed_ms=1271 company_limit=none user_limit=none threshold_classification=proposed`; ephemeral web/worker/scheduler restart and health checks passed. |
| `make lint` | Pass. Ruff, mypy (`111 source files`), TypeScript, and ESLint passed. |
| `make test-unit` | Pass. `286 passed`; one existing `botocore` `datetime.utcnow()` deprecation warning. |
| `make test-integration` | Pass. `108 passed`; seven existing `botocore` `datetime.utcnow()` deprecation warnings. |
| `make build` | Pass. Django system check and Vite production build passed. |
| `make smoke` | Pass. Ephemeral PostgreSQL/MinIO web/worker/scheduler smoke completed successfully. |

The Compose runner also reports that the local Docker installation lacks the
Buildx plugin; it does not affect the successful test/build results. No command
used production data, credentials, endpoints, or persistent non-ephemeral
volumes. The capacity measurement remains Proposed and is not an accepted
throughput target.
