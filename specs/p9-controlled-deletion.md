# Exclusão definitiva controlada

## Metadados

- **Fase/status:** P9 — implementada e verificada no issue 0024; P9-04 foi concluído no
  issue 0031 e P9-05 permanece bloqueado pelas decisões externas e pelo backup físico.
- **Backlog:** P9-03. **Dependências:** P8-03 e P9-02.
- **PRD:** RET-005, RET-006, RET-008, AUD-006, AUD-008, AUD-009. **Aceite:** AC-014, AC-015.
- **Arquitetura:** seções 14, 17, 27, 28, 31, 33, 37, 40 e 41.

## Propósito e resultado

Permitir somente a Administrador excluir manualmente documento elegível após prévia exata, confirmação e motivo, tratando vínculos/objetos coerentemente e preservando auditoria sem conteúdo fiscal.

## Baseline e escopo

P8 calcula elegibilidade e prévia, mas não apaga. P9-02 já fornece backup verificável, validação de integridade e procedimento manual de recuperação; a ausência de automação para reconstruir PostgreSQL/MinIO não bloqueia esta spec. Não exclui empresa, usuário, backup, lote automático ou item retido.

## Estado e contrato implementado

Retenção é dona da decisão; Artefatos executa tratamento de bytes; Documentos mantém estado coerente; Auditoria preserva evento. **Implementado:** solicitação de exclusão com Admin, motivo, prévia ID/hash/versão, estado, timestamps e passos/itens; estados `pendente|em_execução|recuperação_necessária|falha|concluída`. Constraint impede decisão ativa concorrente por documento; índices por estado/data/documento.

Contrato recebe prévia e confirmação inequívoca, revalida no servidor: papel, sessão, elegibilidade atual e hash do escopo. Se qualquer vínculo mudou, recusa e exige nova prévia. Execução marca intenção, trata documento/eventos/original/XML/PDF/derivados e só conclui quando não há órfão/registro enganoso. Auditoria guarda IDs/hash/motivo/resultado, nunca conteúdo. A implementação adota a saga em duas fronteiras: remove cada byte após conferir digest/tamanho/versão e só então resolve referências protegidas e registros relacionais numa transação PostgreSQL; qualquer divergência fica em `recovery_required` para retomada administrativa.

## UI, segurança e observabilidade

Tela Admin mostra exatamente o escopo, datas/regra, artefatos e confirmação; Operador/Visualizador não veem e recebem 403. Não aceitar confirmação genérica reutilizável. Logs redigidos; métricas de solicitado/bloqueado/falha/recovery/concluído e órfão.

## Falhas, recovery e testes

Não há transação atômica DB+MinIO: execução é saga/checkpoint implementada, retomável e idempotente. Falha após remover alguns objetos não declara sucesso; bloqueia nova decisão até recovery e usa backup/runbook quando necessário. Testar item retido, papel, motivo, prévia stale, vínculo novo, falha em cada passo, dois Admins, órfão, restart e auditoria sem conteúdo.

## Aceite e DoD

- [x] Backup verificável, validação de integridade e procedimento manual de recuperação permanecem preservados; ausência de restore automatizado não bloqueia comando/rota.
- [x] Apenas Admin, com motivo/confirmação e prévia atual, inicia.
- [x] Item retido é recusado inclusive para Admin.
- [x] Falha parcial é recuperável e nunca aparece como sucesso.
- [x] Auditoria permanente não contém conteúdo fiscal.

DoD: schema, workflow, UI, recovery/runbook e fault injection verdes. Evidência: migration `0020`, `retention.deletion`, rotas/UI, worker `retention.delete`, métricas bounded, testes unitários e integração isolada; o desenho físico da saga foi adotado e testado nesta implementação.
