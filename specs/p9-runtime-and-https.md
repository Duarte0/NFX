# Runtime interno e HTTPS

## Metadados

- **Fase/status:** P9 — pronta após núcleo e health.
- **Backlog:** P9-01. **Dependências:** P1-01, P1-03, P3-04.
- **PRD:** SEC-006, SEC-008, OPS-002, OPS-007, NFR-007. **Aceite:** AC-024.
- **Arquitetura:** ADR-001, ADR-002, ADR-013; seções 7–9, 12, 33, 34, 36, 39–41.

## Propósito e resultado

Entregar topologia Docker de runtime com proxy como única entrada HTTPS, processos web/worker/scheduler separados, serviços internos não publicados, volumes persistentes e limites que protejam a aplicação.

## Baseline, escopo e não escopo

Compose atual é somente desenvolvimento e publica Postgres/MinIO em loopback. Esta spec cria configuração runtime e procedimento de upgrade/rollback. Não cria acesso externo, CA interna, HA, broker, cluster, backup separado nem trata certificado autoassinado como confiança equivalente a CA.

## Decisões e configuração Proposed

São **Accepted** host único Docker, HTTPS autoassinado, mesma versão de aplicação e limites distintos. **Proposed:** proxy específico, nomes de serviços/redes, valores CPU/memória e estratégia de gerar/montar certificado; implementação mede e documenta. Segredos/certificado não entram na imagem/repositório.

Proxy publica somente HTTPS para rede interna, aplica tamanho/timeout/headers adequados e encaminha web. DB, MinIO/console, worker e scheduler ficam em rede privada. Web readiness depende de schema/DB/MinIO conforme operação; liveness não executa dependência cara. Worker/scheduler têm health próprio. Saídas obedecem allowlist P0.

## Segurança, observabilidade e falhas

Cookies Secure/HttpOnly/SameSite e CSRF permanecem obrigatórios. Logs registram versão/container/correlação sem segredo. Métricas/health distinguem vivo, pronto, degradado, espaço e dependências. Reinício web não mata jobs; worker morto recupera lease; scheduler morto recupera agenda; DB/MinIO indisponível impede progresso seguro. Limite de PDF/ZIP não deve derrubar web.

## Testes, rollback e evidência

Testar portas do host, HTTPS/certificado, redirect/rejeição HTTP, headers/cookies, acesso direto negado, restart de cada serviço, dependência indisponível, limite CPU/memória/disco e coletores sem browser. Upgrade aplica migrações compatíveis e health antes de tráfego; rollback usa imagem/config anterior enquanto schema compatível, sem apagar volume.

## Aceite e DoD

- [ ] Proxy é a única entrada de usuário e exige HTTPS.
- [ ] DB/MinIO/console/worker/scheduler não são publicados.
- [ ] Processos usam mesma versão e sobrevivem a reinícios independentes.
- [ ] Health distingue liveness/readiness/degradação.
- [ ] Limitação autoassinada está documentada.

DoD: imagens/config, runbook, limites medidos, testes/evidências verdes. **Deferred:** CA confiável e HA não bloqueiam o MVP.
