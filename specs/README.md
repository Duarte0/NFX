# Índice de implementação das specs

## Autoridade, baseline e regra de uso

Estas 25 specs são o handoff de implementação do MVP. `PRD.md` é autoridade de produto; `ARCHITECTURE.md`, de decisões/invariantes; `IMPLEMENTATION_PLAN.md`, de backlog e sequência; o código existente, da baseline real. P0, P1 e P2 estão concluídos; a higiene do template de ambiente foi verificada no issue 0007 e o contrato reproduzível de `make build` foi concluído no issue 0008. O issue 0011 concluiu a extração arquitetural transversal do frontend sem alterar o status ou o contrato de nenhuma spec P1–P4.

Uma spec individual fica concluída somente quando seu próprio DoD tem evidência. Uma fase fica concluída somente quando todas as specs da fase estão concluídas; marcar uma spec não marca automaticamente a fase.

## Ordem, cobertura e dependências diretas

| # | Progresso | Spec | Fase | Backlog exato | Dependências diretas |
|---:|:---:|---|---|---|---|
| 1 | [x] | [p0-project-foundation.md](p0-project-foundation.md) | P0 | P0-01, P0-03, P0-05 | Nenhuma spec anterior; baseline implementada |
| 2 | [x] | [p0-safe-configuration-and-test-isolation.md](p0-safe-configuration-and-test-isolation.md) | P0 | P0-02, P0-04 | P0-01 |
| 3 | [x] | [p1-persistence-and-migrations.md](p1-persistence-and-migrations.md) | P1 | P1-01 | P0-03 |
| 4 | [x] | [p1-object-storage-and-integrity.md](p1-object-storage-and-integrity.md) | P1 | P1-06 | P0-03, P1-01 |
| 5 | [x] | [p1-authentication-sessions-and-rbac.md](p1-authentication-sessions-and-rbac.md) | P1 | P1-02, P1-03, P1-07 | P0-02, P1-01 |
| 6 | [x] | [p1-audit-foundation.md](p1-audit-foundation.md) | P1 | P1-05 | P1-01, P1-03 |
| 7 | [x] | [p1-user-administration.md](p1-user-administration.md) | P1 | P1-04 | P1-02, P1-03, P1-05 |
| 8 | [x] | [p2-company-lifecycle-and-public-enrichment.md](p2-company-lifecycle-and-public-enrichment.md) | P2 | P2-01, P2-02, P2-04 (empresa/UI) | P0-04, P1-03, P1-05 |
| 9 | [x] | [p2-certificate-lifecycle-and-envelope-encryption.md](p2-certificate-lifecycle-and-envelope-encryption.md) | P2 | P2-03, P2-04 (certificado/UI) | P1-05, P1-06, P2-01 |
| 10 | [x] | [p3-durable-jobs-leases-and-policy-engine.md](p3-durable-jobs-leases-and-policy-engine.md) | P3 | P3-01/P3-02/P3-04 implementados e validados | P1-01, P1-05 |
| 11 | [x] | [p3-manual-collection-control.md](p3-manual-collection-control.md) | P3 | P3-05 concluído no issue 0005 | P1-03, P1-05, P3-01, P3-02 |
| 12 | [x] | [p3-fiscal-adapter-simulation-and-fixtures.md](p3-fiscal-adapter-simulation-and-fixtures.md) | P3 | P3-03 concluído | P0-04, P3-01 |
| 13 | [x] | [p4-fiscal-document-ingestion-and-integrity.md](p4-fiscal-document-ingestion-and-integrity.md) | P4 | P4-01/P4-02/P4-03/P4-04 concluídos; migration `0014` e testes de matriz | P1-01/05/06, P2-03, P3-01/03 |
| 14 | [ ] | [p5-nfe-distribution-and-manifestation.md](p5-nfe-distribution-and-manifestation.md) | P5 | P5-01, P5-02, P5-03 | P2-03, P3-02/03, P4-02 |
| 15 | [ ] | [p6-nfse-adn-distribution-and-coverage.md](p6-nfse-adn-distribution-and-coverage.md) | P6 | P6-01, P6-02 | P2-03, P3-02/03, P4-02 |
| 16 | [ ] | [p7-document-consultation-and-individual-download.md](p7-document-consultation-and-individual-download.md) | P7 | P7-01, P7-02 | P1-03/04, P4-01/04 |
| 17 | [ ] | [p7-danfe-danfse-rendering.md](p7-danfe-danfse-rendering.md) | P7 | P7-03 | P3-01, P4-01, P7-01, renderer Open |
| 18 | [ ] | [p8-zip-export.md](p8-zip-export.md) | P8 | P8-01 | P3-01, P7-01/02; P7-03 se PDF |
| 19 | [ ] | [p8-dashboard-and-operational-health.md](p8-dashboard-and-operational-health.md) | P8 | P8-02 | P3-04 + dados P2–P7 disponíveis |
| 20 | [ ] | [p8-retention-eligibility.md](p8-retention-eligibility.md) | P8 | P8-03 | P1-05, P4-01, P7-03 se houver PDF |
| 21 | [ ] | [p9-runtime-and-https.md](p9-runtime-and-https.md) | P9 | P9-01 | P1-01, P1-03, P3-04 |
| 22 | [ ] | [p9-backup-and-restore.md](p9-backup-and-restore.md) | P9 | P9-02 | P1-06, P2-03, P3-04 |
| 23 | [ ] | [p9-controlled-deletion.md](p9-controlled-deletion.md) | P9 | P9-03 | P8-03, P9-02 comprovado |
| 24 | [ ] | [p9-hardening.md](p9-hardening.md) | P9 | P9-04 | P5–P8, P9-01/02/03 |
| 25 | [ ] | [p9-internal-pilot-and-homologation.md](p9-internal-pilot-and-homologation.md) | P9 | P9-05 | P5, P6, P8, P9-01..04 |

