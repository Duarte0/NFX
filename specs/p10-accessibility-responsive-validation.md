# Acessibilidade, responsividade e validação UX

## Metadados

- **Fase/status/versão:** P10-08 — implementada e verificada no issue 0041 — v1.1.
- **Dependências:** P10-02..07.
- **Fontes:** PRD NFR-009..012 e AC-023/026; Arquitetura §10.4; Plano P10-08.

## Objetivo e não escopo

Validar e ajustar transversalmente os fluxos P10 em desktop/notebook. Não amplia o MVP para mobile, não altera contratos/autorizações, e não substitui testes funcionais dos owners de domínio.

## Matriz e requisitos verificáveis

A matriz mínima é Chrome, Firefox e Edge desktop atuais em 1024, 1280 e 1440 px; mobile não é alvo. Nenhuma largura pode cortar, sobrepor ou tornar por mouse somente um controle, uma ação crítica, um filtro aplicado, um erro ou dado operacional essencial. Tabelas podem rolar horizontalmente dentro de contêiner identificado, desde que não imponham rolagem horizontal à página e retenham cabeçalho/associação compreensível.

Ordem de tabulação deve seguir a leitura visual; foco visível deve usar o token P10-01; controles devem ter nome/label, estado e mensagem semânticos; ação por mouse precisa alternativa por teclado. Diálogo/confirmador crítico, se usado, deve reter foco, permitir Escape somente quando cancelar for seguro e devolver foco ao disparador. Contraste segue P10-01, e cor não é o único sinal. Loading, vazio válido, erro, indisponibilidade, degradação, bloqueio, sucesso e ação crítica devem empregar a variante canônica sem apagar informação funcional.

## Evidência e aceite

Validar, com contas/fixtures sintéticas, autenticação e cada papel, navegação/âncoras/deep links, dashboard, documentos/XML/PDF, empresas/certificados/coletas, ZIP e administração crítica. A evidência deve registrar as capacidades de skills/plugins aplicadas, browser, largura, papel, fluxo, resultado, captura/descrição reproduzível, divergências visuais encontradas e refinamentos realizados. Quando a skill selecionada exigir aprovação de conceito/design antes da implementação, a evidência deve registrar a aprovação correspondente; essa etapa é obrigatória e não pode ser pulada.

Testes automatizados possíveis, inspeção manual da matriz e TypeScript/lint/build são obrigatórios; uma divergência vira issue e mantém o slice afetado aberto, não é mascarada visualmente. A validação visual e o uso de skills/plugins não substituem os testes funcionais, contratos, RBAC ou estados definidos pelos owners de domínio.

- [x] Fluxos e estados críticos passam nos três browsers e nos tamanhos declarados.
- [x] Foco, teclado, labels e contraste são verificáveis em toda área entregue.
- [x] Nenhuma regressão de contrato, âncora, papel ou autorização server-side é encontrada.
- [x] A evidência registra as skills/plugins aplicáveis, a aprovação de conceito/design quando exigida e os refinamentos visuais realizados.
- [x] Mobile permanece explicitamente fora do escopo.

## Evidência de implementação e validação — issue 0041

`frontend/browser-tests/accessibility.spec.ts` adiciona o gate transversal para dashboard,
documentos, empresas/certificados/coletas, exportações, administração e shell. As asserções
verificam landmark `main`, headings e nomes de seções, associações label/control,
`aria-describedby`, live regions, nomes de diálogos, redaction, papéis/sessões negativas,
overflow horizontal da página, contenção de tabelas e clipping de ações em toda a matriz.

Os diálogos críticos de usuários e exclusão controlada agora recebem foco ao abrir, têm
`aria-labelledby`, aceitam Escape somente enquanto o cancelamento é seguro e devolvem foco ao
controle disparador. O botão de cancelamento de exclusão fica bloqueado durante uma solicitação
em andamento; nenhum endpoint, estado de negócio, contrato, âncora, papel ou autorização foi
alterado.

Skills/plugins avaliados: a skill instalada `graphify` foi usada para navegação de relações entre
issue, spec, código e testes; não havia skill/plugin frontend ou browser adicional instalado no
catálogo ativo. Nenhuma skill aplicável exigia aprovação de conceito/design antes da implementação;
portanto não houve gate externo de aprovação. O refinement foi limitado ao defeito de foco/nome de
diálogo demonstrado por teste red-green. Não foram incluídas capturas com dados; as descrições
reproduzíveis são as rotas sintéticas e as métricas automatizadas abaixo.

Validação executada:

- `npm --prefix frontend run test:ui-contract` — passou; oito estados, dez pares de contraste,
  labels, landmarks, dialogs, redaction e overflow de tabela.
- `npm --prefix frontend run lint` e `npm --prefix frontend run build` — passaram.
- `docker compose -f docker-compose.test.yml run --build --rm --no-deps browser-tests npx playwright test browser-tests/admin.spec.ts --project=chrome-1024` — 9 passaram; a nova asserção falhou antes da correção e passou depois.
- `make test-browser` — 342 passaram na matriz Chrome/Firefox/Edge × 1024/1280/1440.

Os testes usam exclusivamente fixtures sintéticas, não adicionam dependência, backend, migration,
telemetria ou regra mobile. A inspeção manual determinística usa as mesmas rotas e registra como
critério a ausência de scroll horizontal de página, ações fora da viewport e overflow somente em
`.ui-table-wrap`; não houve divergência a abrir ou refinar além dos diálogos descritos acima.
