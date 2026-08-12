# Plano de implementação — NFX INOV

## Controle e baseline

| Campo | Valor |
|---|---|
| Produto | NFX INOV |
| Atualizado em | 2026-08-12 |
| Fontes avaliadas | Código/migrações/configuração, testes, PRD, arquitetura, specs, issues e histórico Git |
| Estado geral | P0–P6, P7-01/P7-02/P7-03, P8-01/P8-03, P9-01/P9-02/P9-03/P9-04 e P10-01..08 estão concluídos e preservados como histórico verificado. P8-02 permanece parcial, com todos os cards atualmente implementados reconciliados. A atualização do PRD/arquitetura para NFR-013/AC-027 e React Router cria o novo incremento **P10-09**, agora especificado e pronto para issues, mas ainda não implementado; o shell hash atual e a entrega somente em `/` não satisfazem esse delta. P9-05 e transporte oficial continuam bloqueados externamente. |

Código e migrações definem a baseline; testes definem o comportamento verificado. PRD e arquitetura definem o comportamento pretendido. Esta atualização não altera a árvore de produto nem reabre entregas concluídas sem evidência de lacuna.

## Estado confirmado

### Concluído e verificado

| Marco | Evidência de implementação | Evidência de verificação atual |
|---|---|---|
| P0 — fundação, configuração e isolamento | Django/React, Compose isolado, configuração fail-closed e simuladores | `make validate` em 2026-08-12: build, lint, mypy, **315 testes unitários**, integração isolada e smoke verdes. |
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
| P9-04 — hardening integrado | `docs/P9_HARDENING.md`, matriz de ameaças/limites, falhas Architecture §40, canários redigidos, ensaio PostgreSQL de 200 empresas/400 fluxos/jobs e runbook efêmero | issue 0031; focused P9 test, ephemeral restart/fault exercise, full validation; backup físico permanece residual de P9-05. |
| P0 follow-up — entrega do build React | `backend/nfx/urls.py` serve o artefato Vite fixo, confina assets resolvidos e preserva API/health/session; Docker `app` mantém `frontend/dist` no runtime | issue 0032; testes HTTP sintéticos, MIME/containment, leituras concorrentes, build Vite e smoke de imagem/runtime. |
| P0 follow-up — provisionamento seguro do administrador | `load_settings()` permite a senha somente no boundary explícito de `bootstrap_admin`; comando valida entrada, serviço serializa a primeira execução e mantém Argon2id/idempotência sem migration | issue 0033; testes em processo novo, matriz web/worker/scheduler, redaction, rerun, base não vazia e concorrência PostgreSQL. |
| P10-01 — fundação visual | `frontend/src/shared/ui/tokens.css` é a fonte única de valores; `Button`, `Field`, `Panel`, `DataTable`, `Badge` e `Feedback` cobrem ações, campos, painéis, tabelas, badges e estados operacionais com semântica nativa, foco e mensagens seguras | issue 0034; teste de contrato UI verifica oito estados, dez pares de contraste, ARIA, foco, teclado nativo e bloqueio; sem backend, migration ou dependência nova. |
| P10-02 — shell de aplicação (concluído) | `App.tsx` publica header/sidebar/main, skip link, contexto de sessão, modelo tipado de navegação por papel, active state por hash e destino único autorizado `#certificados`; a composição preserva callbacks, IDs, query strings, drill-downs e autorização server-side | issue 0035; contrato UI e matriz Docker sintética verificam os três papéis e anônimo, landmarks, foco, âncoras, matriz positiva/negativa, query/deep links e ausência de efeitos; lint/build e validações de repositório passam sem backend ou migration. |
| P10-03 — dashboard (concluído) | `DashboardSection` apresenta cards em grupos semânticos, períodos atual/anterior, frescura, estados owner-provided, capacidades redigidas, saúde Admin-only e URLs de drill-down; refresh/error preserva leitura stale e sequenciamento protege concorrência | issue 0036; contrato UI cobre estados, grupos, URLs, redaction e RBAC; matriz Docker cobre 90 testes em Chrome/Firefox/Edge a 1024/1280/1440 px; lint/build e validações de repositório passam sem backend, migration ou dependência nova. |
| P10-04 — documentos (concluído) | `DocumentsSection` preserva filtros, deep links, fronteira temporal, totais e cursor opaco do owner P7; explicita estados fiscais/operacionais e retém leitura stale/error; detalhe associa ações XML/PDF e usa somente URLs autorizados | issue 0037; contrato UI e matriz Docker cobrem estados, redaction, cursor, ações, foco, três papéis e sessões negativas; 135 testes passam em Chrome/Firefox/Edge a 1024/1280/1440 px; lint/build e validações de repositório passam sem backend, migration ou dependência nova. |
| P10-05 — empresas, certificados e coletas (concluído) | `CompaniesSection`, `CertificateInventoryPanel`, `CertificatePanel` e `CollectionsSection` usam primitives compartilhados, labels semânticos, filtros/deep links allowlisted, totais/limites/truncamento, cursor opaco, retenção stale/error e guards de sequência/interação; não exibem material de certificado, payload bruto ou erros internos | issue 0038; contrato UI, lint/build e matriz Docker cobrem estados, redaction, RBAC, sessões negativas, foco, teclado, overflow, cursor e retry; 180 testes passam em Chrome/Firefox/Edge a 1024/1280/1440 px; sem backend, migration ou dependência nova. |

