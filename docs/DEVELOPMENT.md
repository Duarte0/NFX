# Fundação P0

## Limites da arquitetura frontend

O bootstrap em `frontend/src/main.tsx` somente valida o elemento `#root` e monta `App.tsx`.
`App.tsx` é o composition root: mantém a composição do shell autenticado, a navegação por
âncoras e a visibilidade por papel, enquanto cada funcionalidade mantém seus próprios tipos,
contratos HTTP, estado, handlers e apresentação em `frontend/src/features/`:

- `auth` — login, restauração, encerramento e shell de sessão;
- `users`, `companies`, `certificates`, `collections`, `documents`, `exports`, `dashboard` e `audit` — um limite por
  domínio, sem estado ou regra de negócio compartilhado entre funcionalidades;
- `shared/http.ts` — credenciais same-origin, CSRF, serialização e erros seguros; e
  `shared/ui/` — primitives sem regras de domínio.

A direção de dependências é `App → features → shared`; funcionalidades não importam umas às
outras, exceto a composição explícita de certificados dentro da área de empresas. O frontend
continua sem router, biblioteca global de estado, framework de componentes ou camada de retry.
Autorização permanece server-side, e os endpoints, payloads, mensagens, IDs de seção e estados
visíveis das specs P1–P4 continuam sendo contratos de compatibilidade.

## Workflow operacional de frontend

Em criação, redesign, modernização ou alteração visual significativa, identificar antes do trabalho as skills/plugins disponíveis e aplicáveis por capacidade, ler suas instruções e executar o workflow selecionado. Se uma skill exigir aprovação de conceito/design antes da implementação, a aprovação é obrigatória e a codificação não começa antes dela. A seleção de skills complementa os contratos de PRD, arquitetura, specs e issues; não autoriza alterar endpoints, contratos HTTP, RBAC, regras de negócio, estados funcionais, URLs/âncoras ou os limites desta seção.

Conceber e implementar pela fundação visual compartilhada, mantendo `App.tsx` como composition root, `App → features → shared` e a separação entre `shared/http.ts`, `shared/ui/` e os owners de domínio. Ao concluir, executar a validação aplicável: `npm --prefix frontend run test:ui-contract`, lint e build; para alterações que afetem interação, layout ou comportamento visual em browser, executar também `make test-browser` (ou o comando equivalente documentado) e inspecionar/refinar as divergências na matriz Chrome, Firefox e Edge em 1024, 1280 e 1440 px. Essa validação visual não substitui os testes funcionais, de contrato ou de RBAC dos owners.

## Fundação visual P10-01

`frontend/src/shared/ui/tokens.css` é a fonte única dos tokens de marca, neutros, estados,
tipografia, espaçamento, superfícies, bordas, raios, sombra e foco. A direção aprovada usa vinho
como primária, cinza como estrutura/neutro e branco como superfície; `success`, `warning`,
`danger` e `info` têm superfícies claras próprias e não substituem texto ou semântica.

`frontend/src/shared/ui/primitives.ts` contém os primitives sem regras de domínio: `Button`
(primário, secundário, perigo e bloqueado), `Field` (label, ajuda e erro), `Panel`, `DataTable` e
`Badge`. `Feedback` acrescenta os estados loading, vazio válido, erro, indisponível, degradado,
bloqueado, sucesso e ação crítica, com HTML/ARIA nativos, live regions, foco visível e fallback
para mensagem segura. Um botão bloqueado é nativamente `disabled`; ocultação visual nunca é
autorização.

O dashboard, o drill-down de jobs, o shell autenticado e o login exercitam a fundação sem mudar
rotas, âncoras, chamadas HTTP, papéis, dados fiscais ou estado local das features. A verificação
determinística é `npm --prefix frontend run test:ui-contract`; ela valida os oito estados, pares
de contraste documentados, semântica, foco, labels, bloqueio e ausência de efeitos colaterais sem
introduzir dependências ou infraestrutura de browser.

## Shell de aplicação P10-02

`frontend/src/App.tsx` continua sendo o composition root e agora publica o shell autenticado em
um grid desktop/notebook com header institucional, sidebar nomeada e landmark `main`. O modelo
tipado `navigationModel` é a única fonte da navegação: filtra Administrador, Operador e
Visualizador conforme a matriz existente, conserva os hashes e dispara somente os `loadSignal`
que já pertenciam aos links. O item correspondente ao hash inicial e a eventos `hashchange`
recebe `aria-current="page"` e a classe visual ativa; parâmetros de consulta e URLs de
drill-down não são reescritos.

O skip link aponta para `#main-content`, que recebe foco por ser programaticamente focalizável.
`#certificados` é um único destino dentro de `CompaniesSection`, sob a mesma barreira
`canManage`; não há rota, endpoint ou feature paralela. O header mantém somente marca,
identidade/papel, logout e contexto de Brasília/R$, enquanto notificações seguras permanecem no
landmark principal. A composição usa os tokens P10-01, mantém labels visíveis e reserva a grade
de duas colunas para larguras desktop/notebook a partir de 1024 px.

O contrato UI renderiza contextos sintéticos dos três papéis e verifica landmarks, skip link,
foco, estado ativo, hashes, destino único de certificado, visibilidade negativa e ausência de
efeitos de rede/persistência. A matriz reproduzível de interação usa
`docker compose -f docker-compose.test.yml run --rm --no-deps browser-tests` (ou `make test-browser`)
para executar a fixture sintética em Chrome, Firefox e Edge nas larguras 1024, 1280 e 1440 px.
O target instala os browsers em uma imagem efêmera; a fixture rejeita chamadas de rede e usa
somente identidades sintéticas.

