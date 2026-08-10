# Plano de implementação — NFX INOV

## 1. Controle do documento

| Campo | Valor |
|---|---|
| Produto | NFX INOV |
| Tipo | Plano de implementação do MVP |
| Versão | 1.0 |
| Status | Aprovado para desdobramento em specs |
| Idioma | Português brasileiro |
| Fonte | PRD.md e ARCHITECTURE.md |
| Data | 2026-08-04 |

## 2. Propósito e escopo

Este plano organiza o MVP em fatias verticais incrementais, dependentes, testáveis e recuperáveis. É a fonte para criar specs futuras sob specs/, mas não cria código, schema, migração, teste, CI ou infraestrutura.

Abrange fundação, segurança, PostgreSQL, MinIO, empresas, certificados, jobs, NF-e, NFS-e/ADN, documentos, XML, PDF, ZIP, dashboard, retenção, backup, HTTPS, observabilidade e piloto. Exclui migração legada, SaaS, acesso externo, mobile, integrações contábeis, API pública e fontes municipais fora do ADN.

## 3. Fontes e precedência

1. PRD.md define comportamento, regras, papéis e critérios de aceite.
2. ARCHITECTURE.md define decisões, responsabilidades e invariantes técnicas.
3. Este plano define ordem, dependências, evidências e specs futuras.

O usuário confirmou o PRD como aprovado, apesar de seu cabeçalho indicar Proposto para aprovação. Isso não altera o arquivo nem o escopo. O backup local, embora diverja de OPS-BKP-002 e OPS-BKP-006, é exceção Accepted na arquitetura; será rastreado como limitação, não reaberto como bloqueio.

## 4. Base atual do repositório

O repositório não possui aplicação, schema, migrações, testes, specs ou CI. Contém Dockerfile de desenvolvimento, Docker Compose com PostgreSQL 16 e MinIO, arquivo de ambiente de exemplo, documentação e Graphify. PostgreSQL e MinIO são scaffolds aceitos, mas o Compose atual não é a topologia final de runtime.

## 5. Assunções de implementação

- Accepted: monólito modular Django/DRF e React/TypeScript; processos web, worker e scheduler.
- Accepted: PostgreSQL é autoridade transacional; MinIO armazena blobs.
- Accepted: jobs, leases e fila durável ficam no PostgreSQL; não há Redis/broker no MVP.
- Proposed: segredos de implantação são montados fora do repositório; chave mestre e senha inicial nunca são valores versionados.
- Accepted: testes bloqueiam endpoints fiscais produtivos e usam simuladores/fixtures sintéticas.
- Accepted: TLS autoassinado e backup local são limitações explícitas do MVP; CA confiável e backup separado são Deferred.

## 6. Modelo de status

| Status | Uso |
|---|---|
| Accepted | Decidido no PRD ou arquitetura e pronto para uso |
| Proposed | Recomendado; a spec futura confirma detalhes |
| Open | Não resolvido, mas trabalho independente continua |
| Deferred | Fora da fase ou do MVP |
| Blocked | Impede somente trabalho diretamente dependente |

Não há bloqueio global.

## 7. Estratégia de entrega

Entregar primeiro uma fundação executável e segura. Introduzir migrações, auditoria, objetos, autorização e invariantes fiscais antes de integrar fontes. Construir jobs e simuladores antes de adaptadores. Desenvolver a UI a cada capacidade vertical. Só então preparar runtime, restore e piloto.

~~~mermaid
flowchart LR
  P0[P0 Fundação] --> P1[P1 Núcleo seguro]
  P1 --> P2[P2 Empresas e certificados]
  P1 --> P3[P3 Jobs e simuladores]
  P2 --> P4[P4 Ingestão comum]
  P3 --> P4
  P4 --> P5[P5 NF-e]
  P4 --> P6[P6 NFS-e/ADN]
  P4 --> P7[P7 Consulta e artefatos]
  P5 --> P7
  P6 --> P7
  P7 --> P8[P8 ZIP, dashboard e retenção]
  P8 --> P9[P9 Operação e piloto]
~~~

## 8. Workstreams

| Workstream | Responsabilidade | Fases |
|---|---|---|
| Plataforma | projeto, configuração, ambiente e testes | P0, P9 |
| Segurança | identidade, sessões, RBAC, auditoria e segredos | P1, P9 |
| Dados | migrações, PostgreSQL, MinIO, backup e reconciliação | P1, P4, P9 |
| Cadastro fiscal | empresas, cobertura e A1 | P2 |
| Processamento | jobs, scheduler, leases e políticas | P3 |
| Integrações | simuladores, NF-e e NFS-e/ADN | P3–P6 |
| Acervo | documentos, eventos, XML, PDF e conflitos | P4–P7 |
| UX | login, gestão, consulta e administração | P1–P9 |
| Operação | métricas, health, TLS, restore e rollout | P3, P8, P9 |

## 9. Visão das fases

| Fase | Resultado | Dependências |
|---|---|---|
| P0 | Ambiente reproduzível e rede fiscal produtiva bloqueada | Scaffold |
| P1 | Aplicação autenticável, auditável, migrável e com objetos seguros | P0 |
| P2 | Empresas e A1 validados/cifrados | P1 |
| P3 | Scheduler e workers recuperáveis; simuladores disponíveis | P1 |
| P4 | Ingestão fiscal durável com cursor seguro | P2, P3 |
| P5 | NF-e recebida, emitida, eventos e manifestação | P4 |
| P6 | NFS-e/ADN e cobertura explícita | P4 |
| P7 | Consulta, XML, PDF e downloads | P4; P5/P6 para cobertura completa |
| P8 | ZIP, dashboard e elegibilidade de retenção sem exclusão | P7 |
| P9 | Runtime, HTTPS, backup/restore, exclusão habilitada, hardening e piloto | Dependências específicas por item |

