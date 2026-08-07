---
id: 0003
title: "Implement deterministic fiscal simulators and synthetic fixtures"
type: feature
status: closed
priority: high
phase: P3
created_at: 2026-08-06
updated_at: 2026-08-07
closed_at: 2026-08-07
related_issues: [0001, 0002]
blocked_by: []
affects:
  - backend/nfx/adapters/
  - backend/nfx/jobs/
  - tests/unit/
  - tests/integration/
  - docs/
---

## Description

Deliver P3-03: a deterministic, transport-substitutable fiscal-adapter contract with synthetic NF-e and ADN simulators, scenario fixtures, and an explicit no-network proof. The completed P3-01 job engine provides the handler boundary and recovery semantics, while the current `EmptyFiscalSimulator` only returns an empty tuple and cannot model pagination, coverage, classified failures, replay, or restart cases required by P4–P6.

The outcome must make later collection and ingestion code independent of real fiscal endpoints, credentials, certificates, CNPJs, and XML. Simulated outcomes must distinguish valid empty responses, unavailable source, no coverage, partial work, cooldown, permanent blocking, malformed content, and conflicts without treating one as another.

## Implementation Plan

1. Define an internal fiscal-adapter port under the existing `nfx.adapters` boundary. Its request must carry only source/family/actor/flow, opaque cursor or NSU, effective-policy reference, abstract certificate handle, and correlation ID; its typed response must express synthetic raw units/pages, next cursor/NSU, coverage, cooldown, and classified outcome. Keep NF-e and ADN contracts independently selectable even if they share neutral value types.
2. Replace or extend the P0 empty-only simulator with deterministic NF-e and ADN fakes that implement the port without opening a network connection. Preserve the existing `FiscalDestinationGuard` as the boundary that rejects non-simulator destinations and redirects before a sender can run; no simulator path may invoke DNS, HTTP, SOAP, or a production-capable transport.
3. Add a scenario/fixture library using only clearly marked generated data, reserved domains, and algorithmically valid fictional identifiers where required. A scenario must have a seed and ordered steps so replay is stable, and must fail explicitly when invalid rather than being interpreted as an empty result. Do not add real XML, customer CNPJ, PFX/PEM, token, credential, endpoint, or copied fiscal payload.
4. Cover the required scenarios through the port: paginated success; valid empty response; duplicate with equal hash; same identity with different content; timeout/unavailability; cooldown; permanent block; malformed or unknown payload; event without parent; repeated cursor; partial result; and interruption/restart. Ensure fake transport call recording can prove ordering and absence of network I/O while leaving document persistence, cursor durability, and ingestion behavior to P4.
5. Integrate the simulator only at the generic jobs/handler seam necessary for synthetic worker tests. Preserve P3-01 lease, idempotency, restart, safe-payload, and redacted-log invariants; do not introduce manual collection routes/UI, retry-policy decisions owned by P3-02, official adapters, or document models.
6. During the build pass, update P3-03 evidence in `IMPLEMENTATION_PLAN.md`, this spec and `specs/README.md` only as their completion conventions require, update relevant development documentation, refresh Graphify with `graphify update .`, update this issue’s Resolution, and commit the completed implementation as one focused commit.

## Out of Scope

- P3-02 policy persistence, retry/backoff/jitter implementation, cooldown scheduling, and permanent-job state transitions (covered by open issue 0002).
- P3-04 job metrics, operational health states, dashboards, or alerting.
- P3-05 manual collection commands, RBAC/audit flows, HTTP endpoints, and UI.
- Official SEFAZ/ADN SOAP/HTTP transports, endpoint/envelope/layout decisions, homologation, or any production fiscal call.
- P4 document/event persistence, object storage, cursor checkpoint durability, quarantine implementation, or fiscal-content parsing.

## Tests

- **Unit:** add port, scenario, and fake-transport tests under `tests/unit/` for deterministic seeded replay, independent NF-e/ADN selection, pagination, each typed outcome/error, cursor repetition, invalid fixture rejection, log redaction, and proof that simulator execution performs no network call.
- **Integration:** add synthetic PostgreSQL/job-boundary coverage under `tests/integration/` for handler interruption/restart and replay without duplicate logical effects; use only generated fixture data and fakes.
- **Regression:** retain and extend the existing fiscal-destination guard tests so prohibited destinations and redirect chains still make zero sender calls.
- **Validation:** run focused simulator tests plus `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke`.

