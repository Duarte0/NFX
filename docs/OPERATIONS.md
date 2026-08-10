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

## Backup e restore comprovados (P9-02)

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

O restore exige um destino absoluto e explicitamente isolado, fora do runtime e dos volumes ativos;
configuração ausente ou ambígua falha fechado. Ele verifica manifesto, dump, tamanhos, hashes,
contagens, vínculos, auditoria/jobs/cursors e descriptografia A1 sintética sem alterar volumes
vivos. A evidência segura fica no registro de restore e no `restore-report.json`, sem payloads,
senhas, chaves ou caminhos expostos na API.

Administradores consultam `GET /api/backups/status` ou `GET /api/backups`; os demais papéis recebem
negação sem revelar existência ou localização. A seleção conserva independentemente 7 diários,
4 semanais e 12 mensais. Expiração remove somente diretórios de backup expirados, nunca o acervo
fiscal. `/var/backups/nfx` no mesmo host é uma limitação Accepted: não cobre perda física,
ransomware ou recuperação de desastre; recuperação material e destino fisicamente separado devem
ser protegidos fora do repositório.

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