## 10. Fases detalhadas e backlog estável

### P0 — Fundação de projeto e isolamento seguro

**Objetivo e resultado:** aplicação vazia executável localmente, banco/objeto de teste isolados e bloqueio de rede fiscal produtiva.

**Não escopo:** usuários reais, schema fiscal, certificados, integração e proxy de produção.
**Entrada:** scaffold disponível. **Saída:** build, lint e smoke test reproduzíveis.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P0-01 | Estrutura do monólito, backend, frontend e comandos web/worker/scheduler | — | ADR-001/002 | Build, lint e smoke | Reversível, sem dados |
| P0-02 | Configuração tipada, perfis, segredo externo e redaction — **implementado** (`nfx.infrastructure.configuration`, `redaction`, testes unitários) | P0-01 | SEC-007, ADR-008 | Falha sem segredo; ausência em logs | Perfil inválido falha fechado |
| P0-03 | Ciclo de banco e MinIO de desenvolvimento/teste | P0-01 | ADR-003/004 | Conectividade e isolamento | Volumes de teste descartáveis |
| P0-04 | Allowlist de rede, simulador vazio e bloqueio de produção — **implementado** (`FiscalDestinationGuard`, `EmptyFiscalSimulator`, espião zero-I/O) | P0-02 | NFR-007, arquitetura 38 | Tentativa de destino proibido | Erro seguro |
| P0-05 | Convenções modulares, correlação de logs e baseline de testes | P0-01 | arquitetura 11/37 | Teste de correlação/redaction | Sem estado persistente |

**Riscos:** ambiente local confundido com homologação; mitigação: guardas de destino.
**Specs futuras:** p0-project-foundation.md; p0-safe-configuration-and-test-isolation.md.

### P1 — Núcleo seguro, persistente e auditável

**Objetivo e resultado:** persistência, autenticação, autorização, auditoria e objetos entram antes de qualquer ação fiscal.

**Não escopo:** empresa, certificado, coleta e PDF.
**Entrada:** P0 concluída. **Saída:** usuário autenticado e auditado; nenhum estado crítico sem dono.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P1-01 | Ferramenta de migração, baseline relacional, constraints, índices e forward recovery — **implementado** (`nfx_schema_contract`, `SchemaMigrator`, `nfx_migrate`, `schema_status`) | P0-03 | ADR-003, arquitetura 15/16 | Instalação/rerun, falha transacional/correção, concorrência e banco Compose exclusivo: `tests/integration/test_migrations.py` | Backup e migração corretiva |
| P1-02 | Primeiro Administrador, Argon2id, login, rate limit e sessão por inatividade — **implementado** (`nfx.identity`, `0003_identity`, `bootstrap_admin`, testes de segurança) | P0-02, P1-01 | FR-AUTH-001, FR-AUTH-005, FR-AUTH-006, FR-AUTH-007, BR-AUTH-001, SEC-001, SEC-002, SEC-003 | Brute force, enumeração, timeout | Desativar sessões; senha nunca em claro |
| P1-03 | RBAC server-side para HTTP, jobs e downloads — **implementado** (`nfx.identity.policy.authorize`, decorator HTTP fail-closed e matriz testada) | P1-02 | SEC-005, NFR-006, regras de papéis | Matriz de permissão e acesso direto negado | Falhar fechado |
| P1-04 | Administração de usuários: lista, criação, edição, papel, reset, ativação/desativação, revogação e UI — **implementação validada; pendente Graphify completo** (`nfx.identity` administração, `0005_user_administration_version`, shell React e troca da própria senha) | P1-02, P1-03, P1-05 | FR-AUTH-002, FR-AUTH-003, FR-AUTH-004, BR-AUTH-002, SEC-004 | 9 testes específicos + 47 unitários, build/lint React e `tests/integration` isolados (18); RBAC, sessões revogadas, auditoria e migração 0005; `graphify . --update --code-only`/`cluster-only` verdes, atualização semântica bloqueada sem backend | Usuário desativado não autentica |
| P1-05 | Auditoria append-only, motivos, hash chain e redaction — **implementado** (`nfx.audit`, `0004_audit_foundation`, `/api/audit/events`, shell React) | P1-01, P1-03 | AUD-001, AUD-002, AUD-003, AUD-004, AUD-005, AUD-006, AUD-007, AUD-008, AUD-009, AUD-010, SEC-007 | `tests/integration/test_audit.py`: imutabilidade DB, redaction, motivo, cadeia, concorrência, RBAC e paginação; integração isolada verde | Eventos nunca apagados |
| P1-06 | Abstração MinIO, SHA-256 e estados pendente/finalizado/ausente/divergente — **implementado** (`nfx.artifacts.models`, `nfx.artifacts.storage`, `nfx.0002_artifact`) | P0-03, P1-01 | ADR-004, BR-INT-003, BR-INT-005 | `tests/integration/test_artifact_storage.py`: MinIO Compose, hash/tamanho, falhas, ausência/divergência, reconciliação, retry e concorrência | Não finalizar referência |
| P1-07 | Login, navegação por papel e shell desktop — **implementado** (`frontend/src/main.tsx`, pt-BR, CSRF/session API) | P1-02, P1-03 | NFR-001, NFR-002, AC-023 | Browser e localização | UI não é controle de segurança |

