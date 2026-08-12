# Shell de aplicação desktop/notebook

## Metadados

- **Fase/status/versão:** P10-02 — implementação concluída e verificada — v1.2.
- **Dependências:** P10-01. **Seguida por:** P10-03..08.
- **Fontes:** PRD NFR-010..012, AC-023 e AC-026; Arquitetura §10.4; Plano P10-02.

## Objetivo, escopo e não escopo

Entregar composição visual consistente com sidebar, header, identidade da sessão e navegação para desktop/notebook. Não cria roteamento de cliente, estado global, novos endpoints, nem muda composição/visibilidade funcional por papel.

## Estado atual e contrato de navegação

Hoje `App` compõe todas as features em uma página e navega por hash; seus links disparam o carregamento local já existente. O shell deve preservar `App → features → shared`, as âncoras `#dashboard`, `#documentos`, `#exportacoes`, `#empresas`, `#coletas`, `#usuarios`, `#auditoria` e `#retencao`, e todos os URLs de drill-down/query já publicados. A baseline publica `#certificados`, mas não há destino DOM: P10-02 deve criar um único destino `#certificados` nos controles autorizados de certificado dentro da área de empresas. Esta correção substitui o link sem destino; não cria uma feature ou rota de certificado paralela.

Navegação por hash, deep link e atualização de página devem manter a área endereçável e disparar apenas os carregamentos já previstos. Dashboard, Documentos, Exportações e Coletas permanecem para autenticados; Empresas/Certificados para Administrador/Operador; Usuários/Auditoria/Retenção para Administrador. O shell deve ter landmark principal, navegação nomeada, item ativo perceptível e um salto para conteúdo que recebe foco. UI pode ocultar opções, mas acesso direto e cada ação continuam autorizados no servidor.

## Estados, compatibilidade e validação

Header deve apresentar apenas identidade/papel da sessão, logout e contexto Brasília/BRL. Em largura de 1024 px ou maior, sidebar/header/conteúdo não podem sobrepor controles, esconder item de navegação ou exigir rolagem horizontal; se a sidebar for compactada, texto/nome acessível do item permanece disponível. Sessões anônima/expirada exibem somente o fluxo de autenticação existente. Validar os três papéis, âncoras/deep links, 1024/1280/1440 px, teclado/foco, TypeScript/lint/build e Chrome, Firefox e Edge desktop.

## Aceite

- [x] Todas as áreas e links publicados permanecem endereçáveis e semanticamente equivalentes; `#certificados` passa a ter destino único e autorizado.
- [x] A visibilidade por papel e logout preservam a baseline; acesso direto continua protegido no servidor.
- [x] Shell responde a desktop/notebook com foco e teclado utilizáveis.
- [x] Não há router, estado global, dependência UI relevante ou alteração HTTP sem nova spec.

## Evidência de implementação e validação

`frontend/src/App.tsx` mantém a composição `App → features → shared` e acrescenta o shell
autenticado com header institucional, identidade/papel, logout, contexto de Brasília/R$, skip
link, sidebar nomeada e landmark principal focalizável. `navigationModel` concentra os hashes,
papéis e callbacks de carregamento existentes; o estado ativo é derivado do hash inicial e
sincronizado em `hashchange`, usando `aria-current="page"` e indicação visual sem reescrever
query strings ou URLs de drill-down.

`#certificados` é publicado uma única vez dentro de `CompaniesSection`, sob a mesma visibilidade
`canManage`, e não cria rota, endpoint, estado global, regra de autorização ou feature paralela.
Os tokens P10-01 sustentam a grade de duas colunas, o header, a sidebar, o foco e a mensagem
segura no conteúdo principal; tabelas e conteúdo do main preservam largura utilizável no baseline
desktop/notebook a partir de 1024 px.

O contrato `npm --prefix frontend run test:ui-contract` renderiza contextos sintéticos de
Administrador, Operador, Visualizador e anônimo, verificando landmarks, skip link, foco, estado
ativo, hashes, destino único, matriz positiva/negativa e ausência de requests/persistência na
composição. `npm --prefix frontend run lint` e `npm --prefix frontend run build` passaram.

A matriz reproduzível `docker compose -f docker-compose.test.yml run --rm --no-deps browser-tests`
passou 63 testes sintéticos em Chrome, Firefox e Edge, nas larguras 1024, 1280 e 1440 px. Ela
verifica identidade do browser, visibilidade e nome dos itens por papel, ausência de rolagem
horizontal, skip link e foco de teclado, atualização do item ativo por hash, preservação de
query/deep link e destino único de `#certificados`. O target instala os browsers isoladamente
no container e a fixture rejeita rede, mantendo contas e dados sintéticos; não há chamada fiscal,
credencial ou migração.