## Acceptance Criteria

- [x] A documented internal fiscal-adapter port accepts only safe contextual references and returns typed synthetic pages/outcomes, cursor/NSU, coverage, cooldown, and safe metadata; NF-e and ADN remain independently selectable.
- [x] Deterministic NF-e and ADN simulators implement the port with seeded, ordered scenarios and cannot initiate DNS, HTTP, SOAP, or another fiscal network operation.
- [x] Synthetic scenarios cover paginated success, valid empty response, equal-hash duplicate, divergent-content identity conflict, timeout/unavailability, cooldown, permanent blocking, malformed/unknown payload, event without parent, repeated cursor, partial result, and interruption/restart.
- [x] Valid empty, no coverage, unavailable, partial, cooldown, and blocked outcomes are represented distinctly and invalid fixture data fails explicitly rather than being returned as empty.
- [x] Fixture data is generated and clearly marked, uses no real fiscal XML, customer identifier, certificate, credential, token, or production endpoint, and automated checks prove sensitive/canary material is not accepted or logged.
- [x] Fake transport call recording proves request order and zero network calls; existing destination and redirect rejection remains fail-closed before a sender is invoked.
- [x] Synthetic handlers preserve P3-01 idempotency, lease/restart recovery, safe referential payload, and redacted logging behavior; replay does not create a duplicate logical effect in the fake boundary.
- [x] Automated unit and integration tests cover the scenarios and negative cases above without fiscal network traffic.
- [x] `make lint`, `make test-unit`, `make test-integration`, `make build`, and `make smoke` complete successfully with no regression to queue/lease or safe-configuration behavior.
- [x] Completion updates P3-03 evidence in plan/spec tracking files according to their documented conventions, updates relevant documentation, refreshes Graphify, updates this issue’s Resolution, and is committed as one focused commit.

## References

- Implementation plan: `IMPLEMENTATION_PLAN.md` — P3-03, a critical-path prerequisite for P4 ingestion and later NF-e/ADN adapters.
- Spec: `specs/p3-fiscal-adapter-simulation-and-fixtures.md` — P3-03; version/current repository baseline.
- Related specs: `specs/p3-durable-jobs-leases-and-policy-engine.md` (completed P3-01 engine and pending P3-02 policy) and `specs/p4-fiscal-document-ingestion-and-integrity.md` (downstream ingestion owner).
- Current baseline: `backend/nfx/adapters/fiscal.py` (`EmptyFiscalSimulator` and `FiscalDestinationGuard`), `backend/nfx/jobs/handlers.py`, `backend/nfx/jobs/services.py`, and `tests/unit/test_safe_configuration.py`.
- Dependencies: P0-04 safe configuration/test isolation and P3-01 durable jobs are implemented (closed issue 0001). P3-02 is already covered by open issue 0002 but does not block this port/simulator slice; official endpoint/layout details remain explicitly out of scope.

---

## Resolution
<!-- Filled by the agent on close. DO NOT edit manually. -->
<!-- Include: files modified, tests added, edge cases handled, tracking updates, Graphify update, and focused commit. -->

Implemented `backend/nfx/adapters/simulation.py` with the safe internal adapter port, independent
deterministic NF-e/ADN simulators, generated seeded scenarios, no-network fake transport, and
generic jobs handler conversion. Added 33 unit tests and a PostgreSQL-backed job-boundary test for
typed outcomes, safe references, invalid fixture rejection, request order, socket isolation,
destination guarding, interruption/restart replay, and duplicate-effect prevention. Synthetic
fixtures contain only generated identities and hashes; no fiscal content, credentials, tokens,
certificates, or production endpoints are accepted or logged.

Updated the P3-03 spec, `specs/README.md`, `IMPLEMENTATION_PLAN.md`, and development documentation;
refreshed Graphify with `graphify update .`. Validation passed: targeted Ruff/mypy, `make lint`,
`make test-unit` (108 passed), test-profile `make build`, `make test-integration` (22 passed), and
`make smoke` with web/worker/scheduler running. No fiscal network or production data was used.