### Implementado, porém parcial ou com documentação/teste a consolidar

| Item | Situação atual | Ação de acompanhamento |
|---|---|---|
| P8-02 dashboard | Slice inicial (`/api/dashboard` e `#dashboard`) é calculate-on-read, com períodos comparáveis, RBAC e capacidades indisponíveis explícitas. O issue 0025 integra o status seguro P9-02 no ramo Admin-only, os issues 0026–0028 entregam os drill-downs reconciliados de coleta, documentos e empresas, o issue 0029 entrega o inventário reconciliado dos três cards de certificado, o issue 0030 entrega o drill-down dos três cards de jobs e o issue 0042 fecha o gate sintético cross-owner de todos os cards implementados, todos com owner canônico, filtro equivalente, total bounded, redaction e leituras sem persistência própria. Fontes P5–P7 e disco continuam indisponíveis; a spec ainda deixa DoD posterior aberto. | Não marcar a spec/fase inteira concluída; manter os limites de capacidade e a reconciliação de cada incremento. |
| P1 auth e P7 consulta/download | Código, índice e issues registram conclusão; as listas preliminares de planejamento foram rotuladas como históricas nas respectivas specs, enquanto a evidência canônica permanece nas seções finais/notas de implementação. | Resolvido nesta passagem de **specs**. Não há evidência para reabrir implementação. |
| Frontend | Build/lint TypeScript e o runner Playwright isolado validam a UI; o target Docker fornece Chrome, Firefox e Edge para a matriz sintética do shell. | Manter a matriz de browser como validação dos slices P10; para P7-03/P9-03, escolher cobertura de interação se os fluxos críticos não ficarem adequadamente demonstrados por testes de contrato. |
| Dependências | Integração emite avisos externos de depreciação de `botocore` (`datetime.utcnow`), sem falha funcional. | Avaliar atualização/mitigação em manutenção de dependências; não mistura com as próximas features. |

## Próximos marcos executáveis

| Prioridade | Marco/status | Resultado e critério de conclusão | Dependências, riscos e decisões |
|---:|---|---|---|
| 1 | **P10-09 Navegação SPA — ready for issues** | A [spec P10-09](specs/p10-spa-url-navigation.md) fixa mapa de rotas, migração de hashes/queries, fallback limitado, rota inválida, responsabilidades de `App`/features e matriz de teste. O build conclui somente quando refresh, deep link, Back/Forward, RBAC, filtros e drill-downs preservarem intenção em Chrome/Firefox/Edge a 1024/1280/1440 px. | Não decidir novos filtros, endpoints, RBAC ou rotas de negócio além dos destinos aprovados. O fallback não pode capturar `/api`, health, sessão ou assets. A migração atravessa todas as features que leem hash e deve seguir o contrato aprovado. |
| 2 | **P8-02 expansões — in progress por incrementos** | Os cards atuais e seus drill-downs estão concluídos nos issues 0018/0025–0030/0042. Habilitar uma nova capacidade apenas com owner, estado/frescura, filtro equivalente, total reconciliável, redaction/RBAC e teste de reconciliação; criar spec/issue específico quando houver fonte pronta. | Capacidades de fontes oficiais, disco e quaisquer novos indicadores continuam indisponíveis; não criar snapshot/cache sem decisão documentada na spec. |
| 3 | **P9-05 Piloto/homologação — blocked por decisões externas** | Ambiente segregado, políticas oficiais versionadas e piloto com evidência redigida para os critérios aplicáveis, incluindo AC-016 conforme a versão atual do PRD. DoD em `specs/p9-internal-pilot-and-homologation.md`. | Depende de decisões/credenciais/allowlists oficiais NF-e/ADN e de cópia fisicamente separada com recuperação comprovada para OPS-BKP-002/006. Dados reais nunca entram em Git/testes/logs. |
| 4 | **Transporte real NF-e/ADN — blocked externo** | Criar adapter oficial/homologado somente após requisitos vigentes, allowlists, credenciais segregadas e política versionada com evidência. | Não inferir endpoints, leiautes, limites nem valores de produção. Simuladores P5/P6 permanecem a baseline segura. |
| 5 | **Manutenção de dependência — pending, baixo risco** | Avaliar atualização ou mitigação do aviso de depreciação `botocore` (`datetime.utcnow`) sem misturar com P10-09 ou workstreams fiscais. Conclui com teste compatível e aviso eliminado/justificado. | Não há falha funcional; decidir versão/compatibilidade no trabalho de manutenção. |

