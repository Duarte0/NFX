# Plano de implementação — NFX INOV

## Controle e baseline

| Campo | Valor |
|---|---|
| Produto | NFX INOV |
| Atualizado em | 2026-08-10 |
| Fontes | Código/migrações, testes, PRD.md, ARCHITECTURE.md, specs/ e issues/ |
| Status geral | Fundação, plataforma de processamento, P4-01/P4-02/P4-03/P4-04, P8-01/P8-03, P9-01 e P9-02 concluídos e verificados; P7-03/P9-03..P9-05 permanecem pendentes. |

O código e as migrações são a baseline de implementação; testes são a evidência de comportamento verificado. PRD e arquitetura continuam a definir o comportamento pretendido. Este plano substitui a premissa anterior de que o repositório era apenas um scaffold.

## Estado consolidado

### Concluído e verificado

| Marco | Evidência principal | Verificação atual |
|---|---|---|
| P0 — fundação/configuração/isolamento | Django + React, Compose isolado, guardas de destino fiscal, configuração tipada | Em 2026-08-09: build/lint com perfil sintético, 121 unitários, 23 integrações PostgreSQL/MinIO e `make smoke` verdes. |
| P0 — higiene do template de ambiente | `.env.example` com placeholders externos, entradas únicas e simulador local | Issue 0007: testes de configuração verificam placeholders, fontes montadas/conflitantes, ausência, formato inválido e ausência de valores utilizáveis no template. |
| P1 — persistência, objetos, identidade, RBAC, auditoria e administração | migrações `0001`–`0005`; módulos `artifacts`, `identity`, `audit`; shell React | mesmas suites; migrações aplicadas até `0011_document...` e `schema_status` compatível na integração. |
| P2 — empresa, enriquecimento e certificado A1 | `companies`, `certificates`, migrações `0006`–`0007`, auditoria e UI | suites unitária e de integração acima. |
| P3-01/P3-02 — jobs, leases e políticas | `jobs`, migrações `0008`–`0009`, worker e scheduler | concorrência, reclaim, retry/cooldown/bloqueio e política capturada cobertos. |
| P3-03 — simuladores fiscais | `adapters/simulation.py`, cenários NF-e/ADN determinísticos e sem rede | testes de cenário, replay e boundary do job cobertos. |
| P3-04 — observabilidade inicial | `0010_process_heartbeats`, agregados, `/health/operational` | health, heartbeats e logs estruturados cobertos. |

P4-01 adicionou a identidade e persistência base de documentos/eventos em `documents`, com referências imutáveis a artefatos. P4-02 adicionou pipeline/cursor, P4-03 adicionou a matriz durável de estados/recovery e P4-04 adicionou a API/UI mínima de status/lista; exportações, retenção e renderização continuam fora desta entrega. O simulador genérico continua infraestrutura de teste; o issue 0014 adicionou a porta semântica P6 sobre ele sem habilitar transporte oficial.

O incremento transversal de frontend do issue 0011 também está concluído: `main.tsx` é somente
bootstrap, `App.tsx` compõe o shell e as funcionalidades, e `shared/http.ts` é a fronteira
única para credenciais same-origin, CSRF, serialização e erros seguros. A extração preserva os
contratos e estados visíveis P1–P4; não altera backend, banco, endpoints ou dependências de
runtime. A próxima implementação de produto continua sendo P5 follow-up/P7.

### Implementado, mas com acompanhamento documental/operacional pendente

1. P1-04 está implementado e testado; a passagem de specs removeu o falso blocker Graphify de `specs/p1-user-administration.md`.
2. A UI P1/P2 é compilada e lintada, mas não há runner/teste automatizado de interação frontend no repositório. Não reabrir as entregas concluídas por isso; `P3-05` já exige cobertura HTTP/UI para o novo fluxo de coleta e deve estabelecer evidência de regressão para as interações que tocar.
3. O contrato `make build` foi corrigido no issue 0008: o recipe encapsula somente valores sintéticos locais para o check Django, mantém o fail-closed do loader e executa o frontend depois do check, sem serviços ou migrations.
4. A integração passa com cinco avisos externos de depreciação `botocore` (`datetime.utcnow`); não há falha funcional, mas a atualização/mitigação deve ser considerada na manutenção de dependências.

