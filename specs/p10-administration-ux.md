# Experiência de administração

## Metadados

- **Fase/status/versão:** P10-07 — implementada e verificada no issue 0040 — v1.1.
- **Dependências:** P10-01, P10-02; specs P1, P8-03, P9-02 e P9-03.
- **Fontes:** PRD FR-AUTH-001..007, RET-001..008, AUD-001..009, OPS-BKP-005, NFR-008..012, AC-003/004/014/015/016/026; Plano P10-07.

## Objetivo e limites

Modernizar Usuários, Auditoria, Retenção/Exclusão e saúde/backup administrativa. O escopo é somente apresentação; não cria exclusão automática, automação de restore, poderes novos, alteração de retenção, log/auditoria adicional ou endpoint para styling.

## Estado atual, segurança e ações críticas

Áreas e dados administrativos continuam Admin-only por servidor; a UI deve ocultar navegação sem tratá-la como controle. Criação/alteração de usuário, motivo de auditoria, prévia/escopo/confirmação/motivo de exclusão, acompanhamento/recovery de saga e saúde de backup mantêm contratos, confirmação e estado durável. Para uma ação crítica, a interface deve mostrar alvo/escopo seguro, consequência, campo de motivo quando o owner o exige, ação de confirmar/cancelar inequívoca e resultado retornado. Ela nunca declara exclusão concluída antes do owner, nem oferece recovery/restore automático.

A apresentação deve distinguir retenção não elegível, prévia, solicitada/processando, concluída, parcial, falha, bloqueio e recovery necessário. Eventos/audit logs, backup e falhas devem ser redigidos e não conter segredo, XML, path, manifesto ou identificador sensível. Estado de backup é capacidade operacional Admin-only: a limitação same-host registrada em P9 não pode ser ocultada, nem virar alegação de recuperação de desastre concluída.

## Falhas, observabilidade e testes

Falhas de auditoria que bloqueiam ação continuam bloqueando; falha de backup continua degradação Admin-only. Validar Admin/Operador/Visualizador e acesso direto, último Admin, alteração concorrente, confirmação/motivo, elegibilidade e recovery/reload, health/backup sem dados sensíveis, foco/teclado e TypeScript/lint/build.

## Aceite

- [x] Todos os controles administrativos preservam RBAC e enforcement do servidor — `App.tsx` mantém as três áreas Admin-only e a fixture `admin.*` recusa Operador, Visualizador, anônimo e sessão expirada sem dados administrativos.
- [x] Ações críticas apresentam escopo, confirmação, motivo e estado real sem falso sucesso — `UsersPresentation` e `RetentionPresentation` usam diálogos confirmáveis/canceláveis, guards e respostas owner-provided; exclusão nunca é simulada no cliente.
- [x] Auditoria, backup e erros continuam redigidos e distinguíveis — `AuditPresentation` traduz taxonomias e integridade, retém stale/error e limita contexto seguro; saúde/backup continua exclusivamente no dashboard owner do issue 0036.
- [x] Nenhuma política de retenção, recuperação ou backup é modificada — a implementação altera apenas adaptadores/presentação React, testes sintéticos e documentação.

## Evidência de implementação e validação

- `UsersSection` agora consome listagem filtrada/cursor e as rotas existentes de edição, papel, reset, ativação/desativação e troca própria de senha. Motivos, `version`, conflitos, último Administrador, CSRF e sessão permanecem sob o owner server-side; refreshs após sucesso/rejeição e sequências de requisição preservam a leitura autoritativa.
- `AuditSection` usa `actor_id`, `action`, `entity_type`, `result`, cursor e `integrity` retornados pelo servidor. A apresentação usa labels allowlisted, UTC, contexto bounded e não renderiza IDs, hashes, paths, payloads ou erros internos.
- `RetentionSection` distingue decisões `retained`, `eligible` e `non_executable`, mantém preview/scope/version, bloqueia preview stale, envia confirmação exata vinculada ao escopo somente após ação explícita e apresenta `pending`, `executing`, `recovery_required`, `failed` e `completed` sem transição local.
- `frontend/scripts/ui-contract.mjs` cobre as três apresentações, redaction, estados, integridade, cursores opacos, dialogs, labels e guards; `frontend/browser-tests/admin.*` cobre papéis, sessões negativas, deep links, confirmação/cancelamento, stale/recovery, foco e overflow com dados sintéticos.
- Validações executadas: `npm --prefix frontend run test:ui-contract`, `npm --prefix frontend run lint`, `npm --prefix frontend run build`, `npx tsc --noEmit ... browser-tests/admin.fixture.tsx browser-tests/admin.spec.ts`, `make lint`, `make test-unit` (307 testes), `make build`, `make smoke` e `make test-browser` (306 testes). A matriz local `npm --prefix frontend run test:browser` foi tentada, mas o host não possui a distribuição Chrome nem as bibliotecas gráficas do Firefox; a matriz Docker passou em Chrome, Firefox e Edge a 1024, 1280 e 1440 px.
