# Plano de implementação — NFX INOV

## Controle e baseline

| Campo | Valor |
|---|---|
| Produto | NFX INOV |
| Atualizado em | 2026-08-11 |
| Fontes avaliadas | Código/migrações/configuração, testes, PRD, arquitetura, specs, issues e histórico Git |
| Estado geral | P0–P6, P7-01/P7-02/P7-03, P8-01/P8-03, P9-01/P9-02/P9-03 concluídos; P8-02 tem slice inicial, integração Admin-only do status de backup e drill-downs de coleta, documentos, empresas, certificados e jobs concluídos nos issues 0018/0025–0030; fontes P5–P7, rendering, disco, P9-04/P9-05 seguem pendentes. |

Código e migrações definem a baseline; testes definem o comportamento verificado. PRD e arquitetura definem o comportamento pretendido. Esta atualização não altera a árvore de produto nem reabre entregas concluídas sem evidência de lacuna.

## Estado confirmado

### Concluído e verificado

| Marco | Evidência de implementação | Evidência de verificação atual |
|---|---|---|
| P0 — fundação, configuração e isolamento | Django/React, Compose isolado, configuração fail-closed e simuladores | `make validate` em 2026-08-11: build, lint, mypy, **230 testes unitários**, integração isolada e smoke verdes. |
| P1 — persistência, objetos, identidade, RBAC, auditoria e usuários | migrações `0001`–`0005`; módulos `artifacts`, `identity`, `audit` e UI | suites unitária/integração e `schema_status`; todas as issues 0001–0008 encerradas. |
| P2 — empresas, enriquecimento e certificado A1 | módulos `companies`/`certificates`, migrações `0006`–`0007` | testes de lifecycle, configuração e integração. |
| P3 — jobs, políticas, observabilidade, simuladores e coleta manual | `jobs`, `collection`, `adapters/simulation.py`, migrações `0008`–`0010`/`0012` | leases, retry/bloqueio, simulator boundary, heartbeats e controle manual cobertos. |
| P4 — documentos, ingestão/cursor, matriz de falhas e status/lista | `documents`/`collection.ingestion`, migrações `0011`, `0013`, `0014` | identidade, replay, quarentena/conflito, estados e contratos HTTP/UI cobertos. |
| P5 — NF-e simulator-only | `adapters/nfe.py`, jobs/manifestação e migração `0017` | issues 0013, 0020 e 0022; testes NF-e unitários e de integração. Transporte oficial não foi habilitado. |
| P6 — ADN simulator-only | `adapters/adn.py`, cobertura e migração `0015` | issue 0014; testes de distribuição/cobertura. Transporte municipal/oficial não foi habilitado. |
| P7-01/P7-02 — consulta e download individual | rotas `api/documents*`, consulta, integridade e UI | issue 0015; testes de consulta/status/documentos. |
| P7-03 — renderização DANFE/DANFSe | `DocumentRender`, renderer pinado, job `document.render_pdf`, rotas/UI e capacidade operacional | issue 0023; migração `0019`; testes unitários de fixtures, idempotência, integridade, RBAC do worker e reuso. |
| P8-01 e P8-03 | `exports` + migração `0018`; `retention` calculate-on-read | issues 0021/0019; testes de exportação, retenção e integração. |
| P9-01/P9-02 | Compose runtime/proxy, `backup`, migração `0016`, comandos e runbooks | issues 0016/0017; testes de topology e backup/restore isolado. |
| P9-03 — exclusão controlada | `DeletionOperation`/`DeletionItem`, migration `0020`, saga `retention.delete`, recovery, auditoria, métricas e UI Admin | issue 0024; unitários, integração PostgreSQL/MinIO isolada, migration check, lint/mypy/build. |

### Implementado, porém parcial ou com documentação/teste a consolidar

