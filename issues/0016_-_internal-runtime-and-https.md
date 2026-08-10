---
id: 0016
title: "Deliver the internal HTTPS runtime topology and service isolation"
type: feature
status: closed
priority: high
phase: P9
created_at: 2026-08-10
updated_at: 2026-08-10
closed_at: 2026-08-10
related_issues: [0001, 0004, 0008]
blocked_by: []
affects:
  - docker-compose.app.yml
  - Dockerfile
  - backend/nfx/infrastructure/
  - backend/nfx/management/commands/
  - scripts/
  - tests/
  - docs/
---

## Description

Deliver P9-01: a reproducible internal Docker runtime in which a reverse proxy is the only
user-facing entry point, HTTPS is mandatory, and web, worker, scheduler, PostgreSQL, and MinIO
run as separately restartable services with private data-plane access. The existing application
Compose file starts the web service directly on a loopback HTTP port and does not provide the
approved proxy boundary, runtime TLS configuration, service-specific limits, or a documented
upgrade/rollback procedure.

The P1/P3 configuration, health, lease recovery, and fiscal-destination guards are already the
baseline. This issue wires those contracts into a runtime deployment without adding external
access, a trusted CA, HA, a broker, new fiscal transports, or backup replication.

## Objective and Expected Outcome

An operator can provision only externally supplied runtime secrets and a locally generated
self-signed certificate, start the runtime profile, and reach the application through HTTPS at
the proxy. Direct access to PostgreSQL, MinIO, its console, worker, and scheduler is unavailable
from the user-facing network. Web readiness, worker/scheduler health, dependency failures, and
independent service restarts remain observable; durable jobs and leases recover through the
existing P3 contracts. The self-signed certificate limitation and the host-only deployment
assumption are explicit in the runbook.

## Implementation Plan

1. Map the approved P9-01 topology to the current application Compose services, Docker image
   stages, configuration loader, health endpoints, process commands, and existing development/
   smoke profiles. Keep development/test Compose behavior isolated so their loopback ports and
   disposable networks continue to work; do not weaken fail-closed configuration or fiscal
   destination validation.
2. Add a runtime Compose configuration with one proxy, web, worker, scheduler, PostgreSQL, and
   MinIO service on private application/data networks. Publish only the proxy HTTPS port to the
   host; remove host publication for database, object store, console, worker, and scheduler in
   the runtime profile. Use persistent named volumes for PostgreSQL and MinIO, explicit service
   dependencies/readiness checks, the same immutable application image/version for all three
   application processes, and bounded CPU/memory/temporary-storage settings that cannot starve
   the web service. No secret or certificate material may be copied into an image or committed.
3. Configure the proxy to terminate locally generated self-signed TLS, reject or redirect plain
   HTTP according to the selected safe contract, forward only the web application paths, enforce
   bounded request/body/response timeouts and headers, and avoid exposing provider error details.
   Mount the certificate/key from an external runtime location with restrictive permissions and
   make startup fail closed when it is missing, malformed, or shared with an invalid secret
   source. Preserve secure cookie, CSRF, session, redaction, and allowlist behavior at the
   application boundary.
4. Define runtime health behavior and operator controls: liveness remains dependency-free,
   readiness checks only the dependencies required by the web process, operational health keeps
   worker/scheduler freshness and degraded/unavailable states, and each service can restart
   independently. A DB or MinIO outage must prevent unsafe progress; worker death must leave P3
   leases reclaimable; scheduler death must leave due work recoverable. Do not make health checks
   perform fiscal work or mutate jobs.
5. Add an upgrade/rollback runbook covering external secret/certificate provisioning, schema
   compatibility checks, migration ordering, health-gated traffic, service restart order,
   rollback to the prior image/config while the schema remains compatible, volume preservation,
   certificate renewal, and the accepted self-signed trust warning. State that CA trust, HA,
   physically separate backups, and external access are out of scope.
6. Add synthetic validation for rendered Compose topology, host port exposure, TLS handshake and
   HTTP rejection/redirect, security headers/cookies, direct-service isolation, service restart,
   readiness/dependency failure, resource limits, and background processing without a browser or
   fiscal network. Keep test and smoke projects isolated and never use production credentials,
   certificates, CNPJs, XML, endpoints, or object contents.