## Dashboard P10-03

`frontend/src/features/dashboard/DashboardSection.tsx` mantém o payload de `GET /api/dashboard`
como única fonte de períodos, valores, estados, frescura, capacidades e URLs de drill-down. A
apresentação agrupa empresas/documentos, coletas/processamento e certificados/capacidades; a
saúde operacional e o backup só aparecem quando já foram fornecidos pelo payload autorizado de
Administrador. O navegador não recalcula métricas, filtros, períodos ou autorização.

Durante uma consulta, a última leitura segura fica visível com indicação de desatualização. Uma
falha mantém esse contexto e oferece nova tentativa sem apagar os cards não relacionados. Guards
de sequência impedem respostas antigas de substituir seleções novas; o drill-down de jobs aplica
a mesma proteção e traduz erros allowlisted para mensagens de interface. O HTML usa os primitives
P10-01, labels pt-BR, foco nativo e URLs produzidas pelo servidor.

O contrato determinístico é `npm --prefix frontend run test:ui-contract`. A matriz sintética de
browser usa `docker compose -f docker-compose.test.yml run --rm --no-deps browser-tests` e cobre
90 testes em Chrome, Firefox e Edge nas larguras 1024, 1280 e 1440 px, incluindo grupos, estados,
período comparativo, deep links, teclado, overflow e redaction Admin-only.

## Documentos P10-04

`frontend/src/features/documents/DocumentsSection.tsx` mantém os filtros P7 e os parâmetros de
deep link como estado de localização, exibe os totais, limite, truncamento, cursor opaco e
fronteira `[from,to)` recebidos do servidor e conserva a última leitura segura durante loading ou
erro. Rótulos allowlisted distinguem consulta vazia, cobertura, quarentena, conflito, falha,
bloqueio e os estados de PDF sem renderizar códigos técnicos.

O detalhe mantém a identidade do documento junto às ações XML/original e PDF. Downloads e
regeneração usam somente URLs fornecidos pelo owner; a operação PDF é protegida contra duplo
envio e recarrega o estado durável. O contrato `npm --prefix frontend run test:ui-contract` cobre
cursor, deep links, estados, stale/error/retry, redaction e ações com fixtures sintéticas. A
matriz Docker cobre 135 testes em Chrome, Firefox e Edge nas larguras 1024, 1280 e 1440 px para
Administrador, Operador, Visualizador e sessões anônima/expirada. Não há endpoint, migration,
dependência ou dado fiscal novo.

## Empresas, certificados e coletas P10-05

`frontend/src/features/companies/CompaniesSection.tsx` compõe a apresentação de empresas e seus
detalhes com os owners existentes. Os filtros de ciclo de vida, status, busca, limite e cursor
usam somente os parâmetros allowlisted da URL; o destino `#certificados` continua único e a
visibilidade permanece definida pela composição autorizada em `App.tsx`. Estados de empresa,
enriquecimento público não autoritativo e fluxos NF-e/NFS-e recebem rótulos semânticos, enquanto
confirmação, motivo, versão, autorização e respostas duráveis continuam nos callbacks da feature.

`CertificateInventoryPanel.tsx` e `CertificatePanel.tsx` distinguem certificado atual, ausente,
expirado/próximo do vencimento, validade fresca/desatualizada/desconhecida e resultado vazio válido.
O inventário conserva total, limite, truncamento e cursor opaco para a próxima página sem exibir o
cursor; nenhum material, senha, chave, fingerprint ou payload é renderizado.

`CollectionsSection.tsx` separa cobertura ADN ausente, nenhuma cobertura, desconhecida e erro de
indisponibilidade dos estados de coleta e execução (vazia, em execução, parcial, falha, bloqueio,
cooldown e retry). Filtros de execução preservam `from`, `to` e `state`; a leitura segura fica
visível durante refresh/erro com stale explícito, as leituras de coleta e execução são independentes
e guards de sequência/listeners/mutação impedem respostas fora de ordem e cliques repetidos.

O contrato determinístico é `npm --prefix frontend run test:ui-contract`. A fixture sintética
`frontend/browser-tests/companies.*` cobre os três papéis, sessões anônima/expirada, estados
negativos, foco, teclado, overflow, cursor, stale/error/retry e redaction. A imagem efêmera do
target `make test-browser`, reconstruída para incluir o fixture, passou 180 testes em Chrome,
Firefox e Edge nas larguras 1024, 1280 e 1440 px. Não houve endpoint, migration, dependência ou
dado fiscal novo.

## Administração, auditoria e retenção P10-07

`UsersSection`, `AuditSection` e `RetentionSection` compõem a superfície administrativa P10-07
usando somente os contratos existentes de usuários, auditoria, retenção e exclusão controlada.
Os anchors e a navegação direta continuam sob o shell existente; a autorização continua sendo
decidida pelo servidor e a UI esconde toda a seção para sessões anônimas, expiradas ou não Admin.

Filtros têm listas permitidas, paginação mantém cursor opaco fora da apresentação, e respostas
antigas ficam marcadas como desatualizadas. Contexto de auditoria e prévias de retenção são
redigidos por allowlist. Ações críticas exigem alvo, consequência, motivo quando aplicável,
confirmação explícita e cancelamento; nenhuma operação de exclusão é concluída localmente, e o
estado autoritativo é recarregado após mutações. Estados `pending`, `executing`,
`recovery_required`, `failed` e `completed` permanecem visíveis conforme o servidor os devolve.