**Specs futuras:** p1-persistence-and-migrations.md; p1-object-storage-and-integrity.md; p1-authentication-sessions-and-rbac.md; p1-user-administration.md; p1-audit-foundation.md.

**Decisões Proposed aceitas em P1-05:** há uma cadeia global inicialmente (não particionada), serializada por linha `nfx_audit_chain`; `audit-v1` é SHA-256 sobre JSON canônico contendo hash anterior e os campos persistidos. Trigger PostgreSQL bloqueia alteração/remoção, e a porta redige o contexto antes de persistir. A verificação é exposta na consulta administrativa; métricas/health operacionais detalhados permanecem trabalho de P3/P8.

**Decisões Proposed aceitas em P1-04:** o contrato administrativo usa `/api/users` com cursor/filtros e rotas de ação explícitas; `User.version` é controle otimista junto de locks transacionais. Reset de senha incrementa `revocation_version` e invalida sessões existentes. A troca da própria senha exige a senha atual e também revoga sessões existentes. A última conta Administrador ativa não pode ser desativada nem perder o papel, preservando uma rota administrativa recuperável. Evidência: `backend/nfx/identity/{policy,services,views}.py`, `backend/nfx/urls.py`, `backend/nfx/migrations/0005_user_administration_version.py`, `tests/unit/test_user_administration.py` e o build da shell.

### P2 — Empresas, cobertura e certificados

**Objetivo e resultado:** Administrador/Operador cadastra empresa e A1 de modo seguro; A1 inválido nunca libera coleta.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P2-01 | Empresa, CNPJ normalizado/único, imutabilidade, ativação, pausa e motivo — **implementado** (`nfx.companies`, `0006_company_lifecycle`, serviços e APIs) | P1-03, P1-05 | regras de empresas do PRD | Constraint, RBAC, unidade e integração | Desativação preserva estado |
| P2-02 | OpenCNPJ opcional e não autoritativo — **implementado** (`OpenCnpjClient`, snapshots, métricas e estados de falha) | P2-01, P0-04 | FR-COMP-004/005; BR-COMP-007/008 | Fake, timeout, conteúdo malformado e somente CNPJ | Falha não bloqueia cadastro |
| P2-03 | Upload/validação de PFX, cifragem, A1 corrente único e vencimento — **implementado** (`nfx.certificates`, `0007_certificate_lifecycle`, `nfx.collection`) | P1-05, P1-06, P2-01 | regras de certificados do PRD | Fixture sintética, senha/CNPJ inválidos, envelope, corrida e storage failure | Rejeitar antes de persistir; substituição preserva acervo |
| P2-04 | UI de empresas, fluxos, cobertura e certificado — **implementado** (`frontend/src/main.tsx`, P2-01/P2-02/P2-03) | P2-01, P2-02, P2-03 | AC-001, AC-002, AC-020, AC-021 | UI de empresa/certificado, mensagens seguras, build/lint | Segredo nunca exibido |

**Evidência P2-01/P2-02/P2-04 (empresa):** `tests/unit/test_company_lifecycle.py`,
`tests/integration/test_migrations.py`, migração `0006_company_lifecycle`, frontend lint/build e
Docker integration (18 testes) verdes em 2026-08-06. Decisões Proposed aceitas: UUID/version,
coluna de CNPJ com capacidade alfanumérica futura, dois fluxos criados independentemente, rotas
de ação sem DELETE e `OpenCnpjClient` injetável com snapshots públicos não autoritativos.

**Evidência P2-03/P2-04 (certificado):** `backend/nfx/certificates/{models,services,views}.py`,
`backend/nfx/collection/models.py`, migration `0007_certificate_lifecycle`,
`tests/unit/test_certificate_lifecycle.py`, `tests/unit/test_safe_configuration.py`,
`tests/integration/test_migrations.py` e `frontend/src/main.tsx`. A validação isolada executou
29 testes da spec/configuração, 61 testes unitários e 18 testes de integração, todos verdes; o frontend
passou lint/build e Ruff passou no backend/testes. Decisões Proposed aceitas: `cryptography`
44.0.2 com AES-256-GCM, chave mestre externa base64url de 32 bytes com versão 1, limite de 5 MiB,
estado corrente com constraints parciais de empresa/fingerprint e registro `queued` idempotente
para handoff da coleta inicial sem transporte inline.

### P3 — Jobs, scheduler, políticas e simuladores

