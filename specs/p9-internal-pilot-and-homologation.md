# Piloto interno e homologação segregada

## Metadados

- **Fase/status:** P9 — pronta após hardening e capacidades finais.
- **Backlog:** P9-05. **Dependências:** P5, P6, P8 e P9-01 a P9-04.
- **PRD:** NFR-003, NFR-005, NFR-007, NFR-008; OPS-001, OPS-002, OPS-003, OPS-004, OPS-005, OPS-006. **Aceite:** AC-024, AC-025 e evidências finais AC-001 a AC-023.
- **Arquitetura:** seções 23, 24, 34–41 e 44; ADR-006, ADR-012, ADR-013.

## Propósito e resultado

Confirmar detalhes fiscais voláteis em homologação segregada e executar piloto interno controlado, reunindo evidência de MVP sem transformar dados/credenciais reais em fixtures ou documentação.

## Baseline, escopo e não escopo

Parte de produto endurecido, restore comprovado e runtime HTTPS. Inclui plano de entrada/saída, allowlist/credenciais segregadas, execução, incidentes e decisão operacional. Não cria produção aberta, acesso externo, SLA, HA, novas fontes ou reduz critérios do PRD.

## Plano e decisões

Homologação confirma endpoints, envelopes, leiautes, limites, cooldowns, manifestação e distribuição vigentes de NF-e/ADN. Resultados atualizam política versionada/adapters sob revisão, sem reescrever histórico. Ambiente tem identidade, volumes, allowlist e credenciais próprios; proteção P0 impede confusão com produção.

Plano **Proposed** deve listar responsável, janela, empresas/dados autorizados, versão, política, critérios de pausa, observação e rollback. Dados reais, se formalmente autorizados, ficam restritos ao ambiente e nunca entram em Git, teste automatizado, log integral ou evidência textual. Piloto mede onboarding, coleta 24h sem usuário, reinício, estados, consulta/download/ZIP, RBAC/auditoria, backup/restore e operação aproximada de 200 empresas.

## Falhas, observabilidade e recovery

Incidente pausa fonte/fluxo afetado por política; não zera cursor, apaga acervo nem tenta repetidamente contra bloqueio. Registrar versão, correlação, efeito, dados redigidos, recovery e risco residual. Backup local e TLS autoassinado permanecem limitações Accepted visíveis.

## Testes/evidências e aceite

Checklist de evidência liga cada AC-001–025 à suite, homologação ou piloto; nenhuma evidência contém segredo/conteúdo fiscal. Validar navegador/rede, serviços sem sessão, restart, ~200 empresas e ausência de limite funcional de usuários. Open fiscal é encerrado apenas para a política/versionamento testado; mudança oficial futura não invalida histórico.

- [ ] Ambiente e credenciais são segregados e destinos allowlisted.
- [ ] Regras oficiais confirmadas ficam em política versionada com evidência.
- [ ] Incidente pausa fluxo sem apagar original/cursor.
- [ ] AC-024/025 são demonstrados; AC-001–023 estão referenciados.
- [ ] Nenhum dado real vira fixture, log integral ou documento versionado.

DoD: plano aprovado operacionalmente, execução/evidências redigidas, incidentes tratados e decisão de continuidade. **Open local:** detalhes fiscais até homologação; bloqueiam só a integração correspondente.
