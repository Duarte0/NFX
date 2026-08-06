# Controle manual de coleta

## Metadados

- **Fase/status:** P3 — pronta após jobs/políticas e RBAC/auditoria.
- **Backlog:** P3-05 exclusivamente.
- **Dependências:** P1-03, P1-05, P3-01 e P3-02.
- **PRD:** FR-COLL-001, BR-COLL-001, BR-COLL-003, BR-COLL-004, BR-COLL-005, BR-COLL-008, BR-COLL-009, AUD-005, AUD-008. **Aceite:** AC-004, AC-006, AC-017.
- **Arquitetura:** seções 10.1, 14, 19–22, 26, 27, 32, 36 e 37; ADR-005.

## Propósito e resultado

Permitir que Administrador/Operador solicitem coleta completa, somente NF-e, somente NFS-e e retry permitido, acompanhando estados por empresa/fluxo. Pedido duplicado retorna a execução ativa; bloqueio/cooldown nunca é ignorado.

## Baseline, escopo e não escopo

Usa engine de jobs P3 e empresa/certificado P2. Nesta fase handlers podem ser simulados; não integra SEFAZ/ADN nem ingere documentos. Visualizador não controla coleta. A inicial automática é acionada pelo evento de certificado válido, mas passa pelo mesmo serviço de comando e regras.

## Estado e contratos Proposed

Coleta é dona da execução e estado por empresa/família/fluxo. **Proposed:** execução com empresa, escopo `completa|nfe|nfse`, origem `automática|manual|retry`, solicitante opcional, estado, job, política efetiva, início/fim, resumo/erro; estado de fluxo mantém última tentativa/sucesso, próximo agendamento, cooldown, bloqueio, progresso e execução ativa. Constraint/lock impede duas execuções ativas para a mesma empresa e fluxo.

Comando interno `request_collection` valida empresa ativa, fluxo habilitado, certificado válido, cooldown/bloqueio, RBAC e idempotência; cria uma ou mais execuções/jobs e retorna IDs. Se já ativa, retorna a execução existente com resultado de conflito de negócio, não duplica. Retry referencia execução falha e só cria novo job se política permitir.

## UI, permissões e comportamento visível

Tela de empresa e visão de coletas mostram por NF-e/NFS-e: estado, tentativa/sucesso, próxima execução, cooldown/bloqueio, progresso, erro seguro e ação corretiva. Botões são ocultados/desabilitados conforme papel/estado, mas backend revalida. Estados: concluída, vazia, parcial, retry, bloqueada, falha e em execução. Não usar “Nenhum documento encontrado” antes de consulta fiscal válida (P4/P6).

Matriz: Admin/Operador solicitam e retry; Visualizador somente vê estado operacional permitido; execução automática não possui usuário, mas registra origem do sistema. Todos os comandos geram auditoria de início/recusa/retry/resultado com ator, IP, empresa/fluxo, motivo/correlação, sem certificado.

## Falhas, observabilidade e testes

Falha entre execução e enqueue deve ser transacional ou reconciliada; nunca deixar execução ativa sem job recuperável. Métricas: pedidos, recusas, ativas, duração, cooldown/bloqueio por classe. Testar três papéis, empresa desativada, fluxo pausado, certificado inválido, duplicidade concorrente, cooldown, retry permitido/proibido, inicial automática idempotente, browser e restart.

## Aceite e DoD

- [ ] Apenas Admin/Operador solicitam/repetem coleta.
- [ ] Pedido concorrente retorna execução existente sem novo job.
- [ ] Cooldown, bloqueio, empresa/fluxo e certificado são revalidados no servidor.
- [ ] Estado por NF-e/NFS-e é independente e visível.
- [ ] Toda ação/recusa relevante é auditada sem segredo.

DoD: migrações, comandos, contratos HTTP/UI, reconciliação, auditoria e testes verdes. **Proposed:** códigos HTTP/payloads e divisão de “completa” em jobs; implementação decide mantendo atomicidade e rastreabilidade.