| Item | Situação atual | Ação de acompanhamento |
|---|---|---|
| P8-02 dashboard | Slice inicial (`/api/dashboard` e `#dashboard`) é calculate-on-read, com períodos comparáveis, RBAC e capacidades indisponíveis explícitas. O issue 0025 integra o status seguro P9-02 no ramo Admin-only, os issues 0026–0028 entregam os drill-downs reconciliados de coleta, documentos e empresas, o issue 0029 entrega o inventário reconciliado dos três cards de certificado e o issue 0030 entrega o drill-down dos três cards de jobs, todos com owner canônico, filtro equivalente, total bounded, redaction e leituras sem escrita. Fontes P5–P7, rendering e disco continuam indisponíveis; a spec ainda deixa DoD posterior aberto. | Não marcar a spec/fase inteira concluída; manter os limites de capacidade e a reconciliação de cada incremento. |
| P1 auth e P7 consulta/download | Código, índice e issues registram conclusão; as listas preliminares de planejamento foram rotuladas como históricas nas respectivas specs, enquanto a evidência canônica permanece nas seções finais/notas de implementação. | Resolvido nesta passagem de **specs**. Não há evidência para reabrir implementação. |
| Frontend | Build/lint TypeScript validam a UI; há testes HTTP/backend, mas não há runner de interação de browser configurado. | Manter como dívida de qualidade operacional, não como bloqueio retroativo. Para P7-03/P9-03, escolher cobertura de interação se os fluxos críticos não ficarem adequadamente demonstrados por testes de contrato. |
| Dependências | Integração emite avisos externos de depreciação de `botocore` (`datetime.utcnow`), sem falha funcional. | Avaliar atualização/mitigação em manutenção de dependências; não mistura com as próximas features. |

## Próximos marcos executáveis

| Prioridade | Marco/status | Resultado e critério de conclusão | Dependências, riscos e decisões |
|---:|---|---|---|
| 1 | **P9-03 Exclusão controlada — concluído no issue 0024** | Solicitação Admin com motivo/confirmação/prévia atual, saga/checkpoint idempotente, tratamento coerente de documento/artefatos, recovery sem falso sucesso, auditoria sem conteúdo fiscal e UI/worker entregues. DoD em `specs/p9-controlled-deletion.md`. | P8-03/P9-02 comprovados; restore PostgreSQL/MinIO continua manual conforme P9-02. P9-04 deve revisar a matriz de risco sem reabrir este incremento. |
| 2 | **P8-02 expansões — in progress por incrementos** | O incremento de saúde de backup foi concluído no issue 0025, os drill-downs de coleta, documentos e empresas nos issues 0026–0028, o inventário de certificados no issue 0029 e o drill-down de jobs no issue 0030: `GET /api/collections/executions`, `GET /api/documents`, `GET /api/companies?lifecycle=...`, `GET /api/certificates/inventory?filter=...` e `GET /api/jobs/observability?filter=...` usam owners canônicos, filtros allowlisted, totais reconciliados, páginas redigidas, RBAC e leituras sem escrita. Habilitar cada capacidade futura somente quando a fonte possuir owner, estado/frescura, filtro equivalente e teste de reconciliação. | P5–P7, rendering e disco continuam indisponíveis; não criar snapshot/cache sem decisão documentada na spec. |
| 3 | **P9-04 Hardening — pending após P9-03** | Produzir matriz de ameaças/falhas, evidência de recovery e ensaio sintético ~200 empresas; corrigir ou bloquear release para achado crítico. DoD em `specs/p9-hardening.md`. | Requer P5–P8 e P9-01..03 completos. Thresholds de carga são Proposed e dependem de medição. |
| 4 | **P9-05 Piloto/homologação — blocked por hardening e decisões externas** | Ambiente segregado, políticas oficiais versionadas e piloto com evidência redigida para AC-001..025. DoD em `specs/p9-internal-pilot-and-homologation.md`. | Depende de P9-04, de endpoints, envelopes, limites, certificados e homologação NF-e/ADN aprovados externamente, e de cópia de backup fisicamente separada para fechar AC-016/OPS-BKP-002/006. Dados reais nunca entram em Git/testes/logs. |
| 5 | **Transporte real NF-e/ADN — blocked externo** | Criar adapter oficial/homologado somente após requisitos oficiais vigentes, allowlists, credenciais segregadas e política versionada com evidência. | Não inferir endpoints, leiautes, limites nem valores de produção. Simuladores P5/P6 permanecem a baseline segura. |

