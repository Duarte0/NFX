# Entrega da aplicação React na rota raiz

## Metadados

- **Fase/status/versão:** follow-up de fundação — implementado e verificado no issue 0032; limite de rota supersedido por P10-09 — v1.3.
- **Dependências:** `p0-project-foundation.md`, `p1-authentication-sessions-and-rbac.md`.
- **Fontes:** Arquitetura §§9, 10.4 e 11; Plano “Rota raiz e build React”.

## Contexto e objetivo

A baseline histórica devolvia o placeholder `NFX INOV foundation` em `/`, embora a imagem Docker já construísse/copiasse `frontend/dist`. O issue 0032 consolidou a fronteira em `backend/nfx/urls.py`: `/` lê somente o `index.html` do diretório fixo, a ausência ou leitura inválida do build retorna `503`, e `assets/<path>` rejeita caminhos não canônicos e arquivos fora do diretório de assets resolvido.

O limite histórico de não haver fallback SPA foi supersedido somente para as rotas canônicas
aprovadas em [P10-09](p10-spa-url-navigation.md). A nova spec é o contrato canônico para esse
fallback limitado; as garantias de `503`, containment, MIME, API/health/sessão e ausência de
servidor de arquivos genérico continuam obrigatórias.

## Contrato, segurança e falhas

No contrato histórico entregue pelo issue 0032, `/` responde HTML do build e não havia fallback
SPA. Permanecem obrigatórios o MIME correto dos assets publicados pelo `index.html`, `503` para
build ausente sem placeholder/página de sucesso e confinement do diretório de distribuição, com
`404` para traversal, arquivo inexistente ou fora dele. O fallback limitado das nove rotas
canônicas é exclusivamente o delta de P10-09; esta spec não autoriza fallback genérico, mudança
de API, cache policy, upload de assets ou acesso a conteúdo sensível.

## Testes e aceite

Testar imagem/build presente, HTML e asset referenciado, MIME, build ausente (503), inexistente e traversal (404), e preservar endpoints API/health. A validação deve executar build TypeScript/Vite e smoke de runtime isolado.

- [x] `/` não devolve o placeholder e entrega o `index.html` construído.
- [x] Assets são servidos somente dentro do build, com MIME correto.
- [x] Falta de build e caminhos inválidos não viram sucesso nem vazam arquivo.
- [x] APIs, health e contratos de sessão permanecem inalterados.

## Evidência de implementação

`tests/unit/test_frontend_delivery.py` cobre build sintético presente/ausente, HTML, MIME derivado,
assets referenciados, 404 para caminhos ausentes/malformados/traversal, prefixo repetido,
symlink escapando do build, compatibilidade de health/session e leituras concorrentes sem escrita.
`scripts/smoke.sh` compara o `index.html` e cada asset referenciado com os arquivos presentes em
`/app/frontend/dist` no container de runtime e verifica caminhos inválidos. A imagem existente
continua copiando o resultado do estágio Vite para esse diretório fixo.
