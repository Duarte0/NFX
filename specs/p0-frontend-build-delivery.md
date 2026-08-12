# Entrega da aplicação React na rota raiz

## Metadados

- **Fase/status/versão:** follow-up de fundação — implementado e verificado no issue 0032 — v1.2.
- **Dependências:** `p0-project-foundation.md`, `p1-authentication-sessions-and-rbac.md`.
- **Fontes:** Arquitetura §§9, 10.4 e 11; Plano “Rota raiz e build React”.

## Contexto e objetivo

A baseline histórica devolvia o placeholder `NFX INOV foundation` em `/`, embora a imagem Docker já construísse/copiasse `frontend/dist`. O issue 0032 consolidou a fronteira em `backend/nfx/urls.py`: `/` lê somente o `index.html` do diretório fixo, a ausência ou leitura inválida do build retorna `503`, e `assets/<path>` rejeita caminhos não canônicos e arquivos fora do diretório de assets resolvido. A implementação permanece sem fallback SPA ou servidor de arquivos genérico.

## Contrato, segurança e falhas

`/` deve responder HTML do build; assets publicados pelo `index.html` devem responder com seu MIME correto. Build ausente deve responder falha explícita sem cair para placeholder ou página de sucesso. Caminhos de asset devem ser confinados ao diretório de distribuição, rejeitando traversal, arquivo inexistente e qualquer arquivo fora dele com 404. Isso não cria SPA fallback, novas rotas, mudança de API, cache policy, upload de assets ou acesso a conteúdo sensível.

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
