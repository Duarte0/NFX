# Fundação P0

## Decisões Proposed adotadas

- A árvore física é `backend/`, `frontend/`, `tests/`, `scripts/` e `docs/`. Os pacotes
  `nfx.identity`, `companies`, `certificates`, `collection`, `documents`, `artifacts`,
  `exports`, `retention`, `audit`, `operations`, `adapters` e `infrastructure` estabelecem
  limites lógicos. Um módulo só deve usar a interface pública de outro módulo.
- Python usa `pip` com versões exatas em `requirements*.txt`; o frontend usa `npm` e
  `frontend/package-lock.json`. Python 3.12 e Node 20/22 são validados por `make install`.
- Os comandos são `make web`, `make worker` e `make scheduler`. Eles executam a mesma árvore
  `backend/nfx`; worker e scheduler são loops vazios nesta fase e não contêm transportes,
  endpoints, certificados, CNPJs, XMLs ou trabalho fiscal.
- Cada integração/smoke cria um projeto Compose e bucket `nfx-p0-test-<run-id>` exclusivos,
  em uma rede Compose privada. O teardown usa somente `docker compose -p <id> down --volumes`;
  portanto não toca os volumes `postgres_data`/`minio_data` de desenvolvimento.

## Contratos dos comandos

Run `make install` once in a clean Python 3.12 / Node 20 or 22 checkout. `make build` executes
Django's import/configuration check and creates the Vite artifact without contacting PostgreSQL
or MinIO. `make lint` checks Ruff, mypy, TypeScript and ESLint. `make test-unit` uses no services.

`make test-integration` starts isolated PostgreSQL 16 and MinIO, waits for both, runs the
integration suite and always removes its own containers, network and volumes. `make smoke` does
the same before starting web, worker and scheduler, verifies liveness/readiness and that both
background processes report their intentionally empty loops. Set `TEST_RUN_ID` to run two suites
in parallel with predictable distinct project/bucket names.

`make check-services` returns zero only when PostgreSQL and MinIO are ready. On failure it returns
non-zero and says only which dependency is unavailable; it never prints connection strings or
credentials. `/health/live` is independent of services and `/health/ready` returns 503 until both
dependencies are reachable.

## Scope boundary

## Configuração segura e isolamento fiscal (P0-02/P0-04)

Every web, worker and scheduler boot loads `nfx.infrastructure.configuration` before Django opens a
connection. `NFX_PROFILE` is mandatory and is exactly `test`, `development`, `homologation`, or
`runtime`; it is never inferred from a hostname. `NFX_SECRET_KEY` is supplied through the process
environment or `NFX_SECRET_KEY_FILE` (a mounted secret file), never both. `DATABASE_URL` and
`MINIO_ROOT_PASSWORD` are also required external secrets; PostgreSQL URLs, MinIO credentials and
`CHANGE_ME` values fail boot with a safe, non-zero configuration error.

`test` and `development` are restricted to `simulator://empty` and local transport names. The
simulator returns an empty result and is the only fiscal transport in P0. `homologation` and
`runtime` require an explicit simulator selection, destination, and matching `NFX_FISCAL_ALLOWLIST`;
no production-capable transport exists yet. `FiscalDestinationGuard` normalizes and validates the
configured destination and any redirect chain before it invokes a sender, so a forbidden endpoint
causes zero network calls.

`nfx.infrastructure.redaction.redact` is the shared boundary for structured logs and future audit
or HTTP errors. It redacts sensitive fields recursively, credential-bearing URLs and sensitive query
strings, XML/PDF payloads, bytes, and exception arguments. Never put a secret, certificate, CNPJ,
real XML, or endpoint into a fixture.
