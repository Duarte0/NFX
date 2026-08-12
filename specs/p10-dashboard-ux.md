# Experiência de dashboard

## Metadados

- **Fase/status/versão:** P10-03 — implementação concluída e verificada no issue 0036 — v1.1.
- **Dependências:** P10-01, P10-02 e `p8-dashboard-and-operational-health.md`.
- **Fontes:** PRD FR-DASH-001..003, NFR-008..012, AC-013/023/024/026; Plano P10-03.

## Objetivo e limites

Modernizar a apresentação de cards, comparação de período, hierarquia operacional, estados e drill-downs já implementados. A spec não autoriza recalcular métricas/filtros/capacidades no navegador, criar cache/snapshot, nem mostrar saúde técnica a não-Administradores.

## Estado atual e contrato preservado

`GET /api/dashboard` continua dono da agregação e retorna período atual/anterior comparáveis; o período é `[from,to)`, de mesma duração, consecutivo e sem sobreposição. O cliente não recalcula métrica, comparação, estado de fonte ou elegibilidade. Cada card clicável deve usar o URL/filtro allowlisted produzido pelo servidor, abrir a lista canônica e continuar reconciliável com seu total bounded. Cards sem fonte, stale, parcial, degradada ou indisponível devem declarar estado e frescura quando recebida; zero só pode aparecer quando o owner declarar zero real. Backup e detalhes técnicos permanecem Admin-only, inclusive por acesso direto.

Cards devem separar grupo operacional (empresas/documentos/valores), coleta/jobs e certificado/saúde, sem alterar os grupos, totais ou links existentes. Seleção de período deve apresentar intervalo atual e comparativo anterior em Brasília/BRL quando aplicável. Loading preserva a última leitura segura identificada como desatualizada, se houver; erro de um card não pode mascarar dados ou erro dos demais.

## Interação, segurança e testes

Período, cards e drill-down devem ter rótulos claros, ordem de teclado, loading e erro compreensíveis; o navegador não pode revelar payload, lease, política, identificadores de backup ou dados fiscais adicionais. Validar dataset sintético de zero real versus desconhecido, fronteiras de período, cada link publicado, RBAC Admin/Operador/Visualizador, erro isolado de fonte, navegação por URL e TypeScript/lint/build.

## Aceite

- [x] A apresentação mantém as seleções, totais e capacidades do owner P8 sem escrita.
- [x] Cada drill-down continua URL-endereçável, bounded e reconciliado.
- [x] Estado de fonte é explícito e acessível; falha de um card não mascara os demais.
- [x] Não há cálculo de domínio ou autorização feita pelo cliente.

## Evidência de implementação e validação

O issue 0036 reorganizou `DashboardSection` em grupos semânticos de empresas/documentos,
coletas/processamento e certificados/capacidades, preservando a ordem, os IDs, os valores,
períodos, status, frescura e URLs/filtros produzidos por `GET /api/dashboard`. A apresentação
também expõe a saúde operacional e o backup somente quando o payload já contém essa seção
autorizada; Visualizadores e Operadores não recebem fallback de dados técnicos. O navegador não
recalcula métrica, período, filtro, elegibilidade ou autorização.

O último payload seguro permanece visível com indicação explícita de desatualização durante
refresh e depois de uma falha, com retry seguro. Sequenciamento de requisições evita que resposta
antiga substitua seleção nova; o mesmo guard foi aplicado ao drill-down de jobs, que mantém linhas
seguras em falha e traduz códigos allowlisted para mensagens de interface.

O contrato `npm --prefix frontend run test:ui-contract` cobre dataset sintético com zero real,
indisponibilidade, parcial, degradado, desatualizado, comparação de período, grupos, URLs,
redaction e RBAC. `npm --prefix frontend run lint` e `npm --prefix frontend run build` passaram.
A matriz `docker compose -f docker-compose.test.yml run --rm --no-deps browser-tests` passou 90
testes em Chrome, Firefox e Edge nas larguras 1024, 1280 e 1440 px. `make lint`, `make test-unit`,
`make build` e `make smoke` passaram. Não houve migration, dependência, endpoint ou alteração de
payload; Graphify foi atualizado após a implementação.