O contrato determinístico continua sendo `npm --prefix frontend run test:ui-contract`; a fixture
`frontend/browser-tests/admin.*` cobre RBAC, estados de sessão, confirmação/cancelamento, foco,
prévia desatualizada, recuperação e redaction. O target `make test-browser` passou 306 testes na
matriz Chrome, Firefox e Edge em 1024, 1280 e 1440 px. Não houve endpoint, migration, dependência
ou dado fiscal novo.

## Validação transversal P10-08

O gate transversal usa `frontend/browser-tests/accessibility.spec.ts` para percorrer as fixtures de
dashboard, documentos, empresas/certificados/coletas, exportações, administração e o shell
composto. Ele verifica, com dados sintéticos, landmarks e headings nomeados, associações
label/control e `aria-describedby`, live regions, redaction, papéis Administrador/Operador/Visualizador,
sessões anônima/expirada, skip link, clipping, scroll horizontal da página e overflow somente em
`.ui-table-wrap`, preservando caption e cabeçalhos.

Os diálogos de usuário e exclusão controlada têm `aria-labelledby`, recebem foco ao abrir, cancelam
por Escape somente quando o cancelamento é seguro e devolvem foco ao disparador. O cancelamento de
exclusão é desabilitado enquanto há solicitação em andamento. A mudança permanece na fronteira de
apresentação: não altera endpoints, payloads, RBAC server-side, âncoras, dados owner-provided,
migrations, backend ou suporte mobile.

| Evidência | Resultado |
|---|---|
| `npm --prefix frontend run test:ui-contract` | Passou: estados, tokens/contraste, labels, dialogs, redaction e overflow de tabela. |
| `npm --prefix frontend run lint` / `npm --prefix frontend run build` | Ambos passaram. |
| `make test-browser` | 342 testes passaram em Chrome, Firefox e Edge nas larguras 1024, 1280 e 1440 px. |

As descrições visuais são reproduzíveis pelas rotas das fixtures e pelas métricas de bounding box e
`scrollWidth` das asserções; não há capturas com dados para versionar. O contrato P10-01 fornece os
dez pares de contraste e o foco tokenizado, enquanto a matriz confirma a visibilidade e o alcance
por teclado. A skill instalada `graphify` foi avaliada e usada para navegar as relações entre spec,
issue, código e testes; não havia skill/plugin frontend ou browser adicional instalado no catálogo
ativo e nenhum gate de aprovação de conceito/design foi exigido.

## Decisões Proposed adotadas

- A árvore física é `backend/`, `frontend/`, `tests/`, `scripts/` e `docs/`. Os pacotes
  `nfx.identity`, `companies`, `certificates`, `collection`, `documents`, `artifacts`,
  `exports`, `retention`, `audit`, `operations`, `adapters` e `infrastructure` estabelecem
  limites lógicos. Um módulo só deve usar a interface pública de outro módulo.
- Python usa `pip` com versões exatas em `requirements*.txt`; o frontend usa `npm` e
  `frontend/package-lock.json`. Python 3.12 e Node 20/22 são validados por `make install`.
- Os comandos são `make web`, `make worker` e `make scheduler`. Eles executam a mesma árvore
  `backend/nfx`; o worker processa somente handlers registrados na fronteira de jobs e o
  scheduler recupera leases vencidos. Ambos não têm acesso a transportes, endpoints,
  certificados, CNPJs, XMLs ou trabalho fiscal.
- Cada integração/smoke cria um projeto Compose e bucket `nfx-p0-test-<run-id>` exclusivos,
  em uma rede Compose privada. O teardown usa somente `docker compose -p <id> down --volumes`;
  portanto não toca os volumes `postgres_data`/`minio_data` de desenvolvimento.

## Contratos dos comandos

Run `make install` once in a clean Python 3.12 / Node 20 or 22 checkout. It installs the pinned
Python requirements and the frontend lockfile dependencies. `make build` is then self-contained:
it runs Django's import/configuration check with a local `test` profile and clearly synthetic,
non-production values, followed by the Vite artifact build. The values are scoped to that Make
recipe, are not deployment credentials, and the check does not contact PostgreSQL, MinIO, DNS,
HTTP/SOAP, or a fiscal transport. No service must be running and no manual secret export is
needed for this command.

`make build` is only a build-time validation profile. Web, worker, scheduler, Compose, and
deployment commands still require externally provisioned secrets and their complete runtime
configuration; `.env.example` remains a list of deliberately invalid placeholders. The
configuration loader continues to fail closed for missing, placeholder, malformed, conflicting,
or production-capable values. `make build` performs the Django check before the frontend build
and stops on either failure; it does not start services or apply migrations.

`make lint` checks Ruff, mypy, TypeScript and ESLint. `make test-unit` uses no services.

`make test-integration` starts isolated PostgreSQL 16 and MinIO, waits for both, runs the
integration suite and always removes its own containers, network and volumes. `make smoke` does
the same before starting web, worker and scheduler, verifies liveness/readiness and that both
background processes start their durable loops. Set `TEST_RUN_ID` to run two suites in parallel
with predictable distinct project/bucket names.

## Entrega do build React no runtime