### Pendente / parcialmente implementado

| Prioridade | Item e status | Resultado / critério de conclusão | Dependências e riscos |
|---|---|---|---|
| P3 | P3-05 Controle manual de coleta — **concluído, issue 0005** | `nfx.collection` persiste execuções e estado independente por família; comandos manual/retry/automático validam RBAC, certificado, fluxo, cooldown, bloqueio e política, enfileiram jobs sintéticos idempotentes, auditam e expõem HTTP/UI. | Migração `0012_companyflow_blocked_reason_and_more`; sem transporte fiscal ou resultado documental antes de P4. |
| P0 | P4-01 Identidade fiscal e persistência — **concluído, issue 0006** | Migração `0011`, modelos/serviços para documento, evento, competência, hashes e vínculos; constraints/índices impedem duplicata lógica e preservam conflito. | P4-02 continua dona de unidade, checkpoint e cursor; sem avanço de coleta nesta entrega. |
| P0 | P4-02 Pipeline durável e cursor — **concluído, issue 0009** | Migration `0013`, páginas/unidades/checkpoints, objeto antes do banco, replay/conflito/quarentena, progressão monotônica, reconciliação e ponte de execução de coleta; integração isolada com simuladores sintéticos. | P4-01 e P3-01; P4-03 adiciona a classificação operacional consumida por este pipeline. |
| P1 | P4-03 Estados de falha — **concluído, issue 0012** | Outcome/recovery versionados distinguem vazio válido, cobertura, indisponibilidade, retry, cooldown, bloqueio, malformado, parcial, quarentena e conflito; cursor/NSU só avançam com tratamento terminal. | P4-02, auditoria; migration `0014_ingestion_failure_state_contract`. |
| P1 | P4-04 Contrato mínimo de status/lista — **concluído, issue 0010** | `/api/documents` e a seção `#documentos` exibem metadados limitados, estados explícitos, paginação e resultados de quarentena/conflito sem inferir sucesso de vazio. | P4-01/P4-02; consome a matriz operacional P4-03 sem criar estado paralelo. |
| P1 | Correção do contrato de build — **concluída, issue 0008** | `docs/DEVELOPMENT.md`, `Makefile`, testes de fronteira e spec P0 deixam explícito/encapsulam o perfil exigido, com comando de checkout limpo reproduzível sem segredo versionado. | Não alterar comportamento fail-closed nem valores de produção. |

## Marcos posteriores, ordenados por dependência

