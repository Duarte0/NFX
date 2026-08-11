# Operação e saúde inicial (P3-04)

`/health/live` continua independente de serviços e `/health/ready` continua verificando apenas
PostgreSQL/schema e MinIO. Administradores autenticados podem consultar `/health/operational`, uma
resposta somente leitura com contagens seguras da fila, idade do item vencido, tentativas,
retries, leases expirados, cooldowns, bloqueios e categorias de resultado. O contrato também
mostra a frescura durável de worker e scheduler e diferencia `ready`, `stale`, `missing`,
`stopped`, `degraded` e `unavailable`.

O contrato não expõe payload, resultado bruto, erro, certificado, XML, token, credencial,
endpoint ou identificador de job como label de métrica. Capacidades futuras de fonte fiscal,
disco, backup, documentos e quarentena são declaradas `unavailable` até que tenham uma
implementação própria. Rendering expõe sua disponibilidade segura conforme a versão pinada
instalada.

## Backup verificável e recuperação manual (P9-02)

O backup local é escrito em `NFX_BACKUP_ROOT` (por padrão `/var/backups/nfx`) e captura uma
serialização lógica determinística do PostgreSQL, todos os objetos finalizados, referências de
configuração e probes A1 somente cifrados. Cada conjunto tem estado durável, manifesto versionado,
hash, tamanhos e contagens; falha de banco, objeto, chave, espaço ou interrupção fica `failed` ou
`partial` e não substitui nenhum conjunto anterior. A chave mestre nunca entra em manifesto, log,
auditoria ou argumento de processo.

Use os comandos abaixo somente no host local autorizado:

```sh
python backend/manage.py backup --kind daily --idempotency-key daily:YYYY-MM-DD
python backend/manage.py restore_backup BACKUP_ID \
  --target-root /var/lib/nfx/restore/isolated-YYYY-MM-DD \
  --runtime-root /var/lib/nfx/runtime
```

`restore_backup` exige um destino absoluto e explicitamente isolado, fora do runtime e dos volumes
ativos; configuração ausente ou ambígua falha fechado. Ele é um exercício de validação do conjunto:
verifica manifesto, dump, tamanhos, hashes, contagens, vínculos, auditoria/jobs/cursors e
descriptografia A1 sintética sem alterar volumes vivos. A evidência segura fica no registro de
validação e no `restore-report.json`, sem payloads, senhas, chaves ou caminhos expostos na API.

Esse comando não é restore operacional completo: não cria PostgreSQL/MinIO, não importa o dump e
não repopula objetos. Para recuperação após desastre, operador autorizado prepara host isolado,
sobe PostgreSQL e MinIO, importa o dump, restaura os objetos indicados pelo manifesto, fornece a
chave mestre pelo mecanismo seguro externo, sobe a aplicação e valida o estado. A chave mestre não
faz parte do backup. Essa recuperação manual documentada é a estratégia aceita do MVP.

Administradores consultam `GET /api/backups/status` ou `GET /api/backups`; os demais papéis recebem
negação sem revelar existência ou localização. A seleção conserva independentemente 7 diários,
4 semanais e 12 mensais. Expiração remove somente diretórios de backup expirados, nunca o acervo
fiscal. `/var/backups/nfx` no mesmo host é uma limitação Accepted: não cobre perda física,
ransomware ou recuperação de desastre; recuperação material e destino fisicamente separado devem
ser protegidos fora do repositório.

O perfil de runtime HTTPS, a fronteira do proxy, os serviços privados, os limites e os
procedimentos de reinício/upgrade/rollback estão documentados em
[`docs/RUNTIME.md`](RUNTIME.md). Backup verificável, validação do conjunto e recuperação manual
documentada continuam sendo o incremento P9-02.

Worker e scheduler gravam heartbeats por identidade de processo (`component` + `process_id`).
Restart cria uma nova evidência sem apagar o processo anterior, e atualizações concorrentes de
identidades diferentes são independentes. Os limites são validados antes do boot por
`NFX_WORKER_HEARTBEAT_TIMEOUT_SECONDS`, `NFX_SCHEDULER_HEARTBEAT_TIMEOUT_SECONDS` e
`NFX_JOB_BACKLOG_DELAY_SECONDS` (1–86400 segundos); os padrões são 30, 30 e 300.

## Dashboard inicial (P8-02)

Usuários autenticados podem consultar `GET /api/dashboard`, uma leitura sem persistência própria
que agrega apenas dados já duráveis de empresas, documentos, coletas e jobs. Os limites `from` e
`to` são datas civis de Brasília em intervalo semiaberto `[from,to)`, com máximo de 366 dias; a
resposta sempre informa o período anterior de mesma duração. `zero`, `unavailable`, `degraded` e
`unknown` são estados distintos, e cada card disponível aponta para a lista existente com filtros
suportados. Valores fiscais ainda não persistidos, fontes P5/P6, rendering e disco não são
inventados: aparecem como capacidade indisponível.

Os cinco cards de coleta (`recent`, `running`, `failed`, `blocked` e `partial`) abrem o drill-down
`GET /api/collections/executions` com o período exibido e o estado correspondente. A consulta é
autenticada, somente leitura e bounded: exige `from`, `to` e `state`, aplica `[from,to)` em
Brasília, informa o total reconciliado e mostra até 50 execuções com metadados redigidos. `recent`
é o total das execuções no período, não um novo estado persistido. Período inválido retorna erro
seguro; indisponibilidade não é apresentada como zero. A tela distingue carregamento, vazio válido,
filtro inválido, indisponibilidade e degradação.

