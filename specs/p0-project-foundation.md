# Fundação do projeto

## Metadados

- **Fase/status:** P0 — pronta para implementação.
- **Backlog:** P0-01, P0-03, P0-05.
- **Dependências:** scaffold atual; nenhuma spec anterior.
- **PRD:** OPS-007; suporte futuro a NFR-001, NFR-002 e NFR-005. **Aceite relacionado:** AC-023 e AC-024 serão concluídos em fases posteriores.
- **Arquitetura:** ADR-001, ADR-002, ADR-003 e ADR-004; seções 6, 9, 10, 11, 12, 14, 37 e 39.

## Propósito e resultado observável

Criar uma base executável do monólito modular Django/DRF + React/TypeScript. Um checkout limpo deve conseguir instalar dependências, iniciar `web`, `worker` e `scheduler`, compilar o frontend e executar lint, testes e smoke checks contra PostgreSQL e MinIO isolados. Os três processos usam a mesma versão do domínio, mas comandos e ciclos de vida distintos.

## Baseline, escopo e não escopo

Hoje existem apenas documentos, `Dockerfile` de desenvolvimento, Compose com PostgreSQL 16/MinIO e `.env.example`; não há aplicação, lockfiles, schema, migrações, testes ou CI. Esta spec cria o scaffold, convenções modulares, automação local e baseline de testes. Não cria usuários, tabelas fiscais, certificados, adapters, integração externa, proxy de runtime ou decisões finais de deploy.

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

Criar limites lógicos para identidade, empresas, certificados, coleta, documentos/artefatos, exportações/retenção, auditoria/operação, adaptadores e infraestrutura. Nesta fase não há entidade de domínio. Configuração, relógio, IDs/correlação, banco, objetos e logging devem ser injetáveis. Nenhuma UI é proprietária de estado durável.

## Segurança, observabilidade e falhas

Logs estruturados mínimos: timestamp, nível, processo, ambiente e `correlation_id`; o redator de P0-02 será o único caminho para campos potencialmente sensíveis. Dependência indisponível deve produzir saída não sensível e exit code não zero; processo não pode declarar readiness. O rollback é remover o scaffold ou voltar a versão anterior, pois não há dados produtivos.

## Testes e evidências

Matriz: instalação limpa; build backend/frontend; lint com erro proposital; teste unitário; Postgres/MinIO indisponíveis; smoke dos três processos; execução paralela de duas suites confirmando bancos/buckets distintos; teardown sem tocar desenvolvimento. Fixtures são strings/bytes sintéticos. Evidência: comandos e saídas de sucesso, matriz de processos/health e demonstração de isolamento por nomes/credenciais/volumes diferentes.

## Sequência, aceite e DoD

1. Fixar toolchains e dependências. 2. Criar limites de módulos. 3. Criar processos. 4. Integrar serviços de desenvolvimento/teste. 5. Adicionar build/lint/test/smoke e documentação.

- [ ] Checkout limpo executa todos os comandos documentados.
- [ ] `web`, `worker` e `scheduler` iniciam a mesma versão e têm responsabilidades distintas.
- [ ] Falha de Postgres/MinIO impede readiness sem stack/segredo na resposta.
- [ ] Duas execuções de teste não usam dados/volumes de desenvolvimento nem entre si.
- [ ] Não existe código fiscal, endpoint público ou segredo real.

DoD: comandos reproduzíveis, dependências travadas, suites verdes e evidências registradas. **Assunção Proposed:** nomes físicos e ferramentas serão escolhidos nesta implementação e documentados. Sem blocker local.
