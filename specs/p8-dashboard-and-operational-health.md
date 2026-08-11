# Dashboard e saúde operacional

## Metadados

- **Fase/status:** P8 — implementável progressivamente conforme fontes de dados.
- **Backlog:** P8-02. **Dependências:** P3-04 e capacidades P2–P7 disponíveis.
- **PRD:** FR-DASH-001, FR-DASH-002, FR-DASH-003; FR-OPS-001, BR-OPS-001, BR-DASH-001; NFR-001, NFR-002, NFR-008. **Aceite:** AC-013, AC-023, AC-024.
- **Arquitetura:** seções 14, 26, 32, 35, 36, 39 e 40; ADR-012 quanto à limitação de backup.
- **Implementação:** slice inicial P8-02 concluído no issue 0018; fontes P5–P7, rendering e
  disco continuam explicitamente indisponíveis para incrementos posteriores; o status seguro de
  backup P9-02 foi integrado no issue 0025; o drill-down de execuções de coleta foi concluído no
  issue 0026; o drill-down de documentos foi concluído no issue 0027; o drill-down de empresas foi
  concluído no issue 0028. Os drill-downs de certificado e job continuam em slices próprios.

## Propósito e resultado

Mostrar visão operacional/fiscal com comparação temporal e drill-down fiel. Métrica indisponível deve ser `desconhecida/degradada`, nunca zero inventado. Detalhes técnicos e backup são exclusivos de Admin.

## Baseline, escopo e não escopo

Métricas iniciais vêm P3; dados de empresas/certificados/documentos surgem P2–P7 e backup em P9. Implementar contratos agregados capazes de declarar capacidade ausente. Não criar notificações, relatórios especializados, BI ou metas de SLA inexistentes.

## Contratos e dados Proposed

Operação é dona de health; domínios são donos dos dados agregados. Contrato de dashboard recebe intervalo com limites claros e retorna valor atual, anterior, status/frescura e filtro de drill-down. Período anterior tem mesma duração, termina exatamente no início do atual e não sobrepõe. O owner `nfx.collection` expõe `GET /api/collections/executions` para o slice de coleta, com `from`, `to` e o filtro allowlisted dos cinco cards, total server-side e página limitada. **Proposed:** consultas diretas/indexadas ou snapshots locais; se materialização for necessária, registrar origem/frescura e reconciliação. Não duplicar autoridade do domínio.

Indicadores: empresas ativas/inativas; documentos/quantidades/valores; NF-e/NFS-e e categorias; certificados expirados/próximos; coletas recentes/em execução; pendências/falhas/bloqueios/atrasos. Saúde Admin: espaço, DB, MinIO, fontes, processamento e backup. Cada indicador clicável usa filtros suportados por P7 e deve reconciliar contagem com a lista.

## UI, autorização e observabilidade

Todos veem dashboard fiscal permitido; apenas Admin vê detalhes técnicos/backup/configuração. Interface pt-BR, Brasília/BRL, com loading, parcial, stale, degradado e indisponível. O drill-down de coleta mantém o período e o estado na URL, consulta o servidor e mostra total, vazio válido, indisponível, inválido ou degradado sem filtrar no browser. Health distingue liveness/readiness/dependência. Métricas próprias: latência, freshness, erro e divergência de drill-down; logs sem dados fiscais agregados desnecessários.

## Falhas e testes

Falha de uma fonte não derruba demais cards. Cache/snapshot antigo mostra idade. Testar intervalos inclusivo/exclusivo, DST de Brasília quando aplicável, moeda, zero real versus desconhecido, agregações, drill-down, RBAC, backup ausente e browsers. Dataset sintético com valores conhecidos prova contagens.

## Aceite e DoD

- [ ] Atual/anterior têm duração igual, são consecutivos e não sobrepostos.
- [ ] Todo card clicável abre lista com filtro equivalente e contagem reconciliada.
- [ ] Ausência/frescura é explícita, não zero silencioso.
- [x] Saúde/backup técnico é Admin-only server-side.
- [ ] Não há notificação ou relatório fora do MVP.

DoD: contrato, queries/snapshots decididos, UI, RBAC, telemetria e testes verdes. **Proposed:** estratégia de agregação/cache e limites padrão de período.

### Evidência do slice inicial P8-02