## Sequência e paralelismo

```text
P7-03 (renderização, concluído) ─────┐
                                     ├─ P8-02: ampliar apenas capacidades prontas
P9-03 (exclusão; alto risco) ────────┤
                                     └─ P9-04 hardening (concluído) ─→ P9-05 piloto/homologação

P10-01..08 (concluídos) ─→ P10-09 spec (pronta) ─→ P10-09 issue/build/validação
                              independente de P9-05

Transporte real NF-e/ADN ─────────── bloqueado por decisões/evidência externas
```

P7-03, P9-03 e P9-04 estão concluídos; P9-05 permanece bloqueado pelas decisões externas e pelo backup fisicamente separado. P10-09 é independente de P9-05, mas sua implementação depende da spec de migração. A saga de P9-03 e o ensaio P9-04 usam fault injection e recovery explícito; não duplicar cursor, idempotência, retenção, objetos ou auditoria: P3/P4/P8 continuam os owners canônicos.

### P10 — Frontend UX & Visual System

#### Workflow de execução de issues frontend

Toda issue de frontend deve iniciar avaliando as skills/plugins disponíveis e aplicáveis por capacidade, além de ler a issue/spec e levantar contratos funcionais, estados e guardrails. Em criação, redesign, modernização ou alteração visual significativa, o workflow obrigatório é: (1) selecionar as skills/plugins aplicáveis e seguir integralmente suas instruções; (2) produzir a concepção visual e, quando a skill selecionada exigir aprovação de conceito/design antes da implementação, obter essa aprovação obrigatoriamente antes de codificar; (3) aplicar ou estender o design system compartilhado sem introduzir regras de domínio; (4) implementar dentro da arquitetura frontend vigente; e (5) validar contratos funcionais e a experiência no navegador, refinar divergências visuais e registrar a evidência.

O uso de skills/plugins é um acelerador especializado, não uma fonte de autoridade funcional: PRD, arquitetura, specs e issues continuam definindo os contratos. O workflow não autoriza mudança silenciosa de endpoint, contrato HTTP, RBAC, regra de negócio, estado funcional, URL/âncora ou limite arquitetural. A validação visual inclui a matriz aplicável de Chrome, Firefox e Edge em 1024/1280/1440 px, sem substituir os testes dos owners de domínio.

