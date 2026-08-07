# Fundação P0

## Decisões Proposed adotadas

- A árvore física é `backend/`, `frontend/`, `tests/`, `scripts/` e `docs/`. Os pacotes
  `nfx.identity`, `companies`, `certificates`, `collection`, `documents`, `artifacts`,
  `exports`, `retention`, `audit`, `operations`, `adapters` e `infrastructure` estabelecem
  limites lógicos. Um módulo só deve usar a interface pública de outro módulo.
- Python usa `pip` com versões exatas em `requirements*.txt`; o frontend usa `npm` e
  `frontend/package-lock.json`. Python 3.12 e Node 20/22 são validados por `make install`.
- Os comandos são `make web`, `make worker` e `make scheduler`. Eles executam a mesma árvore
  `backend/nfx`; o worker processa somente handlers registrados na fronteira de jobs e o
  scheduler recupera leases vencidos. Ambos não têm acesso a transportes, endpoints,
  certificados, CNPJs, XMLs ou trabalho fiscal.
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
background processes start their durable loops. Set `TEST_RUN_ID` to run two suites in parallel
with predictable distinct project/bucket names.

`make check-services` returns zero only when PostgreSQL and MinIO are ready. On failure it returns
non-zero and says only which dependency is unavailable; it never prints connection strings or
credentials. `/health/live` is independent of services and `/health/ready` returns 503 until both
dependencies are reachable.

## Persistência e migrações (P1-01)

PostgreSQL é a autoridade relacional. O único schema desta fase é
`nfx_schema_contract`, metadado operacional sem estado de domínio. Sua chave singleton e os
constraints impedem mais de um contrato; o índice de `updated_at` sustenta a consulta operacional
de verificação mais recente. Entidades fiscais, usuários, jobs, empresas e certificados continuam
fora desta migration e serão adicionados exclusivamente por suas specs proprietárias.

Para uma instalação vazia, inicie os serviços de desenvolvimento e execute
`python backend/manage.py nfx_migrate`. O comando obtém um advisory lock PostgreSQL, aplica o
grafo Django e informa apenas nomes de migrations e resultado. `python backend/manage.py
schema_status` mostra a versão NFX esperada e falha quando ela está ausente ou quando o banco está
adiantado para uma versão incompatível. `python backend/manage.py showmigrations nfx` mostra o
grafo e pendências. A readiness também falha com resposta genérica quando o schema não for
compatível; não inclui URL ou senha.

Cada migration futura deve declarar dependências, constraints e índices que atendam uma consulta
identificada, além de testes de instalação limpa, upgrade, falha e recovery. Mudanças aditivas são
preferidas até P9. Mudanças irreversíveis exigem backup/restore aplicável e uma migration corretiva
ou backfill reiniciável; rollback nunca deve apagar dados para “consertar” schema.

## Scope boundary

## Configuração segura e isolamento fiscal (P0-02/P0-04)

Every web, worker and scheduler boot loads `nfx.infrastructure.configuration` before Django opens a
connection. `NFX_PROFILE` is mandatory and is exactly `test`, `development`, `homologation`, or
`runtime`; it is never inferred from a hostname. `NFX_SECRET_KEY` is supplied through the process
environment or `NFX_SECRET_KEY_FILE` (a mounted secret file), never both. `DATABASE_URL` and
`MINIO_ROOT_PASSWORD` and `NFX_CERTIFICATE_MASTER_KEY` are also required external secrets;
the certificate key is base64url-encoded 32-byte key material and may be mounted through
`NFX_CERTIFICATE_MASTER_KEY_FILE`. PostgreSQL URLs, MinIO credentials and
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

## Simuladores fiscais sintéticos (P3-03)

`nfx.adapters.simulation` é a porta interna usada pelos testes antes dos adaptadores oficiais.
`FiscalRequest` aceita somente referências seguras — fonte, família, ator, fluxo, cursor, política,
handle abstrato de certificado e correlação — e `FiscalResponse` devolve unidades sem conteúdo,
hashes sintéticos, cursor/NSU, cobertura, cooldown e códigos seguros. NF-e e ADN são simuladores
independentes, com cenários gerados por seed e sequência reproduzível; `FakeFiscalTransport`
registra a ordem das chamadas e nunca abre DNS, HTTP ou SOAP.

Os cenários distinguem vazio válido, ausência de cobertura, indisponibilidade, parcial, cooldown,
bloqueio, duplicata, conflito, payload malformado, evento sem pai e cursor repetido. O handler
genérico transforma esses valores em `HandlerOutcome` e preserva a fronteira de lease/idempotência
dos jobs. Fixtures não carregam XML, credenciais, tokens, certificados ou endpoints produtivos.
