# Navegação SPA URL-endereçável

## Metadados

- **Fase/status/versão:** P10-09 — pronta para passagem de issues; não implementada — v1.0.
- **Prioridade:** próxima fatia executável.
- **Dependências:** P10-01, P10-02 (shell histórico), P10-03..08; preserva os owners P1, P2, P3, P7, P8 e P9.
- **Fontes:** PRD NFR-013 e AC-027; Arquitetura §§10.4 e 11, ADR-014; Plano P10-09; `p10-application-shell.md` e `p0-frontend-build-delivery.md`.

## Objetivo, escopo e não escopo

Substituir a navegação autenticada por hash por navegação SPA com React Router, mantendo um `AppShell` persistente e exatamente uma área de negócio primária por rota. A mudança deve preservar intenção de URL, filtros, drill-downs, estado operacional e autorização existente.

Não muda endpoints, payloads, CSRF, sessão, RBAC do servidor, regras fiscais, dados, migrações, filtros de negócio, cálculo de dashboard, design system, mobile, estado global ou biblioteca UI. Não cria rotas de detalhe além das queries já publicadas nem um fallback genérico para caminhos desconhecidos.

## Baseline e delta aprovado

`App.tsx` monta todas as features e usa `#...`, `hashchange` e `pushState`; as features leem a query global condicionada ao hash. `backend/nfx/urls.py` entrega o build apenas em `/`; `frontend/package.json` ainda não declara React Router. Essa baseline satisfazia P10-02 histórico, mas não NFR-013/AC-027 nem a arquitetura atual.

P10-09 substitui somente o contrato de navegação de P10-02 e o limite de entrega de build de P0. O shell, a semântica, os estados e a evidência dos slices P10-01..08 permanecem válidos até onde não dependem de hash ou de todas as páginas montadas.

## Contrato de rotas e compatibilidade

Após autenticação, `/` deve normalizar para `/dashboard`. A sidebar deve usar destinos abaixo; a rota ativa deve ter o mesmo nome, papel e semântica de foco atuais.

| Destino canônico | Papel visível | Legado aceito |
|---|---|---|
| `/dashboard` | todos autenticados | `#dashboard` |
| `/documentos` | todos autenticados | `#documentos` |
| `/exportacoes` | todos autenticados | `#exportacoes` |
| `/empresas` | Administrador, Operador | `#empresas` |
| `/certificados` | Administrador, Operador | `#certificados` |
| `/coletas` | todos autenticados | `#coletas` |
| `/usuarios` | Administrador | `#usuarios` |
| `/auditoria` | Administrador | `#auditoria` |
| `/retencao` | Administrador | `#retencao` |

Uma URL legada conhecida no formato `/?<query>#<destino>` deve ser convertida no cliente, antes de apresentar a área, para `<rota>?<query>` por substituição de histórico; a query deve ser preservada byte a byte e o fragmento removido. Hash ausente em `/` normaliza para `/dashboard` preservando query somente quando ela pertencer ao destino migrado por um hash conhecido; a implementação não deve adivinhar o owner de uma query solta. Fragmento desconhecido não deve ser tratado como rota válida.

As queries continuam propriedade de cada feature e conservam seus validadores/limites atuais. No mínimo, a migração deve preservar: `dashboard` (`from`, `to`, `filter`); documentos (`search`, `family`, `direction`, `nfse_category`, `from`, `to`, `cursor`); empresas (`lifecycle`, `status`, `search`, `limit`, `cursor`); certificados (`filter`, `cursor`); coletas (`from`, `to`, `state`); usuários (`active`, `role`, `cursor`, `limit`); auditoria (`actor_id`, `action`, `entity_type`, `result`, `cursor`, `limit`); retenção (`state`, `family`, `cursor`, `as_of`). Exportações preservam as queries já aceitas pelo owner, sem criar parâmetros novos.

Todo link de drill-down fornecido pelo dashboard deve ser convertido para o destino canônico equivalente sem alterar filtros retornados pelo owner. O cliente não deve derivar contagens, elegibilidade, filtros de negócio ou autorização para construir esse link.

## Requisitos funcionais e técnicos