| Slice/status | Resultado e critério de conclusão | Dependências e guardrails |
|---|---|---|
| **P10-01 Design System Foundation — concluído no issue 0034** | Tokens de tipografia, espaçamento, cores institucionais, superfícies, bordas/sombras e primitives compartilhadas publicados; loading, vazio válido, erro, indisponibilidade, degradação, bloqueio, sucesso e ação crítica têm estados explícitos. | `shared/ui` é owner; valores exatos e pares de contraste estão na spec P10-01. Adoção representativa preserva contratos e não adiciona biblioteca UI. |
| **P10-02 Application Shell — concluído no issue 0035** | Sidebar, header, identidade do usuário, navegação, landmarks, skip link e composição principal para desktop/notebook, com preservação das áreas, hashes, callbacks e visibilidade por papel existentes. | Histórico verificado para o contrato então vigente. Foi supersedido somente para navegação por P10-09, porque PRD NFR-013/AC-027 e arquitetura §10.4 agora exigem React Router e destinos URL-endereçáveis. |
| **P10-03 Dashboard UX — concluído no issue 0036** | Modernizar cards, período, hierarquia operacional, estados e drill-downs já existentes, preservando o owner P8 e as fronteiras de segurança. | P10-01/02 comprovados; contrato UI e matriz Docker 90/90 passaram sem recalcular métricas, filtros, capacidades ou autorização no navegador. |
| **P10-04 Documents UX — concluído no issue 0037** | Modernizar filtros, busca, resultados, detalhe, XML/PDF e os estados vazio, degradado e bloqueado. | P10-01/02 e P7 comprovados; contrato HTTP, dados fiscais e ações atuais preservados. |
| **P10-05 Companies, Certificates & Collections UX — concluído no issue 0038** | Modernizar empresas, ciclo de vida, certificados, cobertura/estado de coletas e ações administrativas. | P10-01/02 comprovados; contrato UI e matriz Docker 180/180 passaram; preservados owners de estado, confirmação, fluxos funcionais, contratos HTTP e redaction. |
| **P10-06 Exports UX — concluído no issue 0039** | Modernizar solicitação, progresso, parcial/falha, download e expiração de ZIP. | P10-01/02 comprovados; contrato UI e matriz Docker 234/234 passaram em Chrome/Firefox/Edge a 1024/1280/1440 px; preservados autorização, expiração, composição de ZIP, contrato HTTP, redaction e owner `exports`, sem backend, migration ou dependência nova. |
| **P10-07 Administration UX — concluído no issue 0040** | Modernizar usuários, auditoria, retenção, exclusão controlada e a fronteira de saúde/backup administrativa quando aplicável; adicionar estados redigidos, stale/retry, filtros/cursors, dialogs críticos, conflitos de versão e recovery sem falso sucesso. | P10-01/02 comprovados; owners P1/P8/P9 e dashboard P10-03 preservados. Contrato UI, lint/build e fixtures sintéticas passaram; 306 testes Playwright Docker passaram em Chrome/Firefox/Edge a 1024/1280/1440 px; a execução local foi limitada pela ausência de Chrome/bibliotecas Firefox. |
| **P10-08 Accessibility, Responsive Polish & UX Validation — concluído no issue 0041** | Validar contraste, foco, teclado, labels, browsers desktop suportados, tamanhos de notebook, consistência entre features e estados críticos; contrato transversal e refinamentos de dialogs críticos concluídos. | P10-02..07 comprovados. O gate usa fixtures sintéticas, mantém mobile fora do escopo e passou Chrome, Firefox e Edge desktop em 1024/1280/1440 px. |
| **P10-09 Navegação SPA URL-endereçável — pronta para issues** | Implementar NFR-013/AC-027 conforme [spec P10-09](specs/p10-spa-url-navigation.md): `AppShell` persistente, uma página primária por rota e React Router; preservar filtros e drill-downs canônicos, RBAC no servidor, estados de cada feature e URLs suportados. | A arquitetura §10.4 aprova React Router e exige fallback SPA limitado; `App.tsx` e features ainda dependem de hashes/`hashchange`/`pushState`, `package.json` não contém React Router e `urls.py` só serve `/`. |

P10 é modernização de UX/UI, não reescrita funcional. Cada spec P10 deve preservar contratos HTTP existentes, IDs e semântica necessários aos fluxos, autorização server-side e papéis; não duplicar lógica de domínio nem recalcular regra fiscal no navegador. Backend só pode mudar em issue futura de P10 para necessidade funcional concreta com spec aprovada, nunca para facilitar styling. P10 não se mistura com P9-05, homologação fiscal ou backup fisicamente separado.

## Specs, inconsistências e trabalho operacional restante