**Objetivo e resultado:** processamento em segundo plano durável, testável e recuperável antes de adaptadores oficiais.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P3-01 | Job, scheduler, worker, lease, renovação e reclaim — **implementado** (`nfx.jobs`, `0008_durable_jobs`, comandos e testes) | P1-01, P1-05 | ADR-005; OPS-001, OPS-003, OPS-005 | Concorrência PostgreSQL, morte de worker, lease, restart e payload referencial seguro | Reprocessar idempotentemente; retry/backoff seguem P3-02 |
| P3-02 | Políticas externas, retry, backoff, jitter, cooldown e bloqueio — **implementado e validado** (`JobPolicy`, `0009_job_policies`, seleção/engine de outcomes classificados) | P3-01 | BR-COLL-002/007; OPS-006 | `make lint`, `make test-unit`, `make test-integration`, build e smoke verdes; 108 unitários, 22 integração PostgreSQL, Ruff/mypy, Django check, migração e frontend validados | Suspender bloqueado; política efetiva e referência capturada pelo job são imutáveis |
| P3-03 | Simuladores e fixtures NF-e/ADN com transporte substituível — **implementado e validado** (`nfx.adapters.simulation`, cenários gerados e handlers sintéticos) | P0-04, P3-01 | arquitetura 38 | 33 testes unitários direcionados, 108 unitários, 22 integração PostgreSQL, `make lint`, Django check/build, frontend lint/build e smoke verdes | Sem endpoint produção |
| P3-04 | Logs, métricas de job e health inicial — **implementado e validado** (`ProcessHeartbeat`, agregados read-only, `/health/operational` e logs estruturados) | P3-01 | OPS-002/004; NFR-008 | 115 testes unitários, 23 integração PostgreSQL, `make lint`, build, migração e smoke verdes | Estado degradado explícito; capacidades futuras permanecem `unavailable` |
| P3-05 | Controle manual: coleta completa, NF-e, NFS-e, retry permitido, exclusão mútua, cooldown, autorização, auditoria e UI de acompanhamento | P1-03, P1-05, P3-01, P3-02 | FR-COLL-001, FR-COLL-002, BR-COLL-003, BR-COLL-004, BR-COLL-005, BR-COLL-008, BR-COLL-009 | Browser, RBAC, execução simultânea, cooldown e auditoria | Retornar execução existente; não ignorar bloqueio |

**Specs futuras:** p3-durable-jobs-leases-and-policy-engine.md; p3-manual-collection-control.md; p3-fiscal-adapter-simulation-and-fixtures.md.

### P4 — Ingestão fiscal comum e integridade

**Objetivo e resultado:** uma unidade simulada produz payload original, documento/evento ou quarentena/conflito; cursor só avança após durabilidade.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P4-01 | Identidade fiscal, hash, documento, evento, competência e vínculos | P1-01, P1-06 | BR-INT-001, BR-INT-005, BR-INT-006, BR-INT-007, BR-INT-008, FR-DOC-001, FR-DOC-005 | Unicidade, colisão, competência e relações | Conflito sem sobrescrita |
| P4-02 | Pipeline objeto-transação-checkpoint-cursor/NSU e reconciliação | P3-01, P4-01 | BR-INT-003/004; AC-006/007/017 | Falha antes/depois de objeto, registro e cursor | Replay sem perda/duplicata |
| P4-03 | Quarentena, conflito, parcial, vazio, bloqueio e degradação | P4-02, P1-05 | BR-INT-002, BR-INT-008; PRD seção 18 | Payload malformado/desconhecido | Evidência preservada |
| P4-04 | Contrato web de status e lista mínima de documentos | P4-01, P1-06 | BR-COLL-008/009 | Contrato e browser com mock | Estados explícitos |

**Specs futuras:** p4-fiscal-document-ingestion-and-integrity.md.

### P5 — Adaptador e fluxos NF-e

**Objetivo e resultado:** NF-e recebida/emitida, XML, eventos e Ciência da Operação preservam fluxo e cursor próprios.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P5-01 | Porta NF-e, política de endpoint e distribuição simulada | P2-03, P3-02/03, P4-02 | FR-NFE-001; BR-NFE-002; ADR-006 | Contrato e destino bloqueado | Desativar política/fluxo |
| P5-02 | Fluxos recebida/entrada e emitida/saída independentes | P5-01 | FR-NFE-001/003/004; BR-NFE-001 | Cursor por fluxo, replay e restart | Cursor preservado |
| P5-03 | Ciência da Operação, XML completo e eventos vinculados | P5-02 | FR-NFE-002, FR-NFE-003, FR-NFE-004, BR-NFE-003 | Manifestação e evento idempotentes | Nunca repetir logicamente |

**Specs futuras:** p5-nfe-distribution-and-manifestation.md.

### P6 — Adaptador e fluxos NFS-e/ADN

**Objetivo e resultado:** ADN distingue cobertura, vazio e indisponibilidade; classifica tomada, prestada e eventos.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P6-01 | Porta ADN, distribuição por ator, NSU e política de leiaute | P2-03, P3-02/03, P4-02 | FR-NFSE-001; ADR-006 | Contrato e simulador | Adaptador isolado |
| P6-02 | Tomada/prestada/eventos, substituições e cobertura visível | P6-01 | FR-NFSE-002, FR-NFSE-003, BR-NFSE-001, BR-NFSE-002, BR-NFSE-003, AC-008, AC-018 | Vazio versus cobertura versus indisponível | Quarentena sem descarte |

**Specs futuras:** p6-nfse-adn-distribution-and-coverage.md.

### P7 — Consulta, downloads e artefatos

**Objetivo e resultado:** acervo pesquisável e baixável; PDF é derivado, versionado e nunca substitui XML/original.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P7-01 | Busca, filtros, detalhes e UI de eventos | P4-01, P4-04 | FR-DOC-001, FR-DOC-002, FR-DOC-003, FR-DOC-004, FR-DOC-005, BR-DOC-001, BR-DOC-002 | Índices, contrato e browser | Consulta não altera acervo |
| P7-02 | Download individual autorizado e auditado | P1-03/04, P7-01 | FR-ART-001; NFR-006 | Negado, auditado e stream seguro | Falhar fechado |
| P7-03 | Jobs de DANFE/DANFSe, renderer versionado e regeneração | P3-01, P4-01, P7-01, biblioteca de renderer resolvida | FR-ART-002, FR-ART-003, BR-ART-001, BR-ART-002, BR-ART-003 | Renderer falho e idempotência | XML permanece disponível |

**Specs futuras:** p7-document-consultation-and-individual-download.md; p7-danfe-danfse-rendering.md.

### P8 — ZIP, dashboard e elegibilidade de retenção

