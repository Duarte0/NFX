# Exclusão definitiva controlada

## Metadados

- **Fase/status:** P9 — **Blocked localmente** até evidência concluída de P9-02.
- **Backlog:** P9-03. **Dependências:** P8-03 e P9-02.
- **PRD:** RET-005, RET-006, RET-008, AUD-006, AUD-008, AUD-009. **Aceite:** AC-014, AC-015.
- **Arquitetura:** seções 14, 17, 27, 28, 31, 33, 37, 40 e 41.

## Propósito e resultado

Permitir somente a Administrador excluir manualmente documento elegível após prévia exata, confirmação e motivo, tratando vínculos/objetos coerentemente e preservando auditoria sem conteúdo fiscal.

## Baseline, escopo e gate local

P8 calcula elegibilidade e prévia, mas não apaga. Esta spec habilita decisão/execução apenas quando uma evidência válida de restore P9-02 estiver registrada. Isso não bloqueia nenhuma outra spec. Não exclui empresa, usuário, backup, lote automático ou item retido.

## Estado e contrato Proposed

Retenção é dona da decisão; Artefatos executa tratamento de bytes; Documentos mantém estado coerente; Auditoria preserva evento. **Proposed:** solicitação de exclusão com Admin, motivo, prévia ID/hash/versão, estado, timestamps e passos/itens; estados `pendente|em_execução|recuperação_necessária|falha|concluída`. Constraint impede decisão ativa concorrente por documento; índices por estado/data/documento.

Contrato recebe prévia e confirmação inequívoca, revalida no servidor: papel, sessão, restore aprovado/fresco conforme política local, elegibilidade atual e hash do escopo. Se qualquer vínculo mudou, recusa e exige nova prévia. Execução marca intenção, trata documento/eventos/original/XML/PDF/derivados e só conclui quando não há órfão/registro enganoso. Auditoria guarda IDs/hash/motivo/resultado, nunca conteúdo.

## UI, segurança e observabilidade

Tela Admin mostra exatamente o escopo, datas/regra, artefatos e confirmação; Operador/Visualizador não veem e recebem 403. Não aceitar confirmação genérica reutilizável. Logs redigidos; métricas de solicitado/bloqueado/falha/recovery/concluído e órfão.

## Falhas, recovery e testes

Não há transação atômica DB+MinIO: execução é saga/checkpoint **Proposed**, retomável e idempotente. Falha após remover alguns objetos não declara sucesso; bloqueia nova decisão até recovery e usa backup/runbook quando necessário. Testar item retido, papel, motivo, prévia stale, vínculo novo, falha em cada passo, dois Admins, órfão, restart e auditoria sem conteúdo.

## Aceite e DoD

- [ ] Sem restore comprovado, comando/rota permanece desabilitado.
- [ ] Apenas Admin, com motivo/confirmação e prévia atual, inicia.
- [ ] Item retido é recusado inclusive para Admin.
- [ ] Falha parcial é recuperável e nunca aparece como sucesso.
- [ ] Auditoria permanente não contém conteúdo fiscal.

DoD: gate, schema, workflow, UI, recovery/runbook e fault injection verdes. **Blocked:** evidência P9-02; desenho físico da saga é Proposed.