`npm --prefix frontend run build` produz `frontend/dist`; a imagem `app` copia esse diretório
para `/app/frontend/dist`. A rota `GET /` lê somente o `index.html` desse diretório fixo e
retorna `503` quando o build não está presente. URLs publicadas sob `/assets/` são lidas do
subdiretório de assets do mesmo build, com MIME derivado do arquivo; caminhos ausentes,
malformados, traversal ou symlinks que escapem do build retornam `404`. Não há fallback SPA nem
servidor de arquivos genérico. O `make smoke` compara o HTML e cada asset referenciado com os
artefatos dentro do container e exercita os caminhos inválidos.

### Rebuild do frontend no Compose de desenvolvimento

Quando o código em `frontend/src/` muda, a aplicação web precisa ser reconstruída para que a
imagem copie o novo `frontend/dist` para `/app/frontend/dist`. O arquivo
`docker-compose.app.yml` é um override e não declara sozinho a rede `nfx_network`; por isso ele
deve ser usado junto com o Compose base:

```sh
docker compose -f docker-compose.yml -f docker-compose.app.yml build --no-cache web
docker compose -f docker-compose.yml -f docker-compose.app.yml up -d web
docker compose -f docker-compose.yml -f docker-compose.app.yml ps
```

Depois do reinício, faça hard refresh no navegador (`Ctrl+Shift+R`) ou abra uma janela anônima.
Não execute `docker compose -f docker-compose.app.yml ...` sozinho, pois o override referencia
`nfx_network` e dependências declaradas no arquivo base.

## Exportação ZIP P8-01

`nfx.exports` owns the request, frozen P7 filter snapshot, document/artifact items, composition
job and 24-hour temporary lifecycle. It uses `nfx.documents.status.scoped_documents` for the
selection and `ArtifactStorageService.read_verified` for every source read. The only output
artifact class it creates is `export_zip_temp`; cleanup must never target `fiscal_original`, XML,
event evidence or any collection artifact.

The local bounded policy is 100 selected items, 50 MiB per entry and 100 MiB per ZIP. `POST
/api/exports` requires an idempotency key and returns a durable queued record; `GET /api/exports`
and `GET /api/exports/<id>` expose only safe progress metadata. `GET /api/exports/<id>/download`
rechecks session, requester/Admin authorization, `available` state and the 24-hour deadline on
each request. Missing or divergent inputs produce explicit item outcomes and a partial/failed
export, never a falsely complete archive.

The P10-06 browser slice in `frontend/src/features/exports/ExportsSection.tsx` consumes this
owner-provided metadata without changing the `/api/exports` contract. Its synthetic UI contract
and browser fixture cover every durable state, returned-only progress/counts/bytes, stale refresh
retention, request/detail/download guards, safe redaction, role/session negatives, keyboard focus,
and the Chrome/Firefox/Edge desktop matrix at 1024/1280/1440 px. Browser validation uses only
synthetic responses and never downloads or embeds ZIP/XML/PDF bytes.

`make check-services` returns zero only when PostgreSQL and MinIO are ready. On failure it returns
non-zero and says only which dependency is unavailable; it never prints connection strings or
credentials. `/health/live` is independent of services and `/health/ready` returns 503 until both
dependencies are reachable.

## Persistência e migrações (P1-01)

PostgreSQL é a autoridade relacional. O único schema desta fase é
`nfx_schema_contract`, metadado operacional sem estado de domínio. Sua chave singleton e os
constraints impedem mais de um contrato; o índice de `updated_at` sustenta a consulta operacional
de verificação mais recente. Entidades fiscais, usuários, jobs, empresas e certificados continuam
fora desta migration e serão adicionados exclusivamente por suas specs proprietárias.

Para uma instalação vazia, inicie os serviços de desenvolvimento e execute
`python backend/manage.py nfx_migrate`. O comando obtém um advisory lock PostgreSQL, aplica o
grafo Django e informa apenas nomes de migrations e resultado. `python backend/manage.py
schema_status` mostra a versão NFX esperada e falha quando ela está ausente ou quando o banco está
adiantado para uma versão incompatível. `python backend/manage.py showmigrations nfx` mostra o
grafo e pendências. A readiness também falha com resposta genérica quando o schema não for
compatível; não inclui URL ou senha.

Cada migration futura deve declarar dependências, constraints e índices que atendam uma consulta
identificada, além de testes de instalação limpa, upgrade, falha e recovery. Mudanças aditivas são
preferidas até P9. Mudanças irreversíveis exigem backup/restore aplicável e uma migration corretiva
ou backfill reiniciável; rollback nunca deve apagar dados para “consertar” schema.

## Identidade e persistência fiscal (P4-01)

`nfx.documents.services.persist_document` recebe somente contexto seguro, identidade fiscal
normalizável, timestamps conscientes de fuso, uma referência de `Artifact` finalizado e uma
referência de execução limitada. Escolhe a identidade oficial mais forte disponível; sem identidade
suficiente retorna `quarantine` sem fabricar uma chave. A competência é derivada da emissão em
fuso local, nunca da chegada ou da execução.

O resultado é `persisted`, `replay`, `quarantine` ou `conflict`. O mesmo contexto/identidade com o
mesmo hash retorna replay sem nova evidência; um hash diferente preserva a segunda referência e
marca o conflito. Eventos e substituições exigem um documento pai da mesma empresa e família, e
não alteram a competência do pai. O módulo grava apenas metadados e IDs de artefato: bytes, XML,
PDF e conteúdo de objetos continuam sob responsabilidade de `nfx.artifacts`.

