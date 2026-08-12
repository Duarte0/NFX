# Experiência de exportações ZIP

## Metadados

- **Fase/status/versão:** P10-06 — implementação concluída e verificada no issue 0039 — v1.1.
- **Dependências:** P10-01, P10-02 e `p8-zip-export.md`.
- **Fontes:** PRD FR-ZIP-001..003, BR-ZIP-001..004, NFR-006/008..012, AC-012/023/026; Plano P10-06.

## Objetivo e não escopo

Modernizar solicitação, acompanhamento, completude, download e expiração da exportação ZIP assíncrona. Não muda seleção, autorização, prazo de expiração, composição do ZIP, job, storage, auditoria ou retry do owner `exports`.

## Estado atual e contrato de estado

O cliente deve representar fielmente estados retornados — pendente/processando, concluído completo, concluído parcial, falhou, expirado e indisponível — e explicar completude somente com metadado retornado. Solicitações repetidas/reloads devem consultar o estado durável, não inferir progresso local; botão de download só é habilitado com artefato autorizado e vigente. Filtros/escopo enviados continuam allowlisted pela API, e mensagens não podem enumerar documentos não autorizados.

Enquanto processa, a UI pode apresentar apenas progresso/contagem explicitamente retornado; ausência de percentual não pode ser convertida em estimativa. Parcial deve conservar o número e o escopo que a API autorizou exibir, permanecer distinto de concluído completo e manter as ações permitidas pelo owner. Expirado deve remover somente a ação de download e nunca sugerir que documentos-fonte foram removidos.

## Segurança e validação

Preservar CSRF para mutação, sessão/RBAC server-side, URL de download e auditoria existentes. Testar todos os estados, reload durante processamento, parcial versus falha, expiração, acesso não autorizado, dupla solicitação, erro de rede, foco/teclado e TypeScript/lint/build com dados sintéticos.

## Aceite

- [x] Progresso e completude vêm exclusivamente do contrato durável de exportação.
- [x] Download/expiração preservam autorização, prazo e informação mínima segura.
- [x] Parcial, falha e indisponibilidade permanecem visual e semanticamente distintos.
- [x] Não há alteração de ZIP, job, artefato ou regra de negócio.

## Evidência de implementação e validação — issue 0039

`ExportsSection` foi recomposta com as primitives P10-01 para solicitação, listagem, detalhe,
badges, métricas owner-provided, expiração, stale/error/retry, vazio e indisponibilidade. Os
estados duráveis têm rótulos e explicações pt-BR; `complete` não habilita download, enquanto
somente `available` com URL retornada pelo owner o oferece. Parcial, falha, expiração e exclusão
permanecem distintos, sem exibir `safe_error`, IDs, caminhos, bytes brutos ou exceções internas.

Guards por interação protegem solicitação, refresh, detalhe, retry e download; a chave de
idempotência é criada uma vez por intenção, a resposta posterior reconsulta a listagem e
sequências impedem respostas antigas de sobrescrever uma seleção nova. Refresh/detail preservam a
última leitura segura apenas com indicação stale/loading/error explícita. Não houve alteração de
endpoint, payload, RBAC, backend, migration ou dependência.

Validação executada: `npm --prefix frontend run test:ui-contract`, `npm --prefix frontend run
lint`, `npm --prefix frontend run build`, `make lint`, `make test-unit`, `make build`, `make
smoke` e `docker compose -f docker-compose.test.yml run --rm --no-deps browser-tests`, cobrindo
Chrome/Firefox/Edge em 1024/1280/1440 px com fixtures sintéticas. O contrato e a matriz browser
verificam os oito estados, progresso/contagens/bytes retornados ou ausentes, stale/retry,
idempotência, ordenação de detalhe, download parcial/expirado/não autorizado, redaction, papéis,
sessões negativas, foco e teclado.
