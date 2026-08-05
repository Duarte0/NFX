# Fundação de auditoria append-only

## Metadados

- **Fase/status:** P1 — concluída.
- **Backlog:** P1-05. **Dependências:** P1-01, P1-03.
- **PRD:** AUD-001, AUD-002, AUD-003, AUD-004, AUD-005, AUD-006, AUD-007, AUD-008, AUD-009, AUD-010; SEC-007. **Aceite:** AC-014.
- **Arquitetura:** ADR-010; seções 14, 16, 27, 33, 36, 37 e 40.

## Propósito e resultado

Fornecer escrita append-only, consulta administrativa e verificação de integridade para todos os eventos exigidos. Uma ação crítica não pode declarar sucesso sem seu evento; alteração, remoção ou reordenação deve ser detectável.

## Baseline, escopo e não escopo

Não existe auditoria. Esta spec cria a infraestrutura, taxonomia mínima e tela/consulta administrativa. Specs posteriores integram seus próprios eventos. Auditoria não substitui logs, backup ou conteúdo fiscal e nunca armazena XML/PDF/PFX/segredo.

## Estado e schema Proposed

Auditoria é dona dos eventos. **Proposed:** evento com ID monotônico/UUID, fluxo de cadeia, hash anterior/próprio, timestamp UTC, ator e papel opcionais, IP, ação, entidade/tipo/ID, resultado, motivo, correlação e contexto antes/depois redigido. Índices por tempo, ator, ação, entidade e resultado. Não expor update/delete no repositório da aplicação; privilégios DB devem separar escrita/consulta quando praticável. Algoritmo/canonicalização de hash são Proposed e precisam de vetor de teste estável.

## Contratos, comportamento e autorização

Porta `append` recebe evento já classificado, aplica redaction/canonicalização e devolve ID/hash. Porta de consulta pagina/filtra. Verificador lê cadeia e produz resultado sem reescrever. Somente Administrador consulta auditoria completa; outros veem apenas resultado operacional fornecido pelo módulo dono.

Taxonomia deve cobrir login/logout/falha; usuário/papel/senha; empresa/certificado; coleta/retry/bloqueio; consulta/download; PDF; ZIP; retenção/exclusão; configuração/saúde. Desativar empresa/usuário, resetar senha, alterar papel e excluir documento exigem motivo antes da mutação.

## Falhas, segurança e observabilidade

Para ação crítica transacional, evento e estado relacional concluem juntos ou nenhum declara sucesso. Operações externas usam intenção/resultado correlacionados. Falha do auditor bloqueia ação crítica e retorna erro útil redigido. Métricas: append falho, quebra de cadeia, atraso do verificador; health degradado quando integridade falha.

## Testes e evidências

Testar cada classe AUD-002–007, ator anônimo em login falho, motivo ausente, RBAC, paginação, dois writers, adulteração/remoção/reordenação, redaction com canários e falha DB. Evidência: matriz evento→campos, vetores de hash e relatório de integridade.

## Decisões de implementação e evidências

- **Accepted (Proposed resolvido):** uma cadeia global serializada por `nfx_audit_chain` é a escolha inicial; um lock de linha PostgreSQL atribui a sequência monotônica. Isso evita complexidade prematura de fluxos independentes e mantém uma ordenação total verificável.
- **Accepted (Proposed resolvido):** `audit-v1` usa SHA-256 de JSON canônico (chaves ordenadas, separadores compactos), incluindo hash anterior e todos os campos persistidos. O vetor é coberto em `tests/integration/test_audit.py`.
- **Implemented:** `nfx.audit.models`, `nfx.audit.services` e a migração `0004_audit_foundation` criam eventos e cadeia; um trigger PostgreSQL recusa `UPDATE` e `DELETE` mesmo por acesso ORM comum.
- **Implemented:** `GET /api/audit/events` pagina e filtra por ator, ação, entidade e resultado, exclusivamente para Administradores; a shell React mostra a consulta apenas para esse papel.
- **Implemented:** login, falha/rate-limit de login e logout passam pela porta de auditoria na mesma transação do estado de sessão. Falha de escrita não permite declarar sucesso de autenticação.
- **Validation:** `./scripts/test-integration.sh` passou (18 testes) e a execução isolada de `tests/unit` passou (37 testes), ambas com PostgreSQL/MinIO e dados sintéticos. A migração foi aplicada e `schema_status` confirmou `0004_audit_foundation`.

## Aceite e DoD

- [x] Operações normais, inclusive Admin, não editam/apagam eventos — trigger e testes de update/delete.
- [x] AUD-002–007 produzem campos aplicáveis de AUD-008 — a porta/taxonomia recebe todos os campos e autenticação já emite AUD-002; specs donas dos demais eventos usam a mesma porta.
- [x] Ações AUD-009 sem motivo são recusadas — `REQUIRES_REASON` e teste de recusa.
- [x] Cadeia detecta alteração, remoção e reordenação — `AuditVerifier` e teste de três cenários.
- [x] Senha, token, chave, PFX, XML e PDF não entram no payload — redaction compartilhada e teste com canários.

DoD: migração, porta, consulta UI, verificador, alertas e suite verde. O resultado do verificador integra a resposta administrativa; integrações futuras de health/métricas usarão a mesma verificação em P3/P8. Não há blocker local.