**Objetivo e resultado:** usuário exporta e acompanha acervo; Administrador vê elegibilidade e prévia de exclusão, mas exclusão definitiva permanece desabilitada.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P8-01 | ZIP assíncrono, filtros congelados, expiração e autorização | P3-01, P7-01, P7-02, P7-03 | FR-ZIP-001, FR-ZIP-002, FR-ZIP-003, BR-ZIP-001, BR-ZIP-002, BR-ZIP-003, BR-ZIP-004, AC-012 | ZIP parcial, terceiro negado e traversal | Origem nunca removida |
| P8-02 | Dashboard, drill-down e saúde administrativa | P2–P7, P3-04 | FR-DASH; FR-OPS; BR-OPS | Período, agregação, browser e RBAC | Métrica ausente = degradado |
| P8-03 | Cálculo de elegibilidade, bloqueio por retenção e prévia administrativa do escopo/artefatos, sem excluir | P1-05, P4-01, P7-03 | RET-001, RET-002, RET-003, RET-004, RET-007, RET-008 | Datas limite, bloqueio e prévia imutável | Exclusão continua desabilitada |

**Specs futuras:** p8-zip-export.md; p8-dashboard-and-operational-health.md; p8-retention-eligibility.md.

### P9 — Operação, recuperação, exclusão habilitada e piloto

**Objetivo e resultado:** runtime interno, HTTPS, backup/restore comprovado e, somente então, exclusão definitiva habilitada; hardening e piloto encerram o MVP.

| ID | Resultado e mudanças | Dependências | PRD/arquitetura | Testes e evidência | Falha/rollback |
|---|---|---|---|---|---|
| P9-01 | Runtime, reverse proxy, TLS autoassinado e limites de recurso | P1-01, P1-03, P3-04 | SEC-006, SEC-008, ADR-013 | HTTPS, exposição mínima e health | Reverter imagem/config |
| P9-02 | Backup local, retenção 7/4/12 e restore de banco, objetos, certificados cifrados e chave | P1-06, P2-03, P3-04 | OPS-BKP-001, OPS-BKP-002, OPS-BKP-003, OPS-BKP-004, OPS-BKP-005, OPS-BKP-006, BR-BKP-001, SEC-009, ADR-012 | Restore isolado e descriptografia comprovada | Restore até último backup local |
| P9-03 | Exclusão definitiva de documento elegível, confirmação, motivo e tratamento coerente de artefatos | P8-03, P9-02 | RET-005, RET-006, RET-008, AC-015 | Exclusão, auditoria e artefatos órfãos | Desabilitada até restore aprovado; estado recuperável |
| P9-04 | Hardening e threat review final | P5, P6, P7, P8, P9-01, P9-02, P9-03 | arquitetura 33, arquitetura 36, arquitetura 40 | Segurança, fault injection e capacidade | Degradação explícita |
| P9-05 | Piloto interno e homologação segregada | P5, P6, P8, P9-01, P9-02, P9-03, P9-04 | AC-024, AC-025, NFR-003 | Evidências técnicas e dados permitidos | Pausar fluxos sem apagar acervo |

**Specs futuras:** p9-runtime-and-https.md; p9-backup-and-restore.md; p9-controlled-deletion.md; p9-hardening.md; p9-internal-pilot-and-homologation.md.

## 11. Dependências, caminho crítico e paralelismo

**Caminho crítico:** P0-01/02/03 → P1-01/02/03/05/06 → P2-03 e P3-01/02/03 → P4-01/02 → P5/P6 → P7 → P8-03 → P9-02 → P9-03 → P9-04/05. P9-01 começa em paralelo após P1-01/P1-03/P3-04.

| Trabalho paralelo | Após | Ponto de integração |
|---|---|---|
| Shell web, RBAC UI, administração de usuários e auditoria | P1-02/03 | Contratos HTTP estáveis |
| Empresas/certificados | P1 | Certificado cria job, não coleta inline |
| Jobs/simuladores | P1 | Porta de ingestão comum |
| NF-e e ADN | P4 | Adaptadores e cursores independentes |
| Busca/PDF | P4 | Contrato de documento/artefato |
| Dashboard | P3 e dados posteriores | Consultas agregadas |

Nenhuma UI é proprietária de estado durável. Adaptadores não compartilham cursor, NSU, lease ou estado privado.

## 12. Estratégia de testes e validação

- P0: build, lint, smoke e bloqueio de produção fiscal.
- P1: unitários, integração PostgreSQL/MinIO, migrações, segurança, sessões, RBAC e auditoria.
- P3/P4: testes de propriedade/invariantes, concorrência, leases, idempotência, retry, cooldown, restart e injeção de falha.
- P5/P6: contratos de adaptador, fixtures sintéticas e simuladores; homologação é atividade separada.
- P7/P8: browser, downloads, PDF falho, ZIP, filtros, retenção e exclusão.
- P9: TLS, espaço cheio, indisponibilidade de banco/objeto/fonte, backup e restore.

Testes automatizados normais não usam certificado real, CNPJ de cliente, XML real, credencial real ou endpoint de produção.

## 13. Estratégia de segurança fiscal

1. Segredos e guardas de rede antes de certificados/adaptadores.
2. RBAC e auditoria antes de qualquer ação crítica.
3. Constraints, hash, objeto confirmado e cursor antes de coleta.
4. Jobs/leases antes de scheduler.
5. Original preservado antes de PDF/ZIP.
6. Retenção antes de exclusão.
7. Recuperação da chave antes de declarar backup pronto.

