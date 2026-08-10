# Plano de implementação — NFX INOV

## Controle e baseline

| Campo | Valor |
|---|---|
| Produto | NFX INOV |
| Atualizado em | 2026-08-10 |
| Fontes | Código/migrações, testes, PRD.md, ARCHITECTURE.md, specs/ e issues/ |
| Status geral | Fundação e plataforma de processamento concluídas e verificadas; P4-01/P4-02 de ingestão e o contrato mínimo P4-04 concluídos, a matriz P4-03 de falhas ainda pendente. |

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

P4-01 adicionou a identidade e persistência base de documentos/eventos em `documents`, com referências imutáveis a artefatos. P4-02 adicionou pipeline/cursor e P4-04 adicionou a API/UI mínima de status/lista; exportações, retenção, renderização e a matriz P4-03 de falhas continuam fora desta entrega. Simuladores são infraestrutura de teste; não implementam P5–P6.

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
| P0 | P4-02 Pipeline durável e cursor — **concluído, issue 0009** | Migration `0013`, páginas/unidades/checkpoints, objeto antes do banco, replay/conflito/quarentena, progressão monotônica, reconciliação e ponte de execução de coleta; integração isolada com simuladores sintéticos. | P4-01 e P3-01; P4-03 continua dona da matriz de estados de falha. |
| P1 | P4-03 Estados de falha — **pendente** | Quarentena, conflito, parcial, vazio, bloqueio e degradação preservam evidência e não são confundidos. | P4-02, auditoria. |
| P1 | P4-04 Contrato mínimo de status/lista — **concluído, issue 0010** | `/api/documents` e a seção `#documentos` exibem metadados limitados, estados explícitos, paginação e resultados de quarentena/conflito sem inferir sucesso de vazio. | P4-01/P4-02; P4-03 continua dona da matriz operacional de falhas. |
| P1 | Correção do contrato de build — **concluída, issue 0008** | `docs/DEVELOPMENT.md`, `Makefile`, testes de fronteira e spec P0 deixam explícito/encapsulam o perfil exigido, com comando de checkout limpo reproduzível sem segredo versionado. | Não alterar comportamento fail-closed nem valores de produção. |

## Marcos posteriores, ordenados por dependência

| Marco | Status | Resultado e critérios | Dependências |
|---|---|---|---|
| P5 NF-e | **especificado, não implementado** | Distribuição simulada, fluxos entrada/saída, XML/eventos e manifestação idempotente; transporte real permanece Open até homologação. Ver `p5-nfe-distribution-and-manifestation.md`. | P4-02, P2-03, P3-02/03. |
| P6 NFS-e/ADN | **especificado, não implementado** | Distribuição por ator/NSU, cobertura explícita e tomada/prestada/eventos; sem integrações municipais. Ver `p6-nfse-adn-distribution-and-coverage.md`. | P4-02, P2-03, P3-02/03. |
| P7 consulta/download | **especificado, não implementado** | Busca/filtros/detalhe e download individual RBAC/auditado. Ver `p7-document-consultation-and-individual-download.md`. | P4-01/P4-04; P5/P6 ampliam a cobertura. |
| P7 PDF | **blocked localmente** | DANFE/DANFSe versionado, isolado e regenerável. | P4-01/P7-01 e seleção de renderer; a decisão de biblioteca continua Open. |
| P8 ZIP/dashboard/retenção | **especificado, não implementado** | ZIP assíncrono, drill-down reconciliável e prévia de elegibilidade sem exclusão. Ver specs P8. | Consulta/download; dashboard pode usar P3-04 progressivamente; retenção depende P4. |
| P9 runtime/restore/exclusão/piloto | **especificado, não implementado** | HTTPS interno, restore comprovado, exclusão somente após restore, hardening e piloto segregado. | Ver specs P9; P9-03 permanece bloqueado até P9-02. |

## Sequência executável

```text
Agora: P4-03 / P4-04 ───────────────────┐
                                       ├─ P4-01 → P4-02 → P4-03 / P4-04
Correção do contrato de build ──────────┘                 │
                                                           ├─ P5 NF-e
                                                           ├─ P6 ADN
                                                           └─ P7 consulta → P8 → P9
```

P3-05, P4-01, P4-02 e P4-04 estão concluídos. A coleta manual deve usar o mesmo pipeline P4 quando passar
de resultados sintéticos a resultados fiscais persistidos. Não duplicar cursor, idempotência,
quarentena ou estado de fluxo nos adaptadores.

## Decisões, inconsistências e riscos registrados

| Tema | Registro / impacto |
|---|---|
| Status de P0 | O issue 0008 fechou a lacuna de `make build`: o recipe usa somente valores sintéticos locais, sem alterar o boot fail-closed, o template externo ou a capacidade fiscal. A discrepância de valores literais no template foi corrigida no issue 0007; qualquer uso externo anterior continua sujeito a rotação fora do repositório. |
| Status de P3-04 | A passagem de specs corrigiu `p3-fiscal-adapter-simulation-and-fixtures.md`: P3-04 pertence à spec canônica de jobs e está concluído, com migração `0010` e testes como evidência. |
| P1-04 | Índice marca a spec concluída, mas texto de fase conserva blocker Graphify; tratá-lo como pendência de metadado, não de entrega. |
| Transporte real NF-e/ADN | Endpoints, leiautes, limites e homologação continuam Open; bloqueiam somente transportes reais, nunca a implementação com simuladores. |
| DANFE/DANFSe | Seleção de renderer é decisão requerida antes de P7-03; impacto local. Não escolher sem avaliação de licença, isolamento e reprodução. |
| Backup/exclusão | Backup local e TLS autoassinado são limitações Accepted; backup fisicamente separado e CA confiável são Deferred. Exclusão definitiva fica bloqueada até restore comprovado. |
| Árvore de trabalho | Há mudanças não commitadas em código, testes, documentação, dependências e Graphify que não pertencem a esta passagem. Elas foram preservadas; a verificação acima reflete a árvore atual, não uma revisão de autoria. |
| Cobertura frontend | Não há dependência/configuração de Vitest, Playwright, Cypress, Selenium ou equivalente. O contrato P3-05 foi coberto pela compilação/lint da UI e pelos endpoints HTTP; um runner de browser permanece uma melhoria operacional separada. |

## Trabalho de specs e operação que resta

- Passagem de specs validou as 25 specs ativas sem lacunas de backlog: P0/P1/P3 foram reconciliados e P5/P6 agora declaram explicitamente que estão especificadas, mas não implementadas. Não foram encontrados TODO/FIXME/placeholder de domínio, testes skipped/xfail/flaky, nem duplicação de implementação que alterem esse backlog; os boundaries vazios de `documents`, `exports` e `retention` são intencionais.
- Issue 0007 corrigiu a higiene de `.env.example`; valores que tenham sido usados fora de testes descartáveis continuam potencialmente comprometidos e devem ser rotacionados fora do repositório.
- Antes de P4-03: manter migração aditiva, testes de instalação/upgrade e reconciliação nos limites objeto–banco–cursor; P4-02 cobre a unidade/checkpoint e P4-04 mantém as leituras sem escrita.
- Antes de P5/P6 reais: decidir/adquirir evidência de endpoints, certificados, leiautes e homologação segregada; isso é decisão externa, não assumir valores.
- Antes de P9-03: implementar e comprovar backup/restore incluindo banco, objetos, certificado cifrado e chave necessária.

## Próxima ação recomendada

**Próxima passagem: issues.** As issues `0001`–`0010` estão concluídas; P4-03 ainda
requer a matriz completa de estados de falha conforme a spec.
