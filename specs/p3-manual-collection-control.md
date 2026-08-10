# Controle manual de coleta

## Metadados

- **Fase/status:** P3 — concluída e validada no issue 0005 (2026-08-09).
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

## Implementação e evidência

O issue 0005 implementa `CollectionExecution` e o estado operacional persistido em `CompanyFlow`,
com migration `0012_companyflow_blocked_reason_and_more`. `request_collection` é a única porta
para comandos manual, retry e inicial automático; cria jobs sintéticos por família sob lock e
reutiliza a execução ativa. As rotas protegidas são `/api/collections`,
`/api/companies/<id>/collection`, `/collection/request` e `/collection/retry/<execution_id>`.
O scheduler consome o handoff de certificado e o worker reconcilia somente resultados sintéticos;
nenhum transporte fiscal ou conteúdo de documento é acessado.

Os estados `concluded`, `empty`, `partial`, `retrying`, `cooldown`, `blocked` e `failed` são
persistidos com códigos seguros, e pedidos, recusas, duplicidades, retry e origem automática são
auditados. A UI exibe o estado independente de NF-e/NFS-e e só oferece mutações a Administrador
ou Operador; o backend revalida todas as regras.

## Aceite e DoD

- [x] Apenas Admin/Operador solicitam/repetem coleta.
- [x] Pedido concorrente retorna execução existente sem novo job.
- [x] Cooldown, bloqueio, empresa/fluxo e certificado são revalidados no servidor.
- [x] Estado por NF-e/NFS-e é independente e visível.
- [x] Toda ação/recusa relevante é auditada sem segredo.

DoD: migrações, comandos, contratos HTTP/UI, reconciliação, auditoria e testes verdes. A divisão
de “completa” em duas execuções por família foi adotada para preservar rastreabilidade e exclusão
mútua. **Proposed:** códigos HTTP/payloads foram definidos como códigos seguros e estáveis na
implementação.