| Marco | Status | Resultado e critérios | Dependências |
|---|---|---|---|
| P5 NF-e | **P5-01/P5-02/P5-03 concluídos, issues 0013/0020/0022** | Porta semântica e simulador NF-e bounded para entrada/saída, Ciência, XML completo, eventos e manifestação, com jobs idempotentes, evidência original/XML, vínculo de manifestação a NF-e compatível, recovery de pai ausente e auditoria/métricas seguras. Transporte real permanece Open até homologação. Ver `p5-nfe-distribution-and-manifestation.md`. | P4-02, P2-03, P3-02/03. |
| P6 NFS-e/ADN | **P6-01/P6-02 concluídos, issue 0014** | Adapter semântico simulator-only, cobertura versionada, distribuição por ator/fluxo/NSU, tomada/prestada/eventos/substituições, handoff ao P4, auditoria/métricas/UI segura; sem integrações municipais ou transporte oficial. Ver `p6-nfse-adn-distribution-and-coverage.md`. | P4-02, P2-03, P3-02/03. |
| P7 consulta/download | **P7-01/P7-02 concluídos, issue 0015** | Busca bounded com filtros aprovados, cursor opaco, detalhe/eventos e download individual RBAC/auditado com verificação de digest/tamanho. PDF continua fora. Ver `p7-document-consultation-and-individual-download.md`. | P4-01/P4-04; P5/P6 ampliam a cobertura. |
| P7 PDF | **blocked localmente** | DANFE/DANFSe versionado, isolado e regenerável. | P4-01/P7-01 e seleção de renderer; a decisão de biblioteca continua Open. |
| P8 ZIP/dashboard/retenção | **P8-01 concluído no issue 0021; P8-02 slice inicial concluído no issue 0018; P8-03 concluído no issue 0019** | Exportação assíncrona congela filtros/itens P7, compõe ZIP com verificação de artefatos, estados parciais explícitos, RBAC, expiração/cleanup de temporários e UI de progresso. Dashboard read-only e retenção calculate-on-read permanecem conforme seus slices. | Consulta/download; PDF só é necessário quando existir como artefato selecionado; fontes P5–P7, rendering e backup continuam capacidades independentes. |
| P9 runtime/restore/exclusão/piloto | **P9-01 concluído no issue 0016; P9-02 concluído no issue 0017; P9-03/P9-04/P9-05 pendentes** | Runtime HTTPS interno e backup/restore local verificável com schema operacional, manifestos, retenção 7/4/12, status Admin-only e guardas de restore isolado; exclusão somente após restore, hardening e piloto segregado continuam pendentes. | P9-03 permanece bloqueado até evidência de restore P9-02; backup fisicamente separado é Deferred. |

## Sequência executável

```text
Agora: P5 NF-e follow-up / P7 ──────────┐
                                       ├─ P4-01 → P4-02 → P4-03 → P4-04
Correção do contrato de build ──────────┘                 │
                                                           ├─ P5 NF-e
                                                           ├─ P6 ADN (concluído)
                                                           └─ P7 consulta → P8 → P9
```

P3-05, P4-01, P4-02, P4-03 e P4-04 estão concluídos. A coleta manual deve usar o mesmo pipeline P4 quando passar
de resultados sintéticos a resultados fiscais persistidos. Não duplicar cursor, idempotência,
quarentena ou estado de fluxo nos adaptadores.

O issue 0013 concluiu o incremento P5-01: `nfx.adapters.nfe` valida a solicitação semântica,
mantém received/issued independentes no simulador, mapeia outcomes bounded e chama somente
`ingest_page` para persistência. O issue 0020 concluiu P5-02 com Ciência, XML completo e eventos,
jobs `nfe.science`/`nfe.complete_xml`, evidência original antes de parsing e vínculo de eventos
via P4. O issue 0022 concluiu P5-03 com `NFeManifestation`, o job `nfe.manifestation`,
simulador replayável, estados seguros para pai ausente/incompatível e migração `0017`; nenhum
transporte oficial foi habilitado.

O issue 0014 concluiu P6-01/P6-02: `nfx.adapters.adn` valida a solicitação por empresa,
ator, fluxo e NSU, mantém históricos independentes, persiste snapshots seguros de cobertura,
classifica documentos/eventos/substituições e chama somente o owner P4 para artefatos,
identidade, recovery e checkpoint. A guarda de NSU não monotônico permanece no pipeline, e
nenhum transporte oficial ou municipal foi habilitado.

## Decisões, inconsistências e riscos registrados

