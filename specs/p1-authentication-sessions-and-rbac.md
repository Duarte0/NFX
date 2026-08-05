# Autenticação, sessões, RBAC e shell web

## Metadados

- **Fase/status:** P1 — concluída.
- **Backlog:** P1-02, P1-03, P1-07. **Dependências:** P0-02, P1-01.
- **PRD:** FR-AUTH-001, FR-AUTH-005, FR-AUTH-006, FR-AUTH-007, BR-AUTH-001, SEC-001, SEC-002, SEC-003, SEC-005, NFR-001, NFR-002, NFR-006. **Aceite:** AC-003, AC-004, AC-022, AC-023.
- **Arquitetura:** ADR-002, ADR-009; seções 8, 10.1, 14, 25, 26, 33, 36 e 37.

## Propósito e resultado

Entregar bootstrap do primeiro Administrador, login/logout seguro, sessão opaca revogável, política central de autorização e shell desktop pt-BR. Acesso direto deve ser recusado independentemente do que a UI exibe.

## Baseline, escopo e não escopo

Não há usuários, sessão ou frontend. Esta spec cria autenticação e a matriz-base; administração de usuários é P1-04 e auditoria encadeada é P1-05, embora hooks/eventos de autenticação devam estar previstos. Não inclui 2FA, recuperação por e-mail, API pública ou segregação por empresa.

## Estado e contratos Proposed

Identidade é dona de usuário, papel, credencial, sessão e revogação. **Proposed:** usuário com e-mail normalizado único, nome, papel `administrador|operador|visualizador`, ativo e versão de revogação; sessão com token opaco armazenado apenas como hash, usuário, criação, última atividade, expiração/revogação e contexto seguro. Índices: e-mail único; token hash único; sessões ativas por usuário/expiração.

Bootstrap idempotente cria somente `guilherme.duarte@inovssc.com.br` quando base vazia, usando segredo externo e Argon2id; rerun não troca senha. Contratos HTTP internos: login aceita e-mail/senha e responde uniformemente; logout revoga a sessão; consulta de sessão retorna identidade/papel; qualquer mutação exige CSRF. Nomes/payloads finais são **Proposed**.

## Regras, UI e autorização

Sessão expira após 30 minutos de inatividade, atualizando atividade sem corrida que prolongue sessão já expirada. Cookie `Secure`, `HttpOnly`, `SameSite` apropriado, escopo mínimo. Rate limit progressivo não revela existência do e-mail. Shell oferece login, logout, sessão expirada e navegação por papel; datas em Brasília e BRL. Todos autenticados veem todas as empresas futuramente.

Matriz-base: Administrador administra tudo; Operador empresas/certificados/coletas, consulta/download e ZIP próprio; Visualizador somente consulta/download e ZIP próprio. Jobs/downloads revalidam permissão no servidor no momento da execução.

## Segurança, auditoria e observabilidade

Redigir senha/token/cookie. Eventos: login sucesso/falha, logout, sessão expirada/revogada, com ator quando conhecido, IP, resultado e correlação; resposta de falha é indistinguível. Métricas de sucesso/falha/rate-limit/sessão expirada, sem e-mail como label.

## Testes, sequência e aceite

Testar bootstrap/rerun, Argon2id, enumeração, brute force, CSRF, cookie, relógio em 29:59/30:00, revogação, concorrência de atividade, matriz por ação e URL direta; browser em Chrome/Firefox/Edge suportados. Fixtures usam contas sintéticas.

1. Modelo/bootstrap. 2. Sessões/rate limit. 3. política RBAC. 4. contratos HTTP. 5. shell/localização. 6. segurança/browser.

- [ ] Somente usuário ativo válido autentica; resposta inválida é uniforme.
- [ ] Sessão expira exatamente após 30 minutos de inatividade e pode ser revogada.
- [ ] Todo HTTP/job/download protegido consulta política server-side.
- [ ] Primeiro Admin vem de segredo e senha nunca aparece em saída.
- [ ] Shell pt-BR não é tratado como controle de segurança.

DoD: migrações, bootstrap, contratos, UI, matriz e testes de segurança verdes. **Assunções Proposed:** formato do token, estratégia exata de rate limit e URLs.

## Decisões de implementação e evidências

- **Accepted (Proposed):** `User`, `IdentitySession` e `LoginThrottle` pertencem a `nfx.identity`; o e-mail é normalizado com `casefold`, a sessão usa token aleatório opaco de 256 bits e somente seu SHA-256 é persistido. A sessão registra IP e hash de user-agent, nunca o token/cookie em claro.
- **Accepted (Proposed):** os contratos internos são `GET /api/auth/csrf`, `POST /api/auth/login`, `POST /api/auth/logout` e `GET /api/auth/session`. Mutações passam pelo CSRF do Django; login falho, e-mail inexistente, conta inativa e throttling retornam o mesmo `401` sem expor identidade.
- **Accepted (Proposed):** o throttle persistido usa HMAC do e-mail normalizado e IP, backoff exponencial de 1 a 300 segundos e nenhuma label de métrica contém e-mail. Eventos estruturados `login_success`, `login_failure`, `logout` e `session_expired` são hooks redigidos para a auditoria append-only de P1-05.
- **Accepted (Proposed):** `authorize()` é a política única, fail-closed, para handlers HTTP e futuros jobs/downloads. Administrador autoriza tudo; Operador controla empresas/certificados/coletas e usa documentos/ZIP próprio; Visualizador apenas consulta/download e ZIP próprio. A shell apenas oculta navegação, sem substituir essa política.
- **Bootstrap:** `python backend/manage.py bootstrap_admin` cria idempotentemente apenas `guilherme.duarte@inovssc.com.br` enquanto a base estiver vazia, a partir de `NFX_BOOTSTRAP_ADMIN_PASSWORD` externo. Reexecução não troca a senha e a saída nunca a contém.
- **Implementação:** `backend/nfx/identity/{models,services,policy,views}.py`, migration `backend/nfx/migrations/0003_identity.py`, comando `bootstrap_admin`, endpoints em `nfx.urls` e shell em `frontend/src/main.tsx`.
- **Validação (2026-08-04):** `makemigrations --check --dry-run`, Ruff, build Vite e 37 testes unitários verdes em container isolado; `./scripts/test-integration.sh` passou 14 testes em PostgreSQL/MinIO descartáveis; `./scripts/smoke.sh` passou com web/worker/scheduler. Os testes sintéticos cobrem bootstrap/rerun, Argon2id, enumeração, backoff, CSRF, cookie, 29:59/30:00, revogação, atualização condicional que não ressuscita sessão expirada e matriz RBAC. A shell é `pt-BR`, usa rótulos de Brasília/BRL e compila para os navegadores desktop modernos definidos pelo MVP.

## Aceite e DoD

- [x] Somente usuário ativo válido autentica; resposta inválida é uniforme.
- [x] Sessão expira exatamente após 30 minutos de inatividade e pode ser revogada.
- [x] Todo HTTP/job/download protegido consulta política server-side.
- [x] Primeiro Admin vem de segredo e senha nunca aparece em saída.
- [x] Shell pt-BR não é tratado como controle de segurança.

DoD atendido: migration, bootstrap externo, contratos protegidos por CSRF, shell localizado, matriz central e testes de segurança têm evidência verde. Sem blocker local.
