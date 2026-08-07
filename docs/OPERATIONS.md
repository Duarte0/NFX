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

Worker e scheduler gravam heartbeats por identidade de processo (`component` + `process_id`).
Restart cria uma nova evidência sem apagar o processo anterior, e atualizações concorrentes de
identidades diferentes são independentes. Os limites são validados antes do boot por
`NFX_WORKER_HEARTBEAT_TIMEOUT_SECONDS`, `NFX_SCHEDULER_HEARTBEAT_TIMEOUT_SECONDS` e
`NFX_JOB_BACKLOG_DELAY_SECONDS` (1–86400 segundos); os padrões são 30, 30 e 300.