## Sequência e paralelismo

```text
P7-03 (renderização, concluído) ─────┐
                                     ├─ P8-02: ampliar apenas capacidades prontas
P9-03 (exclusão; alto risco) ────────┤
                                     └─ P9-04 hardening ─→ P9-05 piloto/homologação

Transporte real NF-e/ADN ─────────── bloqueado por decisões/evidência externas
```

P7-03 e P9-03 estão concluídos; P9-04 é o próximo incremento de maior risco. A saga de P9-03 usa fault injection e recovery explícito; não duplicar cursor, idempotência, retenção, objetos ou auditoria: P3/P4/P8 continuam os owners canônicos.

## Specs, inconsistências e trabalho operacional restante

| Tema | Registro e impacto |
|---|---|
| Mapa de specs | Todas as 25 specs têm backlog proprietário. O índice marca 22 concluídas, uma parcialmente entregue (P8-02) e duas pendentes (P9-04/P9-05); esse estado corresponde ao código, salvo as caixas históricas de P1/P7 e o DoD ainda aberto de P8-02. |
| Renderização | P7-03 usa `BrazilFiscalReport[danfse]==1.0.1`, API Python em processo, `DocumentRender`, migração `0019`, job durável, rotas/UI, métricas e fixtures sintéticas; o XML original permanece owner do acervo. A inconsistência de classificação de licença upstream é observação não bloqueante registrada na spec. |
| Exclusão | P9-03 está implementado no owner `retention`, com rota Admin, job durável `retention.delete`, checkpoints de bytes/relações, recovery manual e referências protegidas resolvidas sem apagar backups/auditoria. Não há exclusão automática. |
| Runtime/backup | Runtime HTTPS, backup verificável e validação isolada são implementados. Recuperação completa continua manual e documentada. O backup no mesmo host é uma divergência conhecida do PRD: não satisfaz OPS-BKP-002/006 nem AC-016 para produção; não bloqueia P9-03, mas bloqueia a evidência correspondente de P9-05 até haver cópia fisicamente separada. CA confiável permanece limitação arquitetural separada. |
| Testes/migrações | Migrações chegam a `0020`; P7-03 e P9-03 têm suites unitárias/integração, migration check e validação de lint/mypy/build. A integração P9-03 usa PostgreSQL/MinIO efêmeros e fixtures sintéticas; nenhum teste está marcado skip/xfail/flaky. |

## Decisões necessárias e riscos

- **Open externo:** endpoints, envelopes, leiautes, limites e homologação para transportes NF-e/ADN. Bloqueia somente transporte real e piloto correspondente.
- **P9-03 adotado:** bytes são verificados e tratados individualmente; a remoção relacional ocorre numa transação posterior; divergência, ausência, falha de auditoria ou vínculo protegido fica visível e retomável, sem restore automático.
- **Proposed, dono P8-02:** cache/materialização e limites padrão de período, somente se a agregação calculate-on-read deixar de atender um card.
- **Lacuna de requisito:** cópia de backup fisicamente separada e recovery após perda do host são necessários para OPS-BKP-002/006 e AC-016 em produção; bloqueiam somente essa evidência do piloto, não P9-03. CA confiável, broker e escala horizontal continuam Deferred; registrar seus riscos residuais no piloto, sem expandir o MVP.

## Próxima ação recomendada

**Próxima passagem: issues.** P7-03 foi concluído no issue 0023 e P9-03 no issue 0024. A próxima passagem deve tratar P9-04 após a criação/seleção de issue elegível; a passagem **build** pode executar a issue mais alta elegível.