Invariantes obrigatórias: cursor/NSU pós-durabilidade; zero perda silenciosa; zero duplicata lógica; estado por empresa/fluxo; manifestação idempotente; conflito/quarentena explícitos; jobs retomáveis; cooldown seguro; PDF não substitui XML; auditoria permanente; segredo fora de logs/fixtures.

## 14. Banco e migrações

P1 introduz tooling, baseline, banco de teste e estratégia de upgrade/forward recovery. Toda migração inclui constraints, índices necessários, teste de instalação limpa, teste de upgrade e recuperação segura. Mudança irreversível exige backup e correção progressiva, não rollback destrutivo.

**Decisão Proposed aceita em P1-01:** o baseline físico é `nfx.0001_schema_contract`, um único metadado operacional sem entidades de MVP; sua chave singleton, constraints e índice são verificados em integração. `nfx_migrate` serializa com advisory lock PostgreSQL e `schema_status`/readiness recusam schema NFX ausente ou adiantado incompatível sem divulgar credenciais. As decisões de ID/timestamps das entidades de domínio ficam com as respectivas specs.

**Decisões Proposed aceitas em P1-06:** `Artifact` usa UUID interno, chave física opaca `artifacts/<uuid>/v1`, SHA-256 registrado por objeto, limite inicial de 50 MiB e spool de 1 MiB. PostgreSQL tem uma constraint parcial de uma referência finalizada por chave lógica; retry com bytes idênticos é idempotente e bytes distintos conflitam. A reconciliação só sinaliza pendências, ausências, divergências e órfãos — não remove objetos nem corrige hash.

**Decisões Proposed aceitas em P1-02/P1-03/P1-07:** identidade usa e-mail `casefold` único, Argon2id, token opaco aleatório de 256 bits persistido somente como SHA-256 e expiração deslizante condicional de 30 minutos. O primeiro Admin é criado exclusivamente pelo comando idempotente `bootstrap_admin` com segredo externo. Login é JSON em `/api/auth/*`, protegido por CSRF para mutações, com throttle HMAC(e-mail/IP) e resposta uniforme. `authorize()` central é fail-closed e é a extensão obrigatória para HTTP, jobs e downloads; a shell React localizada somente guia a navegação.

P4 introduz identidade, hash, cursores, transações e unicidade antes de qualquer adaptador. Não há migração legada. O bootstrap cria somente o primeiro Administrador por segredo externo e dados mínimos de política.

## 15. Sequência de frontend

- P1: login, timeout, shell e navegação por papel.
- P2: empresas, cobertura, fluxos e certificados.
- P3/P4: estado de jobs/coletas, erro, retry, bloqueio, conflito e quarentena.
- P5/P6: progresso por família e fluxo.
- P7: busca, filtros, detalhe, XML e PDF.
- P8: ZIP, dashboard, auditoria, retenção e prévia de elegibilidade sem exclusão.
- P9: saúde, backup/restore, exclusão liberada somente após restore e operação final.

O frontend pode usar mocks até estabilizar contratos. A validação final sempre confirma autorização no servidor.

## 16. Observabilidade, backup e restore

P3 introduz logs redigidos, correlação, métricas e health. P8 expõe dashboard/saúde. P9 implementa TLS, limites, backup diário, retenção 7/4/12 e restore trimestral.

Restore obrigatório cobre banco, objetos, certificados cifrados, estado/cursor e chave necessária. Backup local prova recuperação de erro lógico, não de desastre físico; a limitação Accepted não bloqueia as demais fases.

## 17. Mapa de specs

| Spec proposta | Fase | Dependências | Verificação |
|---|---|---|---|
| p0-project-foundation.md | P0 | Scaffold | Build e processos |
| p0-safe-configuration-and-test-isolation.md | P0 | Fundação | Produção fiscal bloqueada |
| p1-persistence-and-migrations.md | P1 | P0 | Migração limpa, upgrade e forward recovery |
| p1-object-storage-and-integrity.md | P1 | P0 | Hash, pendência/finalização e reconciliação |
| p1-authentication-sessions-and-rbac.md | P1 | P0 | Login, timeout, RBAC e AC-003/004/022 |
| p1-user-administration.md | P1 | P1-02/P1-03/P1-05 | Gestão de usuários e revogação imediata |
| p1-audit-foundation.md | P1 | P1-01/P1-03 | AC-014 e eventos imutáveis |
| p2-company-lifecycle-and-public-enrichment.md | P2 | P1 | AC-001/019/020 |
| p2-certificate-lifecycle-and-envelope-encryption.md | P2 | P1 | AC-002/021 |
| p3-durable-jobs-leases-and-policy-engine.md | P3 | P1 | AC-006/007/017 |
| p3-fiscal-adapter-simulation-and-fixtures.md | P3 | P0/P3 | Sem produção |
| p4-fiscal-document-ingestion-and-integrity.md | P4 | P2/P3 | Cursor pós-durabilidade e BR-INT |
| p5-nfe-distribution-and-manifestation.md | P5 | P4 | NF-e, eventos e manifestação |
| p6-nfse-adn-distribution-and-coverage.md | P6 | P4 | ADN, cobertura e estados |
| p7-document-consultation-and-individual-download.md | P7 | P4 | Busca, filtros, detalhe e XML |
| p7-danfe-danfse-rendering.md | P7 | P3/P4/P7-01; biblioteca Open resolvida | Renderer, versão e regeneração |
| p8-zip-export.md | P8 | P7 | ZIP parcial, expiração e autorização |
| p8-dashboard-and-operational-health.md | P8 | P3 e dados disponíveis | Dashboard, drill-down e saúde |
| p8-retention-eligibility.md | P8 | P4/P7 | Elegibilidade e prévia sem exclusão |
| p9-runtime-and-https.md | P9 | P1/P3 | TLS, proxy, limites e health |
| p9-backup-and-restore.md | P9 | P1-06/P2-03/P3-04 | Restore comprovado de banco, objetos e chave |
| p9-controlled-deletion.md | P9 | P8-03/P9-02 | Exclusão somente após restore |
| p9-hardening.md | P9 | capacidades MVP e P9-01/P9-02/P9-03 | Threat review e testes de falha |
| p9-internal-pilot-and-homologation.md | P9 | P5/P6/P8/P9-01/P9-02/P9-03/P9-04 | Homologação segregada e piloto |