Os sete cards de documentos também preservam `from`/`to` e seus filtros P7 canônicos ao abrir
`#documentos`. O arquivo aceita o intervalo civil `[from,to)` de Brasília, informa em `total` a
quantidade server-side de documentos persistidos da seleção e mantém quarentena/status como
linhas distintas. `tomada` e `prestada` são as categorias NFS-e válidas; falha de consulta retorna
503 seguro e não vira zero. A leitura não cria jobs, transições, artefatos ou auditoria adicional
além da consulta P7 existente.

Os cards `companies.active` e `companies.inactive` abrem, para Administradores e Operadores, a
seção `#empresas` com `lifecycle=active` ou `lifecycle=inactive`. O primeiro corresponde somente
a empresas `ativa`; o segundo reúne `cadastrada` e `desativada`, como a agregação do dashboard.
Visualizadores não recebem esses links porque a lista de empresas permanece protegida por
`ADMINISTER_COMPANIES`.

`GET /api/companies?lifecycle=active|inactive` retorna uma página limitada, total server-side,
filtro normalizado e cursor estável por UUID. O total cobre toda a seleção, inclusive quando a
página é continuada por cursor. O endpoint preserva `status`, `search`, `limit` e `cursor` legados;
filtros lifecycle repetidos, conflitantes ou desconhecidos retornam `400`. Uma falha na fonte
retorna `503` e degrada somente a consulta de empresas; não é apresentada como zero e não gera
escrita operacional.

Detalhes de dependências, processos e backlog operacional aparecem no dashboard somente para
Administradores, reutilizando o contrato de `/health/operational`. Operadores e Visualizadores
recebem apenas os cards fiscais/operacionais permitidos e nunca recebem os detalhes técnicos por
URL direta. Para Administradores, `operational_health.backup` reutiliza `backup_status()` como
única fonte e mostra apenas `success`, `failure` ou `unavailable`, estado seguro do último conjunto,
idade medida do último sucesso, contagens concluídas limitadas a 7/4/12 e estado/código seguro da
última validação. Caminhos, manifesto, chaves de objeto, IDs e exceções do provedor não entram na
resposta. Falha na fonte degrada somente esse resumo. O endpoint não cria snapshots, jobs,
auditoria adicional, cache ou migração.

## DANFE/DANFSe derivado (P7-03)

`POST /api/documents/<id>/pdf/render` solicita ou regenera o PDF de uma NF-e/NFS-e com o mesmo
RBAC de consulta; a resposta informa `unavailable`, `pending`, `available`, `failed` ou
`unsupported`. O worker `document.render_pdf` usa a API Python pinada de
`BrazilFiscalReport[danfse]==1.0.1`, lê somente XML finalizado/verificado pelo
`ArtifactStorageService` e não executa CLI, subprocesso, shell ou transporte fiscal.

Cada PDF é um artefato derivado identificado por documento, representação, renderer e versão.
Bytes, hash, tamanho e MIME são verificados antes da finalização; reintentos reutilizam o
equivalente íntegro e versões futuras preservam o histórico. `GET /api/documents/<id>/pdf` repete
autorização e verificação de integridade antes do download. Falhas do renderer ou storage não
alteram nem removem o XML original, que continua baixável quando autorizado.

Solicitação, negação, deduplicação, início, sucesso, falha, regeneração e download entram na
auditoria com contexto bounded; os contadores de rendering não carregam conteúdo fiscal,
segredos ou chaves de objeto. A retenção e a futura exclusão seguem o documento pai.

## Retenção (P8-03)

A tela `#retencao` e as rotas `/api/retention/documents*` são exclusivamente administrativas e
somente de leitura. A decisão `retained`, `eligible` ou `non_executable` é recalculada sob demanda
com `retention-v1`; o operador deve tratar `non_executable` como bloqueio e corrigir a evidência
antes de qualquer futura operação. A resposta não contém payload fiscal nem chave de objeto.

A prévia é um inventário de metadados, não uma autorização de exclusão. Seu `scope-v1` inclui as
referências, digests, tamanhos, versões e estados dos originais/XML e vínculos de eventos. Se a
evidência mudar, a tentativa com o hash anterior retorna `409` e a prévia deve ser gerada de novo.
Não existe exclusão automática nem cleanup genérico. A exclusão controlada usa os contratos próprios
de retenção, confirmação, motivo, auditoria e coerência de documento/artefatos; P9-02 já fornece seu backup
verificável e procedimento manual de recuperação.

## Exclusão fiscal controlada (P9-03)

A exclusão nunca é automática. Um Administrador consulta a prévia atual e envia somente a
confirmação exata `EXCLUIR:<document-id>:<scope-hash>` e um motivo de 1–1000 caracteres para:

```text
POST /api/retention/documents/<document-id>/deletion
GET  /api/retention/deletions/<operation-id>
POST /api/retention/deletions/<operation-id>/resume
```

As requisições mutantes exigem sessão válida, CSRF e o papel Administrator. O worker registra o
handler `retention.delete`; a operação passa por `pending`, `executing`, `recovery_required`,
`failed` ou `completed`. O status e os itens mostram somente IDs, prefixos, tamanhos, versões e
códigos seguros — nunca chaves MinIO, bytes ou exceções do provedor.

Ausência, divergência, inacessibilidade de objeto, perda de lease, falha de banco ou falha da
cadeia de auditoria não é sucesso. Preserve a operação em recovery, corrija a causa somente pelo
procedimento autorizado e use `resume`; se houver perda física ou divergência irrecuperável,
execute a validação e a recuperação manual isolada do P9-02. Não restaure automaticamente, não
apague backups e não use `down --volumes` no runtime. A confirmação de conclusão exige que os
bytes e os vínculos relacionais do conjunto estejam reconciliados; empresas, usuários, backups,
auditoria e documentos não relacionados permanecem intactos.
