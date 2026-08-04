# Configuração segura e isolamento fiscal de testes

## Metadados

- **Fase/status:** P0 — concluída.
- **Backlog:** P0-02, P0-04. **Dependência:** P0-01.
- **PRD:** SEC-007, SEC-008, NFR-007. **Aceite relacionado:** AC-024.
- **Arquitetura:** ADR-008; seções 4, 8, 25, 33, 34 e 38.

## Propósito e resultado observável

Garantir configuração validada antes do boot, segredos fora do repositório, redaction central e impossibilidade de testes/development alcançarem destinos fiscais produtivos. Um perfil inválido ou destino não reconhecido falha antes de abrir rede ou persistir estado.

## Baseline, escopo e não escopo

`.env.example` tem placeholders de Postgres/MinIO e o Compose expõe apenas loopback. Não existe loader tipado, secret store, allowlist ou transporte fiscal. Criar esses contratos e um simulador vazio. Não criar credenciais reais, adaptadores NF-e/ADN, endpoints oficiais, CA, proxy final ou chave mestre versionada.

## Decisões e propostas

É **Accepted** que testes usem simuladores/fixtures sintéticas e bloqueiem produção. É **Proposed** que segredos sejam fornecidos por variáveis ou arquivos montados; a implementação pode escolher a biblioteca de settings e os nomes exatos, mantendo tipagem, precedência explícita e validação no boot. Perfis mínimos: teste, desenvolvimento, homologação e runtime; perfis não são inferidos silenciosamente de hostname.

O contrato de configuração distingue valores públicos de segredos, rejeita placeholder `CHANGE_ME`, valida URLs/esquemas e exige allowlist por integração. Teste aceita apenas transporte em memória/local. Desenvolvimento usa simulador por padrão. Homologação/runtime requer combinação explícita de perfil, transport escolhido e destino allowlisted. Produção fiscal não deve ser habilitada por uma única flag genérica.

**Decisões implementadas (Accepted):** foi escolhido um modelo tipado em dataclasses da biblioteca
padrão, centralizado em `nfx.infrastructure.configuration`, para não acrescentar uma dependência de
settings ao scaffold. `NFX_PROFILE` é obrigatório (`test`, `development`, `homologation` ou
`runtime`) e nunca é inferido. `NFX_SECRET_KEY` vem de variável **ou** de
`NFX_SECRET_KEY_FILE` montado; ambos, ausência e `CHANGE_ME` falham seguramente. P0 implementa
somente `simulator://empty`: teste/desenvolvimento ficam restritos a ele; homologação/runtime
exigem transporte, destino e allowlist explícitos, mas ainda não possuem transporte capaz de rede.

## Segurança, redaction e interfaces

Redator central processa campos e exceções antes de logs, auditoria e HTTP. Deve ocultar senha, PFX, chave, token, cookie, header de autorização, query string sensível, XML/PDF e credencial embutida em URL, inclusive estruturas aninhadas. O transporte recebe destino já validado; redirects, DNS/URL alternativos e protocolos não permitidos falham fechados. Nenhum segredo aparece em `.env.example`, fixtures ou mensagens de validação.

## Estado, falhas e observabilidade

Não há schema. Registrar somente classe segura do erro, perfil e correlação; nunca valor rejeitado. Falha de configuração encerra processo com exit code não zero. Tentativa de destino proibido não cria job, objeto, cursor ou auditoria com segredo. Recuperação: corrigir configuração externa e reiniciar; rollback remove a nova configuração sem migração.

## Testes e evidências

Matriz positiva: cada perfil válido; simulador vazio; segredo sintético montado. Negativa: ausência, placeholder, tipo errado, chave desconhecida, destino não allowlisted, redirect, tentativa SEFAZ/ADN produtiva em teste, segredo em erro aninhado. Boundary: URL equivalente/case/porta e lista vazia. Evidência inclui teste de rede com transporte espião provando zero chamadas e snapshot redigido.

## Sequência, aceite e DoD

1. Inventariar settings. 2. Implementar modelo tipado. 3. Separar secrets. 4. Implementar redator. 5. Aplicar guarda ao transporte. 6. Exercitar matriz.

- [x] Perfil inválido ou segredo obrigatório ausente impede boot.
- [x] Testes e desenvolvimento não alcançam destino fiscal produtivo.
- [x] Destino/redirect não reconhecido falha antes da rede.
- [x] Nenhuma saída contém os canários secretos da suite.
- [x] Simulador vazio é o único transporte fiscal inicial.

**Implementação e evidência:** `backend/nfx/infrastructure/configuration.py` valida o contrato no
boot de Django e em checagens de dependência; `redaction.py` é o redator central usado pelo
formatter JSON; `adapters/fiscal.py` fornece o simulador vazio e a guarda que valida destino e
cadeia de redirects antes de chamar o sender. Os três processos Compose recebem o mesmo perfil e
segredo externo/sintético apropriado. `.env.example` e `docs/DEVELOPMENT.md` documentam o contrato.
`tests/unit/test_safe_configuration.py` cobre matriz positiva, ausência/placeholder/tipo/chave
desconhecida, allowlist vazia, URL/case/porta, redaction aninhada, arquivo montado e espião com zero
chamadas. Não há schema nem migração.

DoD: contratos aplicados aos três processos, documentação de configuração e testes de
bypass/redaction verdes. **Concluído em 2026-08-04.** **Open não bloqueante:** endpoints oficiais
permanecem indefinidos; esta spec não precisa conhecê-los.