P4-01 não cria execução, unidade, checkpoint, cursor/NSU, job ou transporte fiscal. Essa sequência
fica para P4-02.

## Consulta mínima de documentos (P4-04)

`GET /api/documents` é a leitura autenticada e limitada do acervo disponível. Aceita `company_id`,
`family`, `flow`, `limit` (1–100) e cursor assinado, além dos filtros P7 bounded de competência,
período de emissão, direção NF-e, categoria NFS-e, tipo de evento e busca global; a ordenação é determinística por ID. A resposta
separa `valid_empty`, `unavailable`, `no_coverage`, `unknown`, `partial`, `retry` e `blocked` e
lista somente metadados, competência, situação, resultado (`persisted`, `quarantine` ou `conflict`)
e a disponibilidade booleana de evidência. Bytes, chaves de objeto e erros externos nunca saem por
essa fronteira. A seção React `#documentos` mantém ramos explícitos para carregamento, vazio válido,
degradação, detalhe e download; ela não cria cursor, checkpoint, retry ou estado durável.

## Drill-down de documentos do dashboard (P8-02)

Os sete cards de documentos do `GET /api/dashboard` usam o mapa allowlisted canônico de filtros
P7 (`family`, `direction` e `nfse_category`) e carregam o período civil exibido como `from`/`to`.
O dashboard e o arquivo usam a mesma seleção de `Document`; a direção NF-e é aplicada ao campo
`role` e as categorias NFS-e persistidas são exatamente `tomada` e `prestada`.

O `GET /api/documents` aceita esse período adicional e traduz o intervalo civil semiaberto
`[from,to)` para `emitted_from`/`emitted_to` inclusivos no owner P7. A resposta aditiva `total`
conta somente documentos persistidos da mesma seleção, enquanto linhas de quarentena continuam
separadas no resultado existente. A página permanece bounded e determinística, sem payloads,
chaves de objeto, correlação sem limite ou erros brutos; falhas de fonte retornam `503` seguro.
Consultas autenticadas são somente leitura, e a auditoria de consulta continua sendo a única
auditoria P7 aplicável.

## Drill-down de empresas do dashboard (P8-02)

Os cards `companies.active` e `companies.inactive` do `GET /api/dashboard` usam, para
Administradores e Operadores, `?lifecycle=active#empresas` e `?lifecycle=inactive#empresas`.
Visualizadores continuam sem link para a área protegida de administração de empresas. A tela
`#empresas` hidrata o filtro da URL e não recalcula nem autoriza a consulta no navegador.

`GET /api/companies` mantém os filtros legados `status`, `search`, `limit` e `cursor` e adiciona
o filtro allowlisted `lifecycle=active|inactive`. `active` seleciona somente `ativa`; `inactive`
seleciona `cadastrada` e `desativada`. Filtros de lifecycle repetidos, conflitantes, desconhecidos
ou inválidos falham com `400`, sem fallback para a lista completa. A resposta aditiva informa o
filtro aplicado, o total server-side da seleção inteira, limite, truncamento e cursor estável por
UUID, com os metadados de empresa já redigidos; a página e o total usam a mesma seleção canônica.

A autorização continua em `Action.ADMINISTER_COMPANIES` no servidor. Falha de banco/fonte retorna
`503` seguro, nunca zero; leituras repetidas não criam auditoria, mutação, job ou transição.

## Drill-down de certificados do dashboard (P8-02)

Os cards `certificates.current`, `certificates.expired` e `certificates.expiring` do
`GET /api/dashboard` usam, para Administradores e Operadores, `?filter=current|expired|expiring#empresas`.
Visualizadores não recebem esses cards nem o inventário protegido por
`Action.ADMINISTER_CERTIFICATES`.

`GET /api/certificates/inventory` exige exatamente um filtro allowlisted: `current` seleciona
todos os registros `CertificateState.CURRENT`, `expired` seleciona os correntes com
`not_after <= evaluated_at`, e `expiring` seleciona os correntes com
`evaluated_at < not_after <= evaluated_at + 30 dias`. O total e a página limitada usam a mesma
queryset canônica, ordenada por empresa/certificado UUID, com cursor composto estável. O servidor
retorna o filtro normalizado, avaliação UTC, frescura e somente identidade segura da empresa,
estado/status e validade; PFX, senha, chaves, referências de objeto, fingerprint e exceções não
atravessam o contrato.

Filtros repetidos, desconhecidos, ausentes ou cursores/limites inválidos retornam `400`; falha de
fonte retorna `503` seguro e não vira zero. A seção `#empresas` hidrata o filtro da URL, mostra
total reconciliado, avaliação, vazio válido, carregamento, indisponibilidade, degradação e erro
de filtro sem autorizar ou recalcular no browser. Leituras repetidas não criam auditoria, job,
mutação ou transição de certificado/empresa.

## Drill-down de jobs do dashboard (P8-02)

Os cards `jobs.pending`, `jobs.failed` e `jobs.blocked` do `GET /api/dashboard` carregam o
período civil exibido e `filter=pending|failed|blocked` para `GET /api/jobs/observability`. O
owner `nfx.jobs` compartilha com a agregação os predicados `queued|running`, outcomes
`temporary|permanent|partial` e estado `blocked`, além das fronteiras Brasília `[from,to)`.

