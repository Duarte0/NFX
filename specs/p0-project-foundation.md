# Fundação do projeto

## Metadados

- **Fase/status:** P0 — implementação concluída e verificada, incluindo o contrato reproduzível de `make build`.
- **Backlog:** P0-01, P0-03, P0-05.
- **Dependências:** scaffold atual; nenhuma spec anterior.
- **PRD:** OPS-007; suporte futuro a NFR-001, NFR-002 e NFR-005. **Aceite relacionado:** AC-023 e AC-024 serão concluídos em fases posteriores.
- **Arquitetura:** ADR-001, ADR-002, ADR-003 e ADR-004; seções 6, 9, 10, 11, 12, 14, 37 e 39.

## Propósito e resultado observável

Criar uma base executável do monólito modular Django/DRF + React/TypeScript. Um checkout limpo deve conseguir instalar dependências, iniciar `web`, `worker` e `scheduler`, compilar o frontend e executar lint, testes e smoke checks contra PostgreSQL e MinIO isolados. Os três processos usam a mesma versão do domínio, mas comandos e ciclos de vida distintos.

## Baseline, escopo e não escopo

O baseline implementado é um monólito modular Django/DRF + React/TypeScript em `backend/` e `frontend/`, com dependências travadas, Compose de aplicação e de testes, comandos `web`/`worker`/`scheduler`, smoke e suites unitária e de integração isoladas. Os limites lógicos previstos existem; `documents`, `exports` e `retention` permanecem boundaries sem domínio implementado. Esta spec não inclui usuários, tabelas fiscais, certificados, adapters oficiais, integração externa, proxy de runtime ou decisões finais de deploy.

## Decisões e detalhes Proposed

São **Accepted** a stack, o monólito modular, os três processos, PostgreSQL como autoridade e MinIO para blobs. São **Proposed**, a decidir localmente na implementação: nomes físicos de diretórios, gerenciadores de dependência e nomes dos comandos. A escolha deve manter áreas separadas para backend, frontend, testes/fixtures e operação; módulos de negócio não acessam internals uns dos outros.

Cada comando deve ter contrato documentado:

- instalação reproduzível valida versões Python 3.12 e Node compatível e usa dependências travadas;
- build valida import/configuração Django, artefato React e ausência de dependência de serviço externo;
- lint verifica Python e TypeScript, incluindo tipos;
- teste executa suites unitárias e de integração em recursos exclusivos de teste;
- smoke sobe web/worker/scheduler, verifica que continuam vivos, que web responde health básico e que worker/scheduler não executam trabalho fiscal;
- teardown remove apenas volumes/buckets explicitamente identificados como teste.

## Módulos, contratos e estado

Os limites lógicos de identidade, empresas, certificados, coleta, documentos/artefatos, exportações/retenção, auditoria/operação, adaptadores e infraestrutura existem e continuam sendo a fronteira entre módulos. Configuração, relógio, IDs/correlação, banco, objetos e logging devem permanecer injetáveis. Nenhuma UI é proprietária de estado durável.

## Segurança, observabilidade e falhas

Logs estruturados mínimos: timestamp, nível, processo, ambiente e `correlation_id`; o redator de P0-02 será o único caminho para campos potencialmente sensíveis. Dependência indisponível deve produzir saída não sensível e exit code não zero; processo não pode declarar readiness. O rollback é remover o scaffold ou voltar a versão anterior, pois não há dados produtivos.

## Testes e evidências

A baseline tem `make install`, `lint`, `test-unit`, `test-integration` e `smoke`; `docker-compose.test.yml` e os scripts criam projeto, rede, volumes e bucket exclusivos por `TEST_RUN_ID`. As suites cobrem health, dependências injetáveis, configuração/redaction e os processos web/worker/scheduler. Fixtures são strings/bytes sintéticos.

`make build` encapsula apenas no próprio recipe um perfil `test` e valores sintéticos já usados
pelas validações locais. O comando executa o `manage.py check` antes do build frontend, não inicia
serviços, não aplica migrations e não abre conexões externas. O carregador de configuração continua
fail-closed para entradas ausentes, placeholder, malformadas, conflitantes ou capazes de produção;
os processos de runtime continuam dependentes de segredos provisionados externamente.

## Sequência, aceite e DoD

1. Fixar toolchains e dependências. 2. Criar limites de módulos. 3. Criar processos. 4. Integrar serviços de desenvolvimento/teste. 5. Adicionar build/lint/test/smoke e documentação.

- [x] `make build` encapsula e documenta um perfil/valores sintéticos locais, sem segredo versionado utilizável.
- [x] `web`, `worker` e `scheduler` iniciam a mesma versão e têm responsabilidades distintas.
- [x] Falha de Postgres/MinIO impede readiness sem stack/segredo na resposta.
- [x] Duas execuções de teste não usam dados/volumes de desenvolvimento nem entre si.
- [x] Não existe integração fiscal oficial, endpoint público ou segredo real.

DoD: implementação, dependências travadas, suites verdes e evidências estão concluídas. **Accepted:**
a árvore é `backend/`, `frontend/`, `tests/`, `scripts/` e `docs/`; Python usa `pip`/`requirements*.txt`,
e o frontend usa `npm`/`package-lock.json`. Sem blocker de produto.
