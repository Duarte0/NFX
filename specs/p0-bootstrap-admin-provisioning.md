# Provisionamento seguro do administrador inicial

## Metadados

- **Fase/status/versão:** follow-up de fundação — implementado e verificado no issue 0033 — v1.1.
- **Dependências:** `p0-safe-configuration-and-test-isolation.md`, `p1-authentication-sessions-and-rbac.md`.
- **Fontes:** PRD FR-AUTH-001, SEC-001..004 e AC-003; Arquitetura §§25, 26 e 33; Plano “Bootstrap de Administrador”.

## Contexto e objetivo

`bootstrap_admin` exige `NFX_BOOTSTRAP_ADMIN_PASSWORD`, mas a validação fail-closed rejeitava
qualquer `NFX_*` não allowlisted antes do comando. A fronteira de configuração agora reconhece essa
variável somente durante a importação de settings para `bootstrap_admin`, permitindo provisionamento
externo idempotente sem enfraquecer a allowlist global.

## Contrato de configuração e comando

`NFX_BOOTSTRAP_ADMIN_PASSWORD` deve ser reconhecida exclusivamente como segredo de bootstrap; deve ser obrigatória apenas na execução do comando e não fazer parte de `Settings` público, logs, auditoria, respostas HTTP, `--check`, worker ou scheduler. A allowlist continua rejeitando todo `NFX_*` desconhecido. Valor ausente, vazio, placeholder ou configuração de segredo ambígua deve falhar com mensagem segura, sem valor. O comando continua criar somente o administrador inicial aprovado quando a base estiver vazia; reexecução não altera senha, usuário existente ou estado, e concorrência não pode criar mais de um administrador inicial. A senha não tem fonte `*_FILE` suportada.

## Segurança, compatibilidade e testes

O segredo deve existir apenas no ambiente/secret manager do processo que executa o comando, nunca em Git, fixture, output ou traceback. O ajuste não muda cookies, RBAC, política central, emails, API, migração ou credenciais de processos regulares. Testar validação desconhecida versus segredo permitido, valor ausente/placeholder, execução e reexecução, saída redigida, concorrência e que web/worker/scheduler continuam fail-closed sem o segredo.

## Aceite

- [x] O comando opera com segredo externo válido sem ser bloqueado pela allowlist.
- [x] Configurações NFX não reconhecidas continuam recusadas fail-closed.
- [x] Segredo não é persistido, exibido ou aceito por processos não-bootstrap.
- [x] Bootstrap mantém idempotência, unicidade e contratos de autenticação existentes.

## Evidência de implementação

`load_settings()` mantém `KNOWN_NFX_KEYS` como allowlist padrão e recebe uma permissão explícita
somente quando `nfx.settings` é importado para o comando `bootstrap_admin`; a senha não é copiada
para nenhuma dataclass de settings. O comando rejeita ausência, branco e `CHANGE_ME` sem reproduzir
o valor, e variáveis desconhecidas — inclusive uma fonte `NFX_BOOTSTRAP_ADMIN_PASSWORD_FILE` —
continuam falhando fechado. O serviço de identidade serializa a verificação de base vazia com um
lock transacional PostgreSQL, preserva Argon2id/idempotência e transforma a corrida de unicidade em
resultado `unchanged` seguro.

`tests/unit/test_bootstrap_process.py` cobre execução em processo novo, rerun, entradas inválidas,
fonte de arquivo não suportada, rejeição em web/worker/scheduler e redaction da senha. Os testes de
identidade cobrem Argon2id, base não vazia e duas primeiras execuções concorrentes.

DoD concluído em 2026-08-12; não houve migration, mudança de schema, chamada fiscal ou alteração de
autenticação, sessão, cookie ou RBAC.