O endpoint exige exatamente `from`, `to` e um filtro allowlisted, rejeita repetições, parâmetros
desconhecidos e períodos inválidos, informa total server-side e retorna no máximo 50 linhas
ordenadas por timestamp/UUID. Os resumos são limitados a ID, tipo, estado/outcome, timestamps,
tentativas e códigos de erro seguros; payload, alvo, resultado, lease, política, segredos,
conteúdo fiscal e exceções brutas ficam fora. A UI `#dashboard` distingue carregamento, sucesso,
vazio, filtro inválido, indisponibilidade e degradação. A leitura é autorizada server-side e não
cria jobs, leases, auditoria, cache ou transições.

## Consulta e download individual (P7-01/P7-02)

`GET /api/documents/<id>` fornece detalhe seguro, incluindo eventos/substituições e disponibilidade
de evidência. `GET /api/documents/<id>/download` e `GET /api/artifacts/<id>/download` revalidam
relação, estado finalizado, digest e tamanho antes de servir o conteúdo. Chaves MinIO, payloads e
erros do provedor não atravessam a fronteira. Uma falha de leitura não muta o artefato; a
reconciliação continua responsável por classificar objetos ausentes ou divergentes.

Os três papéis autenticados podem consultar e baixar individualmente; cada leitura é autorizada
server-side e auditada com contexto bounded. O XML é a evidência primária; o PDF derivado mantém
estado e metadados versionados sem substituir o original.

## Renderização PDF derivada (P7-03)

`nfx.documents.rendering` é o owner da integração com `BrazilFiscalReport[danfse]==1.0.1`.
`renderer_metadata()` valida a versão instalada; `render_pdf_bytes()` chama `Danfe` ou `Danfse`
diretamente e recebe bytes, sem CLI, subprocesso, shell ou rede. O worker registrado como
`document.render_pdf` lê a evidência XML verificada, grava um artefato `document_derived_pdf` e
só finaliza depois de confirmar hash, tamanho, MIME, bytes PDF e identidade do documento.

O contrato `DocumentRender` separa fonte e derivado e usa a identidade documento + tipo +
representação + renderer + versão para reuso concorrente e histórico de versões. As rotas
`POST /api/documents/<id>/pdf/render` e `GET /api/documents/<id>/pdf` revalidam sessão/RBAC e
integridade; a UI expõe estados de indisponível, pendente, disponível, falho e não suportado.
Falhas preservam o XML e são representadas por erros bounded. Audite e teste somente metadados
seguros; nunca coloque XML, PDF, chave de objeto ou exceção externa em payload, log ou métrica.

## Pipeline fiscal durável (P4-02)

`nfx.collection.ingestion.ingest_page` é a fronteira comum para páginas sintéticas. Ela registra
a página e as unidades limitadas, finaliza o original através de `ArtifactStorageService`, e
então delega a identidade para `nfx.documents.services.persist_document`. Somente uma página
completa ou vazia avança o cursor ou NSU do seu escopo. Use `reconcile_ingestion` para unidades
pendentes ou falhas após interrupção; o reconciliador não apaga objetos nem infere progresso de
uma página incompleta. Checkpoints NF-e (`nfe`) e ADN (`adn`) são independentes. Transportes
oficiais e payloads fiscais brutos continuam fora do escopo.

## Distribuição semântica NFS-e/ADN (P6)

`nfx.adapters.adn` valida referências bounded de empresa, ator, fluxo, política e NSU. Cada
ator+fluxo recebe um histórico independente no `AdnDistributionSimulator`; `taken` e `provided`
não compartilham posição. A resposta mantém `available`, `none` e `unknown` distintos de
`empty`, `unavailable`, `partial` e `unknown`/quarentena, e somente unidades `document`,
`event` e `substitution` atravessam a porta. O método `ingest` grava a evidência de cobertura
segura e delega unidade, artefato, identidade, vínculo, checkpoint, retry e reconciliação ao P4,
usando `actor:flow` no escopo do NSU.

O estado `none` aparece como “Sem cobertura automática no ADN”; não é uma consulta vazia e não
afirma ausência fiscal. Páginas parciais, falhas, desconhecidas, eventos sem pai e evidência
insuficiente não avançam o NSU; o reconciliador aplica também a guarda de NSU não monotônico.
Nenhum adapter chama rede ou fonte municipal, e logs/auditoria/metrics carregam somente códigos,
contagens, prefixos limitados e referências seguras.

## Matriz de falhas de ingestão (P4-03)

`classify_page_response` é a classificação única da resposta do simulador. Ela persiste
`outcome` e `recovery` bounded em execução, página e unidade, mantendo separados `valid_empty`,
`no_coverage`, `unavailable`, `temporary_failure`, `cooldown`, `permanent_failure`, `malformed`,
`partial`, `quarantine` e `conflict`. `IngestionPageState` expõe os estados operacionais sem
reutilizar `empty` para uma fonte indisponível ou sem cobertura.

Somente páginas vazias válidas ou com todas as unidades em tratamento terminal avançam cursor/NSU.
Falhas de objeto/persistência ficam em retry, falhas de posição pedem reconciliação, bloqueios não
são ressuscitados por replay implícito e quarentena/conflito preservam as referências de evidência.
O contrato de status P4-04 lê `page.outcome`; não adicione um mapeamento paralelo em adaptadores,
views ou na UI. A migration `0014_ingestion_failure_state_contract` é aditiva e não reescreve o
histórico fiscal.

## Scope boundary

## Políticas e resultados de jobs (P3-02)

