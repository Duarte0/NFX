# Exportação ZIP assíncrona

## Metadados

- **Fase/status:** P8 — concluída no issue 0021. PDF é dependência somente quando solicitado.
- **Backlog:** P8-01. **Dependências:** P3-01, P7-01, P7-02 e P7-03 para incluir PDF.
- **PRD:** FR-ZIP-001, FR-ZIP-002, FR-ZIP-003; BR-ZIP-001, BR-ZIP-002, BR-ZIP-003, BR-ZIP-004; NFR-006, AUD-006. **Aceite:** AC-012, AC-014.
- **Arquitetura:** ADR-011; seções 14, 17, 20, 26, 27, 30, 33, 36, 37 e 40.

## Propósito e resultado

Criar exportação multiempresa com seleção congelada, job retomável, estrutura segura, completude explícita, acesso restrito e expiração em 24 horas, sem alterar origem fiscal.

## Baseline, escopo e não escopo

P3 fornece jobs; P7 fornece filtros, artefatos e download individual. Esta spec adiciona somente exportação em lote temporária. Não cria novos filtros, CSV/Excel, armazenamento fiscal alternativo nem torna PDF obrigatório quando ele não fizer parte da seleção.

## Estado e contratos Proposed

Exportações é dona do filtro/composição/expiração; objetos guarda ZIP. **Proposed:** exportação com solicitante, filtro canônico, snapshot/critério de seleção, contagem esperada/produzida, arquivos, bytes, estado, job/objeto, criado/expira, resultado/erros seguros; itens registram documento/artefato/status/caminho. Estados Accepted pela arquitetura: pendente, processando, completo, parcial, falho, disponível, expirado, excluído. Índices por solicitante/estado/expiração; chave idempotente definida localmente sem impedir duas solicitações intencionais.

Pedido valida filtros P7 e autorização, persiste-os antes do job. Worker não amplia o escopo quando novos documentos chegam. Completo exige todos os artefatos selecionados confirmados; parcial lista ausências/falhas. Caminhos seguem exatamente as árvores do PRD, com segmentos sanitizados, determinísticos e sem colisão/traversal. Expiração remove somente ZIP temporário.

## UI e autorização

Todos autenticados solicitam ZIP permitido. Solicitante e Administrador listam/baixam; Operador/Visualizador não acessam ZIP alheio. Cada download revalida sessão, ownership/admin, disponibilidade e expiração. Telas: criação a partir de filtros, lista própria, detalhe/progresso, parcial e expirado; Admin pode consultar os demais.

## Segurança, auditoria, observabilidade

Evitar zip bomb reverso por limites de entrada/saída, streaming e quota configurável **Proposed**; worker com recursos limitados. Não usar texto cru em nomes. Auditar solicitação/download/negação; logs sem conteúdo; métricas de duração/tamanho/itens/parcial/expirado/falha.

## Falhas, recovery e testes

Morte do worker retoma sem duplicar itens; arquivo ausente produz parcial; falha final não apaga temporário/origem até reconciliação; cleanup idempotente. Testar multiempresa, frozen filters, terceiro, Admin, expiração 23:59/24:00, traversal/Unicode/colisão, objeto divergente, PDF ausente, grande volume sintético e restart.

## Aceite e DoD

- [x] Filtros/seleção ficam congelados e auditáveis.
- [x] Estrutura de caminhos corresponde ao PRD e bloqueia traversal.
- [x] Parcial nunca é apresentado como completo.
- [x] Só solicitante/Admin baixa e expiração ocorre em 24h.
- [x] Cleanup nunca remove fonte fiscal.

DoD: migrações, jobs, composição/cleanup, UI, auditoria/métricas e testes verdes.

Implementado no issue 0021: `nfx.exports` congela a seleção P7 em itens
documento/artefato, enfileira `export.zip`, compõe somente objetos finalizados e verificados,
mantém resultados parciais explícitos e serve apenas ZIPs `available` dentro da janela de 24
horas. O artifact lógico `export_zip_temp` é o único alvo do cleanup; fontes fiscais permanecem
protegidas. Limites locais adotados: 100 itens, 50 MiB por entrada e 100 MiB por ZIP. O DoD foi
validado com as suites unitária e de integração, lint/typecheck, build e smoke em 2026-08-11.