`GET /api/dashboard` e a seção React `#dashboard` implementam agregação calculate-on-read para
empresas, documentos persistidos, coletas e jobs, com intervalo `[from,to)`, comparação de mesma
duração, drill-down bounded e estados de frescura/degradação. Saúde de dependências permanece
Admin-only e reutiliza o avaliador P3-04; documentos/fonte fiscal futura, PDF e disco continuam
`unavailable`. O incremento do issue 0025 integra, somente para Administradores, o resumo de
`backup_status()` com estado do último conjunto, idade medida do último sucesso, retenção limitada
e última validação, sem caminhos, IDs ou manifesto. Falhas da fonte degradam somente o resumo de
backup; não há migration, snapshot, cache ou escrita fiscal. Evidência: testes unitários de
intervalo/falha isolada/mapeamento seguro e testes de integração de agregação, zero, RBAC, health,
backup e leituras repetidas, além de Ruff/mypy/TypeScript/Vite.

### Evidência do slice de coleta — issue 0026

`GET /api/collections/executions?from=YYYY-MM-DD&to=YYYY-MM-DD&state=recent|running|failed|blocked|partial`
é uma leitura autenticada, bounded e sem cursor. O owner `nfx.collection` compartilha com o
dashboard a consulta `CollectionExecution`, as fronteiras civis de Brasília `[from,to)` e o mapa
canônico de estados; `recent` é o filtro já existente de todas as execuções, não um novo estado
persistido. A resposta limita a página a 50 linhas, ordena por timestamp/UUID, retorna total e
somente metadados redigidos. Falha da fonte retorna indisponibilidade/degradação sem zero inventado.
O slice é coberto por testes unitários de parsing e integração PostgreSQL/MinIO de reconciliação,
limites, RBAC, redaction, erro e no-write, além do contrato TypeScript/ESLint/Vite. Os demais
cards clicáveis permanecem pendentes nos issues 0028–0030.

### Evidência do slice de documentos — issue 0027

Os sete cards (`total`, `nfe`, `nfse`, `entrada`, `saida`, `tomados` e `prestados`) compartilham
com `GET /api/documents` um mapa allowlisted de filtros P7. Os links preservam o período atual
`from`/`to` e usam `tomada`/`prestada` como categorias NFS-e; o arquivo traduz esse período para
o contrato inclusivo de emissão sem incluir a data final. A resposta mantém a lista P7 bounded e
adiciona `total`, calculado somente sobre documentos persistidos da mesma seleção; quarentena e
estados de coleta continuam separados.

O slice retorna página determinística, filtro/boundary normalizados e apenas metadados seguros.
Parâmetros repetidos, desconhecidos, incompletos, reversos ou acima de 366 dias são rejeitados;
falhas de fonte retornam `503` sem zero inventado. A autorização continua server-side para os
três papéis, a auditoria segue somente a política P7 e leituras não criam estado durável. Testes
unitários e a integração PostgreSQL/MinIO cobrem as sete reconciliações, fronteiras, zero,
redaction, erro e ausência de escrita; o contrato React é validado por TypeScript/ESLint/Vite.

### Evidência do slice de empresas — issue 0028

Os cards `companies.active` e `companies.inactive` compartilham com `GET /api/companies` o mapa
allowlisted `lifecycle=active|inactive`: `active` seleciona `CompanyStatus.ACTIVE`, e `inactive`
seleciona exatamente `REGISTERED` e `DEACTIVATED`. Administradores e Operadores recebem links
para `#empresas` com o filtro explícito; Visualizadores não recebem link para a área protegida
por `ADMINISTER_COMPANIES`.

A resposta da lista preserva `status`, `search`, `limit` e `cursor`, adiciona filtro normalizado,
total da seleção completa, truncamento e paginação determinística por UUID. O total e a página
usam a mesma queryset de status, inclusive em páginas continuadas; filtro lifecycle repetido,
conflitante, desconhecido ou inválido retorna `400`. Falha da fonte retorna `503` sem zero
inventado. A UI hidrata o filtro pela URL e exibe total reconciliado, vazio válido, carregamento,
indisponibilidade, degradação e filtro inválido sem autorizar ou recalcular no browser.

O incremento não cria migration, cache, snapshot, job, auditoria, mutação ou transição de empresa.
Testes unitários e integração PostgreSQL/MinIO cobrem os três estados, reconciliação, zero,
paginação, RBAC, sessão expirada, filtros inválidos, falha isolada, redaction e no-write; o
contrato frontend é verificado por TypeScript/ESLint/Vite.
