# Jobs duráveis, leases, políticas e observabilidade inicial

## Metadados

- **Fase/status:** P3 — P3-01 implementado; P3-02 e P3-04 pendentes.
- **Backlog:** P3-01, P3-02, P3-04.
- **Dependências:** P1-01 e P1-05.
- **PRD:** FR-COLL-002; BR-COLL-002, BR-COLL-007, BR-COLL-010; OPS-001, OPS-002, OPS-003, OPS-004, OPS-005, OPS-006; NFR-004, NFR-005, NFR-008. **Aceite:** AC-006, AC-007, AC-017, AC-024.
- **Arquitetura:** ADR-003, ADR-005, ADR-007; seções 14, 19–22, 36, 37, 39–41.

## Propósito e resultado

Criar fila PostgreSQL, scheduler e worker retomáveis, política externa versionada e sinais operacionais. Morte/restart não perde job nem permite conclusão após lease perdido; falhas são classificadas e reprogramadas com segurança.

## Baseline, escopo e não escopo

Existem apenas processos vazios de P0. Esta spec implementa infraestrutura genérica e políticas, não botões/rotas manuais, adaptadores fiscais, ingestão ou valores oficiais definitivos. Controle manual é spec separada.

## Estado e schema Proposed

Infra de jobs é dona de job/lease/tentativa; Coleta será dona do estado fiscal. **Proposed:** job com tipo, alvo lógico, prioridade, payload seguro referencial, estado, chave idempotente, agenda, tentativa, máximo, lease owner/issued/expires, erro seguro, resultado e timestamps; tentativa histórica opcional separada. Constraints: chave idempotente única no escopo ativo; lease coerente apenas em execução; índices por estado+agenda+prioridade, lease expirado e alvo. Política versionada possui fonte/fluxo, validade, limites, backoff, jitter e cooldown.

## Contratos e comportamento

API interna: enqueue idempotente retorna job existente/novo; claim transacional com `SKIP LOCKED` ou mecanismo PostgreSQL equivalente; renew somente pelo owner vigente; complete/fail exige lease válido; scheduler agenda recorrências e recupera vencidos, mas não executa fiscal. Handler deve ser idempotente e declarar resultado `sucesso|temporário|cooldown|permanente|parcial`.

Backoff progressivo tem jitter e teto configuráveis; cooldown oficial prevalece sobre tentativa local; certificado/autorização permanente bloqueia sem loop. Valores são políticas, não constantes. Jobs funcionam sem sessão web. Upgrade deve permitir que versão anterior ignore tipos novos e que job em andamento seja retomado por versão compatível.

## Segurança, logs, métricas e health

Payload de job contém IDs, não PFX/XML/token. Logs: job/correlação/tipo/tentativa/duração/resultado; erro redigido. Métricas: fila por estado, idade, claim, retry, lease expirado, bloqueio e handler; health distingue scheduler vivo, worker vivo e backlog atrasado, sem confundir liveness/readiness.

## Falhas e testes

Testar dois workers concorrentes, morte antes/depois do efeito, renew atrasado, lease expirado, conclusão por owner antigo, scheduler morto/restart, DB indisponível, relógio congelado, jitter determinístico e política alterada. Nenhum teste usa rede fiscal. Evidência inclui timeline dos cortes e ausência de efeito duplicado no handler fake.

## Aceite e DoD

- [ ] Claim/lease persistentes impedem execução concorrente lógica.
- [ ] Worker sem lease válido não conclui job.
- [ ] Restart recupera agenda e leases vencidos idempotentemente.
- [ ] Retry/cooldown/bloqueio seguem política versionada.
- [ ] Logs/health/métricas distinguem atraso e falha sem segredo.

DoD: migrações, engine, processos, políticas, telemetria e testes de concorrência/recovery verdes. **Proposed:** tempos/defaults e schema físico; nenhum valor fiscal oficial é fixado.

## Implementação incremental

P3-01 é a fatia concluída nesta iteração: `nfx.jobs` mantém jobs referenciais, claims
PostgreSQL com `SKIP LOCKED`, leases vinculados ao owner, renovação, conclusão/falha seguras,
reclaim e a fronteira de handlers sintéticos usada pelo worker. A fila não decide retry,
backoff, cooldown ou bloqueio permanente; essas decisões continuam pertencendo a P3-02.
Métricas/health operacionais detalhados continuam pertencendo a P3-04.