| Tema | Registro / impacto |
|---|---|
| Status de P0 | O issue 0008 fechou a lacuna de `make build`: o recipe usa somente valores sintéticos locais, sem alterar o boot fail-closed, o template externo ou a capacidade fiscal. A discrepância de valores literais no template foi corrigida no issue 0007; qualquer uso externo anterior continua sujeito a rotação fora do repositório. |
| Status de P3-04 | A passagem de specs corrigiu `p3-fiscal-adapter-simulation-and-fixtures.md`: P3-04 pertence à spec canônica de jobs e está concluído, com migração `0010` e testes como evidência. |
| P4-03 | A migration `0014` adiciona outcome/recovery seguros a execução, página e unidade. A classificação mantém `valid_empty`, `no_coverage`, `unavailable`, `temporary_failure`, `cooldown`, `permanent_failure`, `malformed`, `partial`, `quarantine` e `conflict` separados; falhas de posição usam `reconcile` e nunca avançam o cursor. |
| P1-04 | Índice marca a spec concluída, mas texto de fase conserva blocker Graphify; tratá-lo como pendência de metadado, não de entrega. |
| Transporte real NF-e/ADN | Endpoints, leiautes, limites e homologação continuam Open; bloqueiam somente transportes reais, nunca a implementação com simuladores. |
| DANFE/DANFSe | Seleção de renderer é decisão requerida antes de P7-03; impacto local. Não escolher sem avaliação de licença, isolamento e reprodução. |
| Backup/exclusão | Backup local e TLS autoassinado são limitações Accepted; backup fisicamente separado e CA confiável são Deferred. Exclusão definitiva fica bloqueada até restore comprovado. |
| Árvore de trabalho | Há mudanças não commitadas em código, testes, documentação, dependências e Graphify que não pertencem a esta passagem. Elas foram preservadas; a verificação acima reflete a árvore atual, não uma revisão de autoria. |
| Cobertura frontend | Não há dependência/configuração de Vitest, Playwright, Cypress, Selenium ou equivalente. O contrato P3-05 foi coberto pela compilação/lint da UI e pelos endpoints HTTP; um runner de browser permanece uma melhoria operacional separada. |

## Trabalho de specs e operação que resta

- Passagem de specs validou as 25 specs ativas sem lacunas de backlog: P0/P1/P3 foram reconciliados, P5-01/P5-02/P5-03 foram implementados nos issues 0013/0020/0022, P6-01/P6-02 no issue 0014 e P8-03 no issue 0019. Não foram encontrados TODO/FIXME/placeholder de domínio, nem duplicação de implementação que alterem esse backlog; `exports` permanece boundary sem implementação e `retention` agora tem seu slice P8-03.
- Issue 0007 corrigiu a higiene de `.env.example`; valores que tenham sido usados fora de testes descartáveis continuam potencialmente comprometidos e devem ser rotacionados fora do repositório.
- P4-03 concluído: manter a matriz de outcome/recovery como contrato único; novos adaptadores devem mapear respostas à classificação antes de alterar qualquer cursor/checkpoint.
- Antes de P5/P6 reais: decidir/adquirir evidência de endpoints, certificados, leiautes e homologação segregada; isso é decisão externa, não assumir valores.
- P9-01 entregue no issue 0016: runtime usa proxy HTTPS único, serviços internos sem portas publicadas, imagem comum por processo, volumes persistentes e runbook de upgrade/rollback. P9-02 entregue no issue 0017: captura lógica determinística, objetos verificados, probes A1 cifrados, manifestos hashados, retenção independente, restore isolado e status Admin-only. Antes de P9-03: repetir o exercício conforme runbook e preservar a evidência operacional.
- P8-01 concluído no issue 0021: exportação mantém seleção congelada, itens e estado em PostgreSQL,
  gera o ZIP em artifact temporário verificado, aplica limites bounded e nunca altera artefatos
  fiscais; download revalida ownership/admin, estado e expiração.
- P8-02 inicial entregue sem materialização: agregação calculate-on-read e capacidades futuras
  permanecem `unavailable` até seus slices proprietários; ampliar cards somente após as fontes
  correspondentes existirem.
- P8-03 entregue sem materialização: retenção calcula sob demanda com regra/versionamento e
  escopo hashável; PDF permanece P7-03 e exclusão permanece bloqueada por P9-02.

## Próxima ação recomendada

**Próxima passagem: issues.** As issues `0001`–`0022` estão concluídas; P9-03 continua bloqueado
pela evidência operacional de restore e P5 transporte real/P7/P9 seguem conforme a tabela.
