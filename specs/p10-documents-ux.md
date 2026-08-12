# Experiência de documentos

## Metadados

- **Fase/status/versão:** P10-04 — implementação concluída e verificada no issue 0037 — v1.1.
- **Dependências:** P10-01, P10-02 e specs P7-01..03.
- **Fontes:** PRD FR-DOC-001..006, NFR-004/006/008..012, AC-010/011/023/026; Plano P10-04.

## Objetivo e não escopo

Modernizar busca, filtros, resultados, detalhe e ações XML/PDF mantendo a consulta fiscal existente. Não altera parâmetros URL, contratos HTTP, retenção, identidade/integridade, geração PDF, autorização ou conteúdo fiscal retornado.

## Estado atual e contrato funcional

A área `#documentos` deve preservar filtros allowlisted, suas fronteiras temporais, paginação/ordenação e deep links; parâmetros inválidos continuam erro do servidor e não podem ser normalizados silenciosamente no cliente. Filtros ativos devem ser perceptíveis e o resultado deve informar contagem/paginação recebidas, sem inventar total. Detalhe, download XML, solicitação/estado/download PDF e ausência/bloqueio de renderização refletem exatamente a resposta do owner P7. Quarentena, conflito, cobertura e fonte indisponível precisam de rótulos distintos de vazio válido e não expõem XML, hashes, erros internos ou metadados além do contrato autorizado.

O detalhe deve manter associação explícita entre documento selecionado e ações; ação assíncrona de PDF deve prevenir duplo envio apenas como proteção de interação, consultar o estado durável após reload e nunca substituir XML disponível por PDF falho. A apresentação não pode adicionar filtro de valor, exportação Excel/CSV ou campo de pesquisa fora do contrato P7.

## Segurança, falhas e testes

Todas as ações devem manter CSRF, sessão e RBAC server-side; links de download não podem ser inventados, retidos ou reutilizados além do contrato. Validar consulta vazia, resultado paginado, cada filtro/URL permitido, filtro inválido, erro/degradação, detalhe autorizado/não autorizado, XML/PDF disponível/pendente/falhou/bloqueado, reload, teclado/foco e TypeScript/lint/build com fixtures sintéticas.

## Aceite

- [x] Busca, filtros, paginação e URLs preservam seleção e limites canônicos.
- [x] Estados fiscalmente distintos continuam distinguíveis e acessíveis.
- [x] Ações XML/PDF preservam autorização e estado sem duplicar regra de domínio.
- [x] Nenhum dado fiscal ou detalhe técnico adicional é exposto.

## Evidência de implementação e validação

O issue 0037 modernizou `DocumentsSection` usando as primitives compartilhadas, mantendo os
filtros P7, query strings, hashes e cursores opacos publicados pelo servidor. A apresentação
mostra os totais, limites, truncamento e fronteira `[from,to)` recebidos, preserva a última
leitura segura durante loading/erro e traduz estados de consulta, resultado, documento e PDF
para rótulos seguros. Respostas antigas não substituem filtros, cursores, detalhe ou operação
de PDF mais recentes.

O detalhe associa explicitamente o documento selecionado às ações XML/original e PDF, usando
somente os URLs autorizados na resposta. Estados pending, failed, unsupported e unavailable
permanecem distintos; regeneração é protegida contra duplo envio e consulta novamente o estado
durável. Metadados técnicos, códigos brutos, bytes fiscais, chaves e segredos não são renderizados.

O contrato sintético cobre filtros/deep links, cursor, estados, stale/error/retry, ações e
redaction. A matriz Docker cobre os três papéis autenticados, sessões anônima/expirada, foco e
teclado em Chrome, Firefox e Edge a 1024/1280/1440 px. Não houve mudança de endpoint, payload,
backend, migration ou dependência; Graphify foi atualizado após a implementação.
