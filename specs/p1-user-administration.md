# Administração de usuários

## Metadados

- **Fase/status:** P1 — concluída.
- **Backlog:** P1-04. **Dependências:** P1-02, P1-03, P1-05.
- **PRD:** FR-AUTH-002, FR-AUTH-003, FR-AUTH-004, BR-AUTH-002, SEC-004, SEC-005, AUD-003, AUD-008, AUD-009. **Aceite:** AC-003, AC-004, AC-014, AC-022.
- **Arquitetura:** ADR-009, ADR-010; seções 14, 26, 27, 33 e 37.

## Propósito e resultado

Permitir que somente Administradores listem, criem e editem usuários, alterem papel, redefinam senha e ativem/desativem contas. Desativação deve impedir imediatamente autenticação e uso de qualquer sessão existente, preservando histórico.

## Baseline, escopo e não escopo

Usa usuário/sessão/política de P1-02/03 e auditoria P1-05. Não cria recuperação por e-mail, convite, 2FA, exclusão física, segregação de empresas ou troca obrigatória da senha inicial. Usuário pode alterar sua própria senha, mas reset de terceiro é somente Admin.

## Regras, contratos e UI

Dados: nome obrigatório, e-mail normalizado/único, papel válido e estado ativo. Criar recebe senha inicial apenas na requisição TLS; resposta nunca a devolve. Alterar papel, resetar senha e desativar exigem motivo. Reset invalida sessões existentes como proteção contra reutilização; essa decisão Proposed foi aceita localmente porque o PRD exige revogação explícita na desativação e não proíbe a proteção adicional.

Decisões Proposed aceitas: `GET /api/users` oferece paginação por cursor e filtros `active`/`role`; criação e ações são rotas separadas sob `/api/users`; a shell React apresenta lista/criação em pt-BR apenas a Administradores. Operador/Visualizador não veem o menu e recebem 403 uniforme por acesso direto. A coluna `User.version` implementa controle otimista e as alterações usam lock transacional. A troca voluntária da própria senha usa `POST /api/users/password`, exige a senha atual e revoga as sessões existentes.

## Estado, backend, auditoria e segurança

Identidade continua dona do estado; nenhuma tabela paralela. Backend normaliza/valida, aplica RBAC, abre transação, revoga sessões e grava auditoria. Eventos: usuário criado/editado, papel alterado, senha redefinida, ativado/desativado; incluem ator, alvo, antes/depois redigido, IP, motivo, resultado e correlação. Hash/senha/token não saem em API, log ou auditoria.

## Falhas, testes e recovery

Falha entre desativação e revogação é protegida pela mesma transação que incrementa `revocation_version`; a próxima resolução de sessão falha. Duplicidade retorna erro claro sem indicar senha. A desativação ou remoção de papel do último Administrador ativo é bloqueada. Testes cobrem papéis, acesso direto, motivo, auditoria, versão obsoleta e revogação; o build da shell React cobre a UI localizada.

## Decisões de implementação e evidências

- **Accepted:** `backend/nfx/identity/services.py` concentra os casos de uso administrativos e a troca voluntária de senha; `backend/nfx/identity/views.py` aplica os contratos HTTP; `backend/nfx/identity/policy.py` inclui a ação de troca da própria senha; e `backend/nfx/urls.py` registra as rotas administrativas.
- **Accepted:** o estado permanece no modelo `User`, com e-mail `casefold` validado/único, hash Argon2id, `revocation_version` e `version`; nenhuma tabela paralela foi criada. A migração `backend/nfx/migrations/0005_user_administration_version.py` adiciona o controle otimista.
- **Accepted:** operações administrativas e a troca da própria senha escrevem eventos `user.*` pela porta append-only, com contexto antes/depois redigido. Senhas, hashes, tokens e motivos não são devolvidos como credenciais nem incluídos no contexto.
- **Implemented:** `GET /api/users` pagina por cursor e filtra estado/papel; criação, edição, papel, reset, ativação/desativação e troca da própria senha usam rotas explícitas. A API valida entrada, rejeita duplicidade com 409 claro, retorna 403 uniforme para não administradores e protege mutações com CSRF.
- **Validation:** os 9 testes de `tests/unit/test_user_administration.py` cobrem autorização de serviço/HTTP, CRUD, normalização/duplicidade, motivos, concorrência/versionamento, último Administrador, revogação e redaction; `tests/unit/test_identity.py` cobre autenticação e resolução de sessão. A suite unitária completa passou com 47 testes, `./scripts/test-integration.sh` passou com 18 testes, Ruff e mypy passaram nos módulos alterados, `npm --prefix frontend run build` e `npm --prefix frontend run lint` passaram, e a migração 0005 foi aplicada/rerun no PostgreSQL descartável.

## Aceite e DoD

- [x] Apenas Administrador executa todas as operações administrativas — `tests/unit/test_user_administration.py::test_user_http_routes_are_admin_only_and_never_return_passwords`.
- [x] Usuário desativado não autentica e sessões ativas falham na próxima requisição — `test_deactivation_invalidates_a_real_session_on_next_resolution` e `revocation_version` transacional.
- [x] Histórico de auditoria permanece ligado ao ID, mesmo desativado — `test_admin_can_edit_role_and_lifecycle_with_audited_before_after` e eventos `user.*` com `entity_id` UUID.
- [x] Papel/reset/desativação sem motivo são rejeitados — `test_reasons_versions_and_last_administrator_are_enforced` e validação de serviço/`AuditService`.
- [x] Nenhuma resposta ou evidência contém senha/hash — `test_user_http_routes_are_admin_only_and_never_return_passwords` e contexto de auditoria redigido.

DoD concluído: `backend/nfx/identity/services.py`, `views.py` e `policy.py` implementam os casos de uso e o enforcement server-side; `0005_user_administration_version.py` adiciona concorrência; `frontend/src/main.tsx` oferece a área localizada de usuários; e os eventos passam pela auditoria append-only. Evidência: 47 testes unitários verdes, 18 testes de integração verdes, build/lint da shell, Ruff, mypy e migração forward/rerun. A disponibilidade de extração semântica do Graphify é metadado de navegação e não é requisito de produto, implementação nem DoD desta spec.