- A navegação autenticada deve usar React Router declarado como dependência de produção compatível com React 18; não pode manter roteador próprio por hash, listeners `hashchange` ou chamadas diretas de `window.history` para trocar página.
- `App.tsx` deve continuar como raiz de composição e compor `AuthShell`, `AppShell` e a saída de rota. A saída deve montar somente a página primária correspondente; features inativas ou sem papel não podem permanecer montadas para buscar dados ou produzir efeitos.
- Cada feature deve obter localização/navegação por mecanismos do roteador, mantendo seus contratos de URL, serialização, cancelamento/sequenciamento e estados loading, vazio, indisponível, degradado, stale, parcial, bloqueado e erro.
- A rota direta de usuário sem o papel necessário deve continuar sem conceder dados ou ações. A ocultação/redirect do cliente é somente UX; as chamadas, downloads e mutações devem manter a autorização do servidor. A UI não deve mostrar sucesso, zero ou conteúdo administrativo como substituto de acesso negado.
- Refresh, deep link, navegação por sidebar e Back/Forward devem restaurar a mesma rota e query. O shell, landmarks, skip link, header, logout, foco e teclado devem persistir entre páginas.
- O servidor deve entregar `index.html` somente para `/` e para as nove rotas canônicas listadas, com ou sem query. Build ausente ou ilegível deve continuar retornando `503` em cada rota SPA conhecida.
- `/api/...`, `/health/...`, sessão/autenticação, `assets/...`, caminhos inválidos e qualquer rota não listada devem manter o comportamento atual e nunca receber o documento SPA. Assets devem manter containment, rejeição de traversal/symlink escape e MIME corretos.
- A migração deve ser idempotente: reabrir ou recarregar uma URL canônica não pode acrescentar entradas de histórico, duplicar carregamentos, mutações ou requests de coleta. A conversão de hash deve usar substituição, não criar uma volta extra para o URL legado.

## Segurança, observabilidade e compatibilidade

Nenhuma rota de UI é uma fronteira de autorização. URLs, mensagens e telemetria não podem expor segredo, certificado, XML, payload fiscal, erro interno ou URL de download além do já autorizado. A entrega de fallback deve continuar fail-closed quando o build não existir e não ampliar a superfície de arquivos servidos.

O build deve manter a matriz sintética e sem rede externa. Falhas de rota devem ser distinguíveis nos testes entre rota SPA conhecida sem build (`503`), asset inválido (`404`), API/health preservados e caminho desconhecido (`404`). Não há mudança de esquema, migração ou compatibilidade de API.

## Testes e critérios de aceite

- Testes de contrato devem provar o mapa completo de rotas, uma área primária montada por vez, sidebar/`aria-current`, RBAC visual e preservação de shell, foco e skip link.
- Para cada papel permitido e negado, testar navegação direta, refresh, deep link, Back/Forward e URL legada conhecida; confirmar que a conversão preserva query, remove hash e não acrescenta histórico.
- Cobrir os drill-downs existentes de documentos, empresas, certificados, coletas e jobs: destino canônico, filtros exatamente preservados e dados ainda carregados apenas pelo owner autorizado.
- Cobrir query/cursor/filtros de cada feature listada, inclusive valores inválidos que continuam normalizados pelo validador dono; nenhuma query deve vazar entre rotas.
- Testes HTTP devem cobrir `/` e cada rota SPA conhecida com build presente e ausente, MIME/containment dos assets, e a não captura de `/api`, health, sessão, assets, traversal e rota desconhecida.
- `npm --prefix frontend run lint`, `npm --prefix frontend run build`, testes unitários/integração afetados e `make test-browser` devem passar. A evidência de browser deve usar fixtures sintéticas, nenhuma chamada de rede/fiscal, e Chrome, Firefox e Edge em 1024, 1280 e 1440 px.

- [ ] React Router substitui a navegação hash e cada destino canônico renderiza uma única página primária dentro do shell persistente.
- [ ] Refresh, deep link, Back/Forward, queries e drill-downs preservam intenção e não duplicam efeitos.
- [ ] Hashes publicados conhecidos são migrados de forma idempotente; fragmentos e caminhos desconhecidos não ganham fallback permissivo.
- [ ] RBAC, endpoints, assets, falhas `503` de build e respostas seguras existentes permanecem preservados.
- [ ] A matriz de testes indicada fornece evidência reproduzível nos três browsers exigidos.

## Decisões em aberto

Nenhuma decisão material bloqueia a passagem de issues: React Router, as nove rotas e o fallback limitado já são aprovados pela arquitetura. A issue deve registrar somente a versão compatível da dependência e a evidência de migração de cada owner de query, sem ampliar o contrato.