`JobPolicy` é versionada por escopo de fonte/fluxo e intervalo de validade. O worker captura a
política efetiva no job, portanto uma atualização futura não reescreve o limite, backoff ou
cooldown de trabalho já iniciado. Handlers registrados retornam `HandlerOutcome.success`,
`.temporary`, `.cooldown`, `.permanent` ou `.partial`; resultados temporários/parciais usam o
backoff progressivo limitado pela política, cooldown oficial usa sua própria data e falhas
permanentes ou retry esgotado ficam `blocked` sem loop automático. Somente códigos e resultados
referenciais seguros são persistidos; certificados, XML, tokens e erros brutos não entram no
payload, resultado ou log.

## Configuração segura e isolamento fiscal (P0-02/P0-04)

Every web, worker and scheduler boot loads `nfx.infrastructure.configuration` before Django opens a
connection. `NFX_PROFILE` is mandatory and is exactly `test`, `development`, `homologation`, or
`runtime`; it is never inferred from a hostname. `NFX_SECRET_KEY` is supplied through the process
environment or `NFX_SECRET_KEY_FILE` (a mounted secret file), never both. `DATABASE_URL` and
`MINIO_ROOT_PASSWORD` and `NFX_CERTIFICATE_MASTER_KEY` are also required external secrets;
the certificate key is base64url-encoded 32-byte key material and may be mounted through
`NFX_CERTIFICATE_MASTER_KEY_FILE`. PostgreSQL URLs, MinIO credentials and
`CHANGE_ME` values fail boot with a safe, non-zero configuration error.

`test` and `development` are restricted to `simulator://empty` and local transport names. The
simulator returns an empty result and is the only fiscal transport in P0. `homologation` and
`runtime` require an explicit simulator selection, destination, and matching `NFX_FISCAL_ALLOWLIST`;
no production-capable transport exists yet. `FiscalDestinationGuard` normalizes and validates the
configured destination and any redirect chain before it invokes a sender, so a forbidden endpoint
causes zero network calls.

`nfx.infrastructure.redaction.redact` is the shared boundary for structured logs and future audit
or HTTP errors. It redacts sensitive fields recursively, credential-bearing URLs and sensitive query
strings, XML/PDF payloads, bytes, and exception arguments. Never put a secret, certificate, CNPJ,
real XML, or endpoint into a fixture.

Copy `.env.example` only as a list of settings: its `CHANGE_ME_*` values are deliberately invalid.
Provide `NFX_SECRET_KEY` and `NFX_CERTIFICATE_MASTER_KEY` through the process environment or their
corresponding mounted `*_FILE` variables, exactly one source per secret. Do not commit or reuse
secrets from prior local copies; if a value was used outside disposable testing, rotate it through
the external secret-management process.

### Provisionamento único do administrador inicial

O comando `python backend/manage.py bootstrap_admin` aceita `NFX_BOOTSTRAP_ADMIN_PASSWORD`
somente no processo explícito de bootstrap. Forneça-o por um secret manager ou pelo ambiente
temporário desse comando; não o adicione ao `.env`, a configurações de web/worker/scheduler ou a
qualquer processo normal. A variável não pertence a `Settings`, não é aceita como arquivo e uma
variável `NFX_*` desconhecida continua fazendo o boot falhar fechado.

Depois de aplicar as migrations, execute o comando uma vez com o valor externo e remova a variável
do ambiente do shell. O comando é idempotente: uma repetição preserva a conta e a senha existentes;
uma base com outro usuário é recusada sem mutação.

## Simuladores fiscais sintéticos (P3-03)

`nfx.adapters.simulation` é a porta interna usada pelos testes antes dos adaptadores oficiais.
`FiscalRequest` aceita somente referências seguras — fonte, família, ator, fluxo, cursor, política,
handle abstrato de certificado e correlação — e `FiscalResponse` devolve unidades sem conteúdo,
hashes sintéticos, cursor/NSU, cobertura, cooldown e códigos seguros. NF-e e ADN são simuladores
independentes, com cenários gerados por seed e sequência reproduzível; `FakeFiscalTransport`
registra a ordem das chamadas e nunca abre DNS, HTTP ou SOAP.

Os cenários distinguem vazio válido, ausência de cobertura, indisponibilidade, parcial, cooldown,
bloqueio, duplicata, conflito, payload malformado, evento sem pai e cursor repetido. O handler
genérico transforma esses valores em `HandlerOutcome` e preserva a fronteira de lease/idempotência
dos jobs. Fixtures não carregam XML, credenciais, tokens, certificados ou endpoints produtivos.

## Distribuição semântica NF-e e follow-ups (P5-01/P5-02)

`nfx.adapters.nfe` é a fronteira worker-facing para distribuição simulada NF-e. A solicitação
usa somente referências bounded, uma página limitada e uma posição `NFePosition` vinculada a
`received` ou `issued`; nenhum fluxo aceita a posição do outro. `NFeDistributionSimulator`
instancia uma história determinística por fluxo, cobre sucesso paginado, vazio válido,
indisponibilidade, timeout/retry, cooldown, bloqueio, malformado e desconhecido, e não abre
socket, DNS ou SOAP. Requisições concorrentes com a mesma correlação e posição são replayadas
sem uma segunda chamada ao transporte sintético.