7. During the build pass, document the runtime contract and evidence, synchronize the P9-01
   status in `IMPLEMENTATION_PLAN.md`, the owning spec, and `specs/README.md` according to their
   conventions, refresh Graphify with `graphify update .`, update this issue's Resolution, and
   close the work in one focused commit.

## In Scope

- Runtime-only Docker topology, proxy TLS termination, private service networking, persistent
  volumes, health/readiness wiring, and measured service resource limits.
- External mounting/validation of runtime secrets and a locally generated self-signed certificate.
- Safe restart, upgrade, rollback, and operator documentation.
- Automated topology, security-boundary, health, restart, and no-network validation using
  synthetic values.

## Out of Scope

- A publicly reachable deployment, trusted internal CA, certificate authority rollout, HA,
  clustering, service mesh, broker, autoscaling, or physically separate backup destination.
- Backup/restore, retention, controlled deletion, hardening review, pilot/homologation, or a new
  dashboard beyond the existing health contract.
- New authentication/RBAC/session semantics, fiscal adapters, official endpoints, production
  credentials, or changes to job, cursor, ingestion, artifact, or document state ownership.
- Replacing the development/test Compose profiles or weakening their isolation and synthetic
  validation contracts.

## Dependencies and Notes

- Plan item: `IMPLEMENTATION_PLAN.md` — P9-01, “Runtime interno e HTTPS”.
- Canonical spec: `specs/p9-runtime-and-https.md`, current repository revision (no explicit
  version field), especially “Decisões e configuração”, “Segurança, observabilidade e falhas”,
  and “Testes, rollback e evidência”.
- Completed prerequisites: P1-01/P1-03 persistence, configuration, session/security, and
  service boundaries; P3-01/P3-04 durable leases, worker/scheduler loops, and operational health
  (issue 0001 and issue 0004). Issue 0008 established the clean-build/runtime-secret boundary.
- Current gap: `docker-compose.app.yml` publishes the web process directly on loopback HTTP and
  has no proxy or runtime-only private-network topology; the repository has no P9 runtime issue
  covering this outcome.
- Data/compatibility: do not delete or recreate persistent PostgreSQL/MinIO volumes during
  upgrade or rollback; schema changes remain owned by their domain specs and must pass the
  existing migration compatibility checks.
- Security/observability: no secrets, certificate keys, raw fiscal content, provider errors, or
  credentials in images, committed configuration, logs, health responses, metrics, or runbooks.
  Proxy and application logs use existing redaction and bounded labels.
- Accepted decisions: single Docker host and self-signed HTTPS. Deferred decisions: trusted CA,
  separate backup location, and HA. Runtime values for limits, proxy choice, names, and mounted
  certificate paths may be selected locally and must be recorded with their rationale and tests.

## Tests

- **Unit:** runtime configuration validation, certificate/secret-source exclusivity, safe
  redaction, health/readiness mapping, and fail-closed invalid configuration.
- **Integration:** rendered Compose service/network/port assertions, TLS and HTTP behavior,
  direct-service access denial, secure headers/cookies, dependency outage, independent service
  restart, lease/scheduler recovery, persistent-volume preservation, and migration compatibility.
- **Smoke:** runtime web/worker/scheduler startup, health endpoints, no-browser operation, and no
  fiscal network call.