## 18. Rastreabilidade do PRD

A matriz abaixo usa somente identificadores existentes no PRD. Itens transversais aparecem em mais de uma linha quando protegem mais de uma capacidade.

| Identificadores exatos do PRD | Work items |
|---|---|
| FR-AUTH-001, FR-AUTH-005, FR-AUTH-006, FR-AUTH-007, BR-AUTH-001 | P1-02 |
| FR-AUTH-002, FR-AUTH-003, FR-AUTH-004, BR-AUTH-002 | P1-04 |
| SEC-001, SEC-002, SEC-003 | P1-02 |
| SEC-004, SEC-005 | P1-03, P1-04 |
| SEC-006, SEC-008 | P9-01 |
| SEC-007 | P0-02, P1-05, P9-04 |
| SEC-009 | P9-02 |
| FR-COMP-001, FR-COMP-002, FR-COMP-003, BR-COMP-001, BR-COMP-002, BR-COMP-003, BR-COMP-004, BR-COMP-005, BR-COMP-006 | P2-01, P2-04 |
| FR-COMP-004, FR-COMP-005, BR-COMP-007, BR-COMP-008 | P2-02 |
| FR-CERT-001, FR-CERT-002, BR-CERT-001, BR-CERT-002, BR-CERT-003, BR-CERT-004, BR-CERT-005, BR-CERT-006, BR-CERT-007 | P2-03, P2-04, P9-02 |
| FR-COLL-001, BR-COLL-001 | P2-03, P3-05 |
| FR-COLL-002, BR-COLL-002, BR-COLL-007, BR-COLL-010 | P3-01, P3-02 |
| BR-COLL-003, BR-COLL-004, BR-COLL-005, BR-COLL-008, BR-COLL-009 | P3-01, P3-05, P4-04 |
| BR-COLL-006 | P4-03, P6-02 |
| FR-NFE-001, FR-NFE-003, FR-NFE-004, BR-NFE-001, BR-NFE-002 | P5-01, P5-02 |
| FR-NFE-002, BR-NFE-003 | P5-03 |
| FR-NFSE-001, FR-NFSE-002, FR-NFSE-003, BR-NFSE-001, BR-NFSE-002, BR-NFSE-003 | P6-01, P6-02 |
| BR-INT-001, BR-INT-002, BR-INT-003, BR-INT-004, BR-INT-005, BR-INT-006, BR-INT-007, BR-INT-008 | P1-06, P3-01, P4-01, P4-02, P4-03 |
| FR-DOC-001, FR-DOC-002, FR-DOC-003, FR-DOC-004, FR-DOC-005, BR-DOC-001, BR-DOC-002 | P4-01, P7-01 |
| FR-ART-001 | P7-02 |
| FR-ART-002, FR-ART-003, BR-ART-001, BR-ART-002, BR-ART-003 | P7-03 |
| FR-ZIP-001, FR-ZIP-002, FR-ZIP-003, BR-ZIP-001, BR-ZIP-002, BR-ZIP-003, BR-ZIP-004 | P8-01 |
| FR-DASH-001, FR-DASH-002, FR-DASH-003, BR-DASH-001 | P8-02 |
| FR-OPS-001, BR-OPS-001 | P3-04, P8-02, P9-01 |
| RET-001, RET-002, RET-003, RET-004, RET-007 | P8-03 |
| RET-005, RET-006, RET-008 | P9-03 |
| AUD-001, AUD-002, AUD-003, AUD-004, AUD-005, AUD-006, AUD-007, AUD-008, AUD-009, AUD-010 | P1-05; transversalmente P1-04, P2-01, P2-03, P3-05, P7-02, P7-03, P8-01, P9-03 |
| OPS-BKP-001, OPS-BKP-002, OPS-BKP-003, OPS-BKP-004, OPS-BKP-005, OPS-BKP-006, BR-BKP-001 | P9-02 |
| OPS-001, OPS-002, OPS-003, OPS-004, OPS-005, OPS-006, OPS-007 | P0-01, P3-01, P3-02, P3-04, P9-01, P9-04 |
| NFR-001, NFR-002 | P1-07, P2-04, P7-01, P8-02 |
| NFR-003 | P9-05 |
| NFR-004, NFR-005 | P3-01, P4-02 |
| NFR-006 | P1-03, P7-02, P8-01 |
| NFR-007 | P0-04, P9-01 |
| NFR-008 | P3-04, P4-03, P6-02, P8-02 |

### Critérios de aceitação

