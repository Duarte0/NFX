# Operação e saúde inicial (P3-04)

`/health/live` continua independente de serviços e `/health/ready` continua verificando apenas
PostgreSQL/schema e MinIO. Administradores autenticados podem consultar `/health/operational`, uma
resposta somente leitura com contagens seguras da fila, idade do item vencido, tentativas,
retries, leases expirados, cooldowns, bloqueios e categorias de resultado. O contrato também
mostra a frescura durável de worker e scheduler e diferencia `ready`, `stale`, `missing`,
`stopped`, `degraded` e `unavailable`.

O contrato não expõe payload, resultado bruto, erro, certificado, XML, token, credencial,
endpoint ou identificador de job como label de métrica. Capacidades futuras de fonte fiscal,
disco, backup, documentos, quarentena e rendering são declaradas `unavailable` até que tenham
uma implementação própria.

O perfil de runtime HTTPS, a fronteira do proxy, os serviços privados, os limites e os
procedimentos de reinício/upgrade/rollback estão documentados em
[`docs/RUNTIME.md`](RUNTIME.md). Backup e restore continuam sendo o incremento P9-02.

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
suportados. Valores fiscais ainda não persistidos, fontes P5/P6, rendering, disco e backup não são
inventados: aparecem como capacidade indisponível.

Detalhes de dependências, processos e backlog operacional aparecem no dashboard somente para
Administradores, reutilizando o contrato de `/health/operational`. Operadores e Visualizadores
recebem apenas os cards fiscais/operacionais permitidos e nunca recebem os detalhes técnicos por
URL direta. O endpoint não cria snapshots, jobs, auditoria adicional, cache ou migração.

## Retenção (P8-03)

A tela `#retencao` e as rotas `/api/retention/documents*` são exclusivamente administrativas e
somente de leitura. A decisão `retained`, `eligible` ou `non_executable` é recalculada sob demanda
com `retention-v1`; o operador deve tratar `non_executable` como bloqueio e corrigir a evidência
antes de qualquer futura operação. A resposta não contém payload fiscal nem chave de objeto.

A prévia é um inventário de metadados, não uma autorização de exclusão. Seu `scope-v1` inclui as
referências, digests, tamanhos, versões e estados dos originais/XML e vínculos de eventos. Se a
evidência mudar, a tentativa com o hash anterior retorna `409` e a prévia deve ser gerada de novo.
Não existe comando, rota, job ou cleanup de exclusão nesta entrega; PDF/DANFE/DANFSe permanece
dependente da decisão P7-03 e exclusão controlada depende do restore comprovado de P9-02.
