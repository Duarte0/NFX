# Hardening, ameaças e testes de falha

## Metadados

- **Fase/status:** P9 — pronta quando capacidades do MVP e P9-01/02/03 existirem.
- **Backlog:** P9-04. **Dependências:** P5, P6, P7, P8, P9-01/02/03.
- **PRD:** SEC-001, SEC-002, SEC-003, SEC-004, SEC-005, SEC-006, SEC-007, SEC-008, SEC-009; OPS-001, OPS-002, OPS-003, OPS-004, OPS-005, OPS-006; NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008. **Aceite:** AC-004, AC-006, AC-007, AC-009, AC-010, AC-012, AC-014, AC-016, AC-017, AC-024, AC-025.
- **Arquitetura:** seções 8, 21, 22, 33, 36–41; todos ADRs como conjunto de invariantes.

## Propósito e resultado

Produzir threat review rastreável, corrigir achados críticos e demonstrar degradação/recuperação segura e capacidade aproximada de 200 empresas com dados sintéticos.

## Baseline, escopo e não escopo

O baseline esperado é o MVP implementado até P9-03, com testes locais de cada spec. Revisar sua superfície integrada: sessão/CSRF/RBAC, uploads/XML, SSRF/allowlist, secrets, objetos, jobs/cursor, downloads, PDF/ZIP, retenção/exclusão, backup/runtime. Não adicionar feature, microserviço, broker, HA, acesso externo, pentest produtivo ou metas não definidas.

## Método e contratos de evidência

Criar matriz ameaça→ativo→limite de confiança→controle→teste→resultado→risco residual. Achado tem severidade, reprodução redigida, proprietário/spec e decisão; crítico não resolvido bloqueia somente piloto/release afetado. Valores de capacidade e thresholds são **Proposed** a partir de medição, não SLA Accepted.

Testes obrigatórios: brute force/enumeração, CSRF/cookie/session theft/revocation, URL direta/RBAC, MIME/tamanho/XXE/XML bomb, SSRF/redirect/DNS, traversal/zip, conteúdo em logs/auditoria/backup, segredo de deploy, replay/cursor, lease owner antigo, objeto/hash, retenção, confirmação e portas Docker.

Fault injection: DB/MinIO/fonte indisponível, disco cheio, web/worker/scheduler morto, lease perdido, payload desconhecido, conflito, renderer/ZIP interrompido, backup atrasado e restore falho. Cada cenário deve preservar original/progresso ou não avançar, emitir estado/métrica e ter recuperação exercitada.

## Testes, observabilidade e capacidade

Verificar labels sem cardinalidade/dados sensíveis, correlação ponta a ponta e health sem segredo. Ensaio sintético representa ~200 empresas, múltiplos fluxos/jobs/usuários, concorrência limitada e recursos P9-01; comprovar ausência de limite comercial/artificial, não throughput agressivo.

## Aceite e DoD

- [ ] Matriz cobre ameaças da arquitetura 33 e todos limites de confiança.
- [ ] Falhas da arquitetura 40 têm evidência de estado seguro/recovery.
- [ ] Nenhum canário secreto aparece em logs, erros, auditoria ou backup.
- [ ] Ensaio sintético cobre ~200 empresas e usuários sem limite artificial.
- [ ] Achado crítico está corrigido ou bloqueia explicitamente apenas o release afetado.

DoD: relatório, testes automatizados/runbooks, correções e evidências ligadas a requisitos/ADRs. **Assunções Proposed:** carga e thresholds definidos pelo ambiente medido.