- **Validation commands:** repository-configured focused checks plus `make lint`,
  `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] The runtime profile starts web, worker, scheduler, PostgreSQL, MinIO, and one reverse proxy
  using the same application version for web/worker/scheduler and externally mounted secrets only.
- [x] The proxy is the sole published user-facing service, requires HTTPS, and safely handles
  plain HTTP, TLS certificate/key errors, bounded request limits, timeouts, and required headers.
- [x] PostgreSQL, MinIO, the MinIO console, worker, and scheduler have no host-published ports
  and are unreachable from the user-facing network while remaining reachable only as required by
  private service networks.
- [x] Runtime PostgreSQL and MinIO data survives independent application-service restarts and a
  compatible upgrade/rollback rehearsal; no command removes or recreates persistent volumes.
- [x] Missing, malformed, duplicated, or committed-secret runtime configuration fails closed
  without printing credentials, certificate material, connection strings, or raw provider errors.
- [x] Liveness, readiness, and operational health preserve their distinct contracts; dependency
  outage is degraded/unavailable rather than false-ready, and health checks do not mutate jobs or
  perform fiscal work.
- [x] Worker and scheduler can restart independently: expired P3 leases and due work remain
  reclaimable/recoverable, and a web restart does not lose durable job or cursor progress.
- [x] Resource limits and proxy timeouts are bounded and validated so worker workloads cannot
  silently starve web traffic; the chosen values and measurement method are documented.
- [x] Synthetic tests cover expected and negative TLS, isolation, restart, dependency, resource,
  configuration, redaction, and no-network cases, and all configured validation commands pass.
- [x] The runbook documents external provisioning, certificate renewal, health-gated upgrade,
  compatible rollback, persistent-volume safety, self-signed trust limitations, and deferred
  CA/HA decisions.
- [x] The P9-01 evidence in `IMPLEMENTATION_PLAN.md`, the owning spec/index, documentation,
  Graphify metadata, and this issue's Resolution are synchronized before closure, and the work is
  closed in one focused commit.

## References

- Plan: `IMPLEMENTATION_PLAN.md` — P9-01 runtime interno e HTTPS.
- Spec: `specs/p9-runtime-and-https.md` — topology, security, health, failure, upgrade, rollback,
  and acceptance contract.
- Architecture: `ARCHITECTURE.md` sections 7–9, 34, 39–41 and ADR-001/002/013.
- Product: `PRD.md` SEC-003, SEC-006, SEC-008, OPS-002, OPS-007, NFR-007, and AC-024.
- Related implementation: `issues/0001_-_durable-job-queue-and-leases.md`,
  `issues/0004_-_job-observability-and-initial-health.md`, and
  `issues/0008_-_reproducible-clean-checkout-build.md`.

---

## Resolution

<!-- Filled by the agent on close. Include files modified, tests, preserved behavior, and decisions. -->

Implemented P9-01 with a dedicated `docker-compose.runtime.yml` topology and pinned Nginx
`runtime-proxy` image stage. Web, worker, scheduler, PostgreSQL, MinIO, and the proxy run as
separately restartable services; only the proxy publishes HTTP redirect/HTTPS ports, while app
and data networks remain private and PostgreSQL/MinIO use persistent named volumes. All three
application processes use the same externally selected immutable image. Runtime application
secrets are mounted from an external read-only directory, and TLS files are mounted from an
external certificate directory; no secret or key material is committed.

Added Nginx TLS termination with HTTP 308 redirect, TLS 1.2/1.3, request-size and timeout
limits, rate limiting, security headers, forwarded HTTPS headers, and fail-closed certificate
loading. Added validated `NFX_ALLOWED_HOSTS`, proxy-aware Django settings, secure session
cookies, resource/tmpfs limits, and the synthetic self-signed certificate provisioning helper.
Added `docs/RUNTIME.md` with provisioning, health, independent restart, upgrade/rollback,
certificate renewal, resource measurement, and accepted self-signed/host-local limitations.

Tests added in `tests/unit/test_runtime_topology.py` cover service topology, port exposure,
private networks, shared image, persistent volumes, external secrets/TLS, proxy limits, resource
limits, and host validation. The Nginx image configuration was validated with `nginx -t` using
synthetic certificate material.

Validation completed:

- `make lint` — passed (Ruff, mypy, frontend lint).
- `make build` — passed (Django check and frontend build).
- `make test-unit` — passed, 215 tests.
- `make test-integration` — passed on the sequential recheck, 61 tests; an earlier concurrent
  run hit the repository's pre-existing nondeterministic document ordering assertion and was
  rerun successfully without changing that unrelated surface.
- `make smoke` — passed.
- Runtime and all existing Compose files rendered successfully with synthetic external values;
  Graphify was refreshed with `graphify update .`.

Key decisions: development/test Compose files remain unchanged; the runtime proxy config is
baked into a non-secret image stage because this environment's Docker daemon mishandles
individual host-file binds, while runtime TLS and application secret material remain external.
