# Dashboard e saúde operacional

## Metadados

- **Fase/status:** P8 — implementável progressivamente conforme fontes de dados.
- **Backlog:** P8-02. **Dependências:** P3-04 e capacidades P2–P7 disponíveis.
- **PRD:** FR-DASH-001, FR-DASH-002, FR-DASH-003; FR-OPS-001, BR-OPS-001, BR-DASH-001; NFR-001, NFR-002, NFR-008. **Aceite:** AC-013, AC-023, AC-024.
- **Arquitetura:** seções 14, 26, 32, 35, 36, 39 e 40; ADR-012 quanto à limitação de backup.
- **Implementação:** slice inicial P8-02 concluído no issue 0018; fontes P5–P7, rendering,
  disco e backup continuam explicitamente indisponíveis para incrementos posteriores.

## Propósito e resultado

Mostrar visão operacional/fiscal com comparação temporal e drill-down fiel. Métrica indisponível deve ser `desconhecida/degradada`, nunca zero inventado. Detalhes técnicos e backup são exclusivos de Admin.

## Baseline, escopo e não escopo

Métricas iniciais vêm P3; dados de empresas/certificados/documentos surgem P2–P7 e backup em P9. Implementar contratos agregados capazes de declarar capacidade ausente. Não criar notificações, relatórios especializados, BI ou metas de SLA inexistentes.

## Contratos e dados Proposed

Operação é dona de health; domínios são donos dos dados agregados. Contrato de dashboard recebe intervalo com limites claros e retorna valor atual, anterior, status/frescura e filtro de drill-down. Período anterior tem mesma duração, termina exatamente no início do atual e não sobrepõe. **Proposed:** consultas diretas/indexadas ou snapshots locais; se materialização for necessária, registrar origem/frescura e reconciliação. Não duplicar autoridade do domínio.

Indicadores: empresas ativas/inativas; documentos/quantidades/valores; NF-e/NFS-e e categorias; certificados expirados/próximos; coletas recentes/em execução; pendências/falhas/bloqueios/atrasos. Saúde Admin: espaço, DB, MinIO, fontes, processamento e backup. Cada indicador clicável usa filtros suportados por P7 e deve reconciliar contagem com a lista.

## UI, autorização e observabilidade

Todos veem dashboard fiscal permitido; apenas Admin vê detalhes técnicos/backup/configuração. Interface pt-BR, Brasília/BRL, com loading, parcial, stale, degradado e indisponível. Health distingue liveness/readiness/dependência. Métricas próprias: latência, freshness, erro e divergência de drill-down; logs sem dados fiscais agregados desnecessários.

## Falhas e testes

Falha de uma fonte não derruba demais cards. Cache/snapshot antigo mostra idade. Testar intervalos inclusivo/exclusivo, DST de Brasília quando aplicável, moeda, zero real versus desconhecido, agregações, drill-down, RBAC, backup ausente e browsers. Dataset sintético com valores conhecidos prova contagens.

## Aceite e DoD

- [ ] Atual/anterior têm duração igual, são consecutivos e não sobrepostos.
- [ ] Todo card clicável abre lista com filtro equivalente e contagem reconciliada.
- [ ] Ausência/frescura é explícita, não zero silencioso.
- [ ] Saúde/backup técnico é Admin-only server-side.
- [ ] Não há notificação ou relatório fora do MVP.

DoD: contrato, queries/snapshots decididos, UI, RBAC, telemetria e testes verdes. **Proposed:** estratégia de agregação/cache e limites padrão de período.

### Evidência do slice inicial P8-02

`GET /api/dashboard` e a seção React `#dashboard` implementam agregação calculate-on-read para
empresas, documentos persistidos, coletas e jobs, com intervalo `[from,to)`, comparação de mesma
duração, drill-down bounded e estados de frescura/degradação. Saúde de dependências permanece
Admin-only e reutiliza o avaliador P3-04; documentos/fonte fiscal futura, PDF, disco e backup
continuam `unavailable`. Não há migration, snapshot, cache ou escrita fiscal. Evidência: testes
unitários de intervalo/falha isolada e testes de integração de agregação, zero, RBAC e health,
além de Ruff/mypy/TypeScript/Vite.