Para persistir uma página, o worker chama `adapter.ingest(storage, request)`. O adapter converte
o resultado seguro para `FiscalResponse` e delega a `nfx.collection.ingestion.ingest_page`;
essa função continua dona de objeto original, identidade, unidade, checkpoint, cursor,
quarentena, conflito e avanço. Auditoria/métricas recebem apenas fluxo, outcome, motivo,
contagem e prefixo de posição. O P5-02 adiciona `NFeFollowUpAdapter`/`NFeFollowUpSimulator` para
Ciência, XML completo e eventos. `nfe.science` é um job próprio; somente Ciência permitida cria
`nfe.complete_xml`. O original é armazenado e vinculado antes da validação/parsing, e o XML completo
é evidência adicional (`fiscal_xml`) do mesmo `Document`. Eventos passam pelo `ingest_page` de P4 em
um escopo de follow-up sem cursor de distribuição; pai incompatível/ausente fica em quarentena e o
reconciliador pode vinculá-lo depois sem alterar competência, situação ou identidade do pai.
P5-03 adiciona `NFeManifestationRequest`/`Result` e `NFeManifestationSimulator`, persistência
`NFeManifestation` na migration `0017`, e o job `nfe.manifestation`. O serviço autoriza o pedido,
revalida empresa, fluxo, certificado e pai no worker, usa a mesma chave de idempotência no simulador
e no job, e grava somente resultado bounded; pai ausente/incompatível fica `quarantined` sem chamada
de transporte. As fixtures rejeitam destino/credencial sensíveis, limitam MIME/tamanho/declarações XML
e mantêm auditoria/resultados sem payloads. Transporte Portal Nacional/SEFAZ e homologação permanecem fora.

## Controle manual de coleta (P3-05)

`nfx.collection.services.request_collection` é a porta server-authoritative para solicitações
completas, NF-e, NFS-e, retry e o handoff automático criado após um certificado válido. A solicitação
completa cria uma execução independente para cada família; locks e a constraint de execução ativa
impedem duplicidade por empresa/família. O scheduler consome o handoff e o worker executa somente o
handler sintético `collection.synthetic` até que P4 forneça ingestão durável.

As rotas são `GET /api/collections`, `GET /api/collections/executions`,
`GET /api/companies/<id>/collection`, `POST /api/companies/<id>/collection/request` e
`POST /api/companies/<id>/collection/retry/<execution_id>`. Admin/Operador podem mutar; Viewer
recebe apenas estado operacional. Todos os pedidos, conflitos, recusas, retry e resultados usam
auditoria append-only com códigos seguros. `empty` significa somente consulta sintética válida sem
unidades; indisponibilidade, parcial, retry, cooldown e bloqueio permanecem estados distintos.

`GET /api/collections/executions` é uma leitura autenticada para o drill-down P8-02. Exige
`from`, `to` e `state` (`recent`, `running`, `failed`, `blocked` ou `partial`), usa datas civis
de Brasília em `[from,to)`, retorna o total server-side e no máximo 50 resumos ordenados por
`created_at`/UUID. `recent` reutiliza o total de todas as execuções e não é um novo estado do
domínio. A resposta não inclui payload fiscal, XML/PDF, chaves de objeto, certificados,
correlação ou exceções brutas; falha de fonte retorna `503` seguro.

## Retenção e prévia administrativa (P8-03)

`GET /api/retention/documents` calcula decisões sob demanda com a regra versionada `retention-v1`:
NF-e completa 132 meses civis desde a autorização; NFS-e torna-se elegível em 1º de janeiro do
sexto ano após a emissão. `as_of` congela a data de cálculo para testes e inspeções.

`GET /api/retention/documents/<id>` detalha a decisão e
`GET /api/retention/documents/<id>/preview` enumera somente IDs, datas, prefixos de digest,
tamanhos, tipos e disponibilidade de evidências originais/XML e eventos relacionados. A prévia
usa `scope-v1` e hash estável; passar um hash antigo retorna `409` quando o escopo mudou. Bytes,
chaves de objeto, credenciais e erros de storage nunca atravessam a fronteira. Todos os três
endpoints são Administrator-only, auditados com contexto redigido e bounded, e não criam jobs,
alteram registros fiscais ou autorizam exclusão. PDF/DANFE/DANFSe continua no P7-03.

## Exclusão controlada e recovery (P9-03)

`nfx.retention.deletion` é o owner da intenção e da saga; `ArtifactStorageService` é a única
fronteira de bytes. `POST /api/retention/documents/<id>/deletion` revalida o `scope-v1`, a
elegibilidade, o papel Administrator, a confirmação literal e o motivo bounded antes de criar
`DeletionOperation`/`DeletionItem` e enfileirar `retention.delete`. A migration `0020` é aditiva;
`ExportItem.document` pode ser nulificado para não deixar referência protegida a documento
apagado. O worker só informa sucesso quando todos os bytes verificados e as relações do conjunto
chegam a estado terminal.

O fluxo físico é deliberadamente uma saga: cada artefato exige digest, tamanho e versão atuais,
depois uma transação relacional resolve `ReceivedUnit`, manifestação, exportação, eventos,
evidências, renders e documento. `recovery_required` ou `failed` preserva o estado e permite
`POST /api/retention/deletions/<id>/resume`; nenhum retry pode repetir um item já concluído de forma
insegura. Não adicione restore automático, exclusão de backup, payload fiscal, chave de objeto ou
exceção externa ao contrato. Atualize o escopo/hash quando mudar relações ou artefatos.

Use fixtures sintéticas e valide o fluxo com `tests/unit/test_retention.py`,
`tests/integration/test_retention.py`, `python backend/manage.py makemigrations nfx --check`,
`make lint`, `make build` e `make test-integration`. A integração precisa de PostgreSQL/MinIO
efêmeros; nunca aponte esses testes para volumes de runtime.