| Critério | Work items |
|---|---|
| AC-001 | P2-01, P2-04 |
| AC-002 | P2-03, P2-04 |
| AC-003 | P1-02, P1-04 |
| AC-004 | P1-03, P1-04 |
| AC-005 | P5-02, P6-02, P7-01 |
| AC-006 | P3-01, P4-02, P5-03 |
| AC-007 | P3-01, P4-02 |
| AC-008 | P4-03, P6-02 |
| AC-009 | P4-03, P6-02 |
| AC-010 | P7-02, P7-03 |
| AC-011 | P7-01 |
| AC-012 | P8-01 |
| AC-013 | P8-02 |
| AC-014 | P1-05 |
| AC-015 | P8-03, P9-02, P9-03 |
| AC-016 | P9-02 |
| AC-017 | P3-01, P4-02 |
| AC-018 | P6-02 |
| AC-019 | P2-02 |
| AC-020 | P2-01, P2-04 |
| AC-021 | P2-03 |
| AC-022 | P1-02, P1-04 |
| AC-023 | P1-07 |
| AC-024 | P3-01, P9-01, P9-04, P9-05 |
| AC-025 | P9-05 |

## 19. Rastreabilidade da arquitetura

| Decisão/seção | Trabalho |
|---|---|
| ADR-001/002; arquitetura 10–12 | P0-01/05, P1-07 |
| ADR-003/004; arquitetura 15–17 | P0-03, P1-01/06, P4 |
| ADR-005/007; arquitetura 19–22 | P3-01/02, P4-02 |
| ADR-006; arquitetura 23–24 | P3-03, P5, P6 |
| ADR-008/009; arquitetura 25–26 | P0-02, P1-02/03/04, P2-03 |
| ADR-010; arquitetura 27 | P1-05 e auditoria transversal |
| ADR-011; arquitetura 29–30 | P7-03, P8-01 |
| arquitetura 31–32 | P4-03, P8-03 |
| arquitetura 33–38 | P0-02/04, P1, P3-03, P9-01/02/04 |
| ADR-012; arquitetura 35–36 | P8-02, P9-02/03 |
| ADR-013; arquitetura 34 | P9-01 |
| arquitetura 39–41 | P3, P4, P9 |

## 20. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Perda fiscal | P1-06, P3-01 e P4-02 antes de adaptadores |
| Duplicidade/replay | Unicidade, hash, idempotência e testes P4–P6 |
| Mudança fiscal | Políticas versionadas, simuladores e homologação isolada |
| Certificado exposto | Cifragem precoce, redaction e restore da chave |
| Fonte indisponível | Cursor persistido, retry/cooldown e estados explícitos |
| Backup local insuficiente | Limitação Accepted, restore comprova o limite |
| TLS autoassinado | Limitação Accepted; CA interna Deferred |
| Big bang | Fases verticais e contratos progressivos |

## 21. Decisões Open, Deferred e Blocked

| Item | Status | Impacto |
|---|---|---|
| Biblioteca DANFE/DANFSe | Open | Não bloqueia fases anteriores; bloqueia apenas o início da spec e implementação P7-03 |
| Endpoints, limites e leiautes vigentes | Open | P5/P6 usam simuladores; homologação confirma |
| CA interna/certificado confiável | Deferred | Não bloqueia TLS do MVP |
| Backup fisicamente separado | Deferred | Não bloqueia restore local |
| Broker externo/escalonamento horizontal | Deferred | Não bloqueia jobs PostgreSQL |
| Backup local versus requisito original | Accepted exception | Risco visível, sem bloqueio |

Não há item Blocked.

## 22. Definição de pronto

Uma spec pode ser criada quando o item tem objetivo, escopo, dependências concluídas, proprietário de estado, requisitos rastreáveis, testes, fixtures permitidas, comportamento de falha e evidência. Specs fiscais exigem simulador e bloqueio de produção antes de homologação. A spec de exclusão controlada também exige evidência concluída de P9-02; essa dependência não é um gate para as demais specs.

## 23. Definição de concluído

Um item termina quando código e migrações necessárias passam nos testes definidos; segurança, autorização, observabilidade/redaction e recuperação aplicáveis são verificadas; a evidência está ligada aos requisitos/decisões; e o comportamento de rollback ou falha segura foi exercitado. Exclusão definitiva só é concluída após comprovação de restore de P9-02.

## 24. Critérios de conclusão do MVP

1. AC-001 a AC-025 têm evidência.
2. Todo requisito relevante e ADR Accepted mapeia para item concluído.
3. Cursor, job, lease, retry, conflito e quarentena foram testados sob interrupção.
4. Original/XML é preservado; PDF/ZIP não o substituem.
5. Três papéis têm autorização server-side validada.
6. Elegibilidade e prévia de exclusão funcionam sem remover dados; exclusão definitiva só fica habilitada depois de P9-02 comprovar restore.
7. Restore recupera banco, objetos, A1 cifrado e chave dentro do limite local conhecido.
8. HTTPS, health, logs seguros, métricas e dashboard administrativo estão ativos.
9. Homologação, se executada, é segregada.
10. Piloto demonstra operação para cerca de 200 empresas sem limite funcional artificial.

## 25. Handoff para criação de specs

Criar specs na ordem da seção 17, citando os IDs deste backlog. Cada spec cobre uma fatia, preserva ADRs Accepted, não reabre decisões resolvidas e explicita testes/evidências. Decisões Open bloqueiam apenas integrações diretamente afetadas.

Depois de modificações de código, atualizar Graphify conforme AGENTS.md. Este documento não exige alteração de código ou Graphify.

**Template hygiene (issue 0007, completed 2026-08-09):** `.env.example` contains only invalid
external placeholders, mounted-file alternatives, unique settings, and simulator-only fiscal
values. Configuration tests cover missing, placeholder, malformed, and conflicting sources.
