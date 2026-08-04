# Persistência relacional e migrações

## Metadados

- **Fase/status:** P1 — concluída.
- **Backlog:** P1-01. **Dependência:** `p0-project-foundation.md`.
- **PRD:** NFR-004 e premissa de base vazia da seção 27.
- **Arquitetura:** ADR-003; seções 14, 15, 16, 37, 40 e 41.

## Propósito e resultado

Estabelecer PostgreSQL como autoridade relacional, com migrações reproduzíveis, constraints/índices verificáveis e política de forward recovery. Instalação vazia e upgrade desde a migração anterior devem chegar ao mesmo schema lógico sem perda silenciosa.

## Baseline e escopo

Postgres 16 existe apenas no Compose; não há projeto Django, banco de teste, migração ou legado. Esta spec cria tooling, convenções e campos fundacionais somente quando necessários. Não antecipa entidades fiscais, jobs, empresa, certificado ou contratos HTTP; cada spec dona desses estados cria suas migrações.

## Decisões e Proposed

São **Accepted** PostgreSQL/ORM transacional, constraints persistentes e correção progressiva em mudança irreversível. Nomes finais de tabelas, UUID versus outro ID e timestamps auxiliares são **Proposed** e podem ser escolhidos localmente; a decisão deve ser consistente, documentada e não converter chave física em identidade fiscal.

Cada migração precisa: dependência explícita; operação reversível quando segura; plano de forward recovery quando não; constraints e índices justificados pela consulta; teste de instalação limpa e upgrade; verificação de compatibilidade com processos da versão anterior quando deploy exigir sobreposição. Dados e schema não são corrigidos por rollback destrutivo.

## Decisões de implementação

- O schema físico de infraestrutura é `nfx_schema_contract`; ele é deliberadamente o único estado criado nesta spec e não representa identidade fiscal ou domínio de produto.
- A migration `nfx.0001_schema_contract` é o baseline explícito, reversível em instalação sem dados de domínio. Usa chave singleton `smallint`, constraints de singleton/versão e o índice `nfx_schema_contract_updated_at_idx` para inspeção operacional mais recente. IDs UUID e timestamps de entidades de domínio permanecem decisão das specs proprietárias.
- `nfx_migrate` usa advisory lock PostgreSQL estável para serializar deploys; `schema_status` e readiness consideram migrations NFX ausentes ou desconhecidas incompatíveis. O comportamento estrito para schema adiantado é seguro até que uma migration futura declare compatibilidade explícita com versão anterior.
- Mudanças futuras continuam aditivas/backfill reiniciável até P9; uma falha usa migration corretiva progressiva, nunca rollback destrutivo de dados.

## Contratos e operação

Comandos devem criar banco vazio, aplicar, mostrar/verificar versão, detectar migração pendente e executar testes em DB exclusivo. Readiness falha se schema requerido estiver ausente/adiantado de forma incompatível. Logs registram nome/versão/resultado, nunca URL com senha. Saúde de schema pertence a Operação; migrações pertencem à infraestrutura relacional.

## Falha, recuperação e compatibilidade

Falha transacional não marca migração concluída. Operação não transacional deve registrar checkpoint e procedimento corretivo. Antes de mudança destrutiva futura, exigir backup/restore aplicável; até P9, usar mudanças aditivas e backfill reiniciável. Não prometer rollback que dependa de apagar dados.

## Testes e evidências

Positivos: banco vazio, upgrade sequencial, rerun sem alteração. Negativos: credencial inválida, constraint violada, schema incompatível. Recovery: falha injetada no meio e aplicação de correção. Boundary: duas instâncias tentando migrar; somente uma conclui. Evidência: grafo de migrações, schema final equivalente e plano de correção.

## Implementação e evidências

- Migrations e compatibilidade: `backend/nfx/migrations/0001_schema_contract.py` e `backend/nfx/infrastructure/schema.py`.
- Operação/readiness: `nfx_migrate`, `schema_status` e o probe de schema em `nfx.infrastructure.dependencies`; respostas de readiness permanecem genéricas e não expõem URL ou credenciais.
- Isolamento: `scripts/test-integration.sh` e `scripts/smoke.sh` aplicam migrations somente no banco Compose de nome/projeto exclusivo de teste antes de validar a aplicação.
- Testes: `tests/integration/test_migrations.py` exercita instalação limpa/rerun, constraints e índice, falha transacional seguida de correção, disputa de duas instâncias e schema adiantado; `tests/unit/test_dependencies.py` cobre readiness incompatível sem detalhes.

## Aceite e DoD

- [x] Instalação limpa e upgrade produzem schema equivalente.
- [x] Migração falha não aparece como aplicada.
- [x] Banco de teste é separado do desenvolvimento.
- [x] Toda migração futura deve declarar constraints, índices, teste e recovery.
- [x] Readiness detecta schema incompatível sem expor credencial.

DoD atendido: tooling documentado, testes de concorrência/falha verdes e nenhum schema de MVP antecipado. Validação em 2026-08-04: `./scripts/test-integration.sh` (5 passed), Ruff, mypy e 24 testes unitários verdes em imagem de teste isolada. Sem blocker local.