Todos os itens P0-01 a P9-05 estão cobertos. P2-04 é deliberadamente compartilhado pelas duas specs P2 porque a UI integra empresa e certificado; isso é cobertura transversal, não execução duplicada. Nenhum outro backlog tem dois proprietários primários. A seção “Specs futuras” de P3 inclui a spec manual; sua ausência na tabela original do mapa é corrigida neste índice conforme instrução explícita.

Todas as entradas acima são specs ativas; não há specs superseded, deprecated ou template versionado neste diretório. P5 e P6 estão prontas para implementação com simuladores, mas não estão implementadas; a conexão real continua bloqueada apenas pelas decisões externas registradas. A caixa de P0 registra a fundação entregue, incluindo o contrato reproduzível de `make build`.

## Fluxo de entrega

Uma spec ativa define o contrato verificável de uma fatia. A passagem de issues a desdobra em itens rastreáveis sem alterar o contrato; a passagem de implementação executa esses itens, adiciona evidência ao DoD da spec e atualiza somente sua própria caixa. Novas mudanças de escopo retornam primeiro à spec e ao plano, nunca são inferidas de uma issue ou de arquivos já existentes.

## Paralelismo e conclusão de fase

- Após P0, partes independentes de P1 podem avançar quando suas dependências diretas estiverem verdes.
- Após o núcleo P1, P2 e P3 podem avançar em paralelo; dentro de P3, simuladores e controle manual seguem após a engine.
- Após P4, P5, P6 e P7-01 podem avançar em paralelo; P5/P6 nunca compartilham cursor/NSU.
- Dashboard pode crescer desde P3-04, declarando capacidades ausentes; runtime P9-01 também pode avançar após P1/P3, sem esperar todo P8.
- P9-03 depende de restore comprovado, mas esse gate não bloqueia outras specs.

Fases: P0 tem 2 specs implementadas e verificadas; P1 tem 5 specs concluídas; P2 tem 2 specs concluídas; P3, 4 (P3-01/02/03/04 e P3-05 concluídos); P4 tem P4-01/P4-02/P4-03/P4-04 implementados dentro da spec; P5, 1; P6, 1; P7, 2; P8, 3; P9, 5. Total: 25.

## Decisões Open, Blocked, Deferred e Proposed

- **Open/Blocked local:** biblioteca DANFE/DANFSe bloqueia somente P7-03.
- **Open:** endpoints, envelopes, limites e leiautes vigentes bloqueiam somente transports reais/homologação P5/P6; simuladores/domínio continuam implementáveis.
- **Blocked local:** P9-03 só habilita exclusão após evidência P9-02.
- **Deferred:** CA confiável, backup fisicamente separado e broker/escalonamento horizontal; nenhum bloqueia o MVP definido.
- **Accepted exceptions:** TLS autoassinado e backup local permanecem riscos explícitos.
- **Proposed:** nomes físicos, schemas/payloads/URLs, ferramentas, thresholds e políticas não definidos nas fontes podem ser decididos na sessão dona da spec, desde que documentados e testados contra seus invariantes.

## Como escolher a próxima spec

Escolha a primeira linha não marcada cujas dependências diretas tenham DoD comprovado e cujo blocker local não se aplique. Não espere conclusão de uma fase inteira quando a tabela permite paralelismo, nem crie aprovação global. Em empate, priorize o caminho crítico do plano e a menor spec que produz evidência integrada. P0 está concluída; P1-01 a P1-07, P2-01/P2-02/P2-03/P2-04, P3-05 e P4-01/P4-02/P4-03/P4-04 estão implementados. A próxima implementação pertence ao caminho P5/P6, respeitando os bloqueios e a ordem do backlog.

Testes automatizados normais usam somente simuladores e fixtures sintéticas: nunca certificado, CNPJ de cliente, XML, credencial ou endpoint produtivo. Cada implementação atualiza apenas sua caixa; a fase é registrada separadamente no acompanhamento do projeto quando todas as caixas daquela fase estiverem concluídas.