| Tema | Registro e impacto |
|---|---|
| Mapa de specs | As 36 specs registram P8-02 parcial, P9-05 bloqueada e P10-01..08 concluídas no contrato anterior. [P10-09](specs/p10-spa-url-navigation.md) é o contrato canônico para substituir hashes por rotas, migrar URLs publicados e limitar o fallback SPA; `p10-application-shell.md` e `p0-frontend-build-delivery.md` preservam a evidência histórica e apontam para o delta. O item está pronto para a passagem de issues. |
| Renderização | P7-03 usa `BrazilFiscalReport[danfse]==1.0.1`, API Python em processo, `DocumentRender`, migração `0019`, job durável, rotas/UI, métricas e fixtures sintéticas; o XML original permanece owner do acervo. A inconsistência de classificação de licença upstream é observação não bloqueante registrada na spec. |
| Exclusão | P9-03 está implementado no owner `retention`, com rota Admin, job durável `retention.delete`, checkpoints de bytes/relações, recovery manual e referências protegidas resolvidas sem apagar backups/auditoria. Não há exclusão automática. |
| Runtime/backup | Runtime HTTPS, backup verificável e validação isolada são implementados. Recuperação completa continua manual e documentada. O backup no mesmo host é uma divergência conhecida do PRD: não satisfaz OPS-BKP-002/006 nem AC-016 para produção; não bloqueia P9-03, mas bloqueia a evidência correspondente de P9-05 até haver cópia fisicamente separada. CA confiável permanece limitação arquitetural separada. |
| Testes/migrações | Migrações chegam a `0020`; não há TODO/FIXME, implementação temporária ou testes `skip`/`xfail`/flaky nos diretórios de produto/teste pesquisados. `make validate` e `make test-browser` concluíram com sucesso em 2026-08-12; a execução atual não valida P10-09 porque ainda exercita hashes. |
| Rota raiz e build React | O issue 0032 permanece concluído para `/` e assets confinados. É **parcial/supersedido** frente a P10-09: `backend/nfx/urls.py` não tem fallback SPA limitado para rotas conhecidas, requisito expresso da arquitetura §10.4. A spec deve preservar `503` para build ausente, containment/MIME de assets e os comportamentos de API/health/sessão antes de qualquer mudança. |
| Bootstrap de Administrador | Issue 0033 concluiu a fronteira command-only de `NFX_BOOTSTRAP_ADMIN_PASSWORD`: a allowlist global permanece fail-closed, a senha não entra em settings/processos regulares e o serviço preserva bootstrap Argon2id, idempotência e concorrência sem migration. [Spec de provisionamento](specs/p0-bootstrap-admin-provisioning.md) registra o DoD. |

## Decisões necessárias e riscos

- **Open externo:** endpoints, envelopes, leiautes, limites e homologação para transportes NF-e/ADN. Bloqueia somente transporte real e piloto correspondente.
- **P9-03 adotado:** bytes são verificados e tratados individualmente; a remoção relacional ocorre numa transação posterior; divergência, ausência, falha de auditoria ou vínculo protegido fica visível e retomável, sem restore automático.
- **P9-04 adotado:** a matriz integrada e as falhas são evidenciadas pelos owners canônicos e por um exercício efêmero bounded; resultados de capacidade são Proposed, sem SLA ou limite artificial. Nenhuma lacuna externa é mascarada como controle concluído.
- **Proposed, dono P8-02:** cache/materialização e limites padrão de período, somente se a agregação calculate-on-read deixar de atender um card.
- **Lacuna de requisito:** cópia de backup fisicamente separada e recovery após perda do host são necessários para OPS-BKP-002/006 e AC-016 em produção; bloqueiam somente essa evidência do piloto, não P9-03. CA confiável, broker e escala horizontal continuam Deferred; registrar seus riscos residuais no piloto, sem expandir o MVP.
- **P10 histórico adotado:** vinho, cinza e branco são a direção visual de produto; P10-01..08 preservaram `App → features → shared`, contratos HTTP, RBAC server-side e os estados operacionais, com matrizes Docker sintéticas em Chrome/Firefox/Edge. O contrato hash/no-router de P10-02 era correto à época, mas foi supersedido para navegação pelo PRD/arquitetura atuais; estado global, framework UI e mudanças de backend por conveniência continuam fora do escopo.
- **P10-09 especificado:** o PRD e a arquitetura atuais substituem somente o contrato de navegação hash de P10-02, não a evidência visual/funcional de P10-01..08. A [spec P10-09](specs/p10-spa-url-navigation.md) fixa a migração, compatibilidade de hash publicado, fallback do servidor e matriz de rotas inválidas; seguir para issues antes do build.
- **Gaps independentes:** a entrega da rota raiz do build React e o provisionamento seguro do bootstrap foram defeitos funcionais/operacionais fora de P10, agora concluídos nos issues 0032 e 0033.

## Próxima ação recomendada

**Próxima passagem: `issues`.** Criar a issue de P10-09 que migra roteamento e entrega de SPA conforme a spec. P8-02 segue somente quando uma capacidade tiver owner/spec; P9-05 continua bloqueado até resolver decisões externas e backup físico.
