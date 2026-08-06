# Distribuição NFS-e/ADN e cobertura

## Metadados

- **Fase/status:** P6 — implementação com simulador pronta; conexão real localmente Open.
- **Backlog:** P6-01, P6-02. **Dependências:** P2-03, P3-02/03, P4-02.
- **PRD:** FR-NFSE-001, FR-NFSE-002, FR-NFSE-003; BR-NFSE-001, BR-NFSE-002, BR-NFSE-003; BR-COLL-006, NFR-008. **Aceite:** AC-005, AC-008, AC-009, AC-018.
- **Arquitetura:** ADR-006/007; seções 10.2, 14, 19, 22, 24, 25, 28, 32, 33, 37, 38 e 40.

## Propósito, baseline, escopo

Implementar adapter exclusivamente para Portal Nacional/ADN, distribuição por ator/NSU, classificação tomada/prestada/evento e cobertura explícita. Baseline P4 preserva unidades; P3 simula. Não integrar sistemas municipais, inferir movimento fora do ADN ou tratar todo município como coberto.

## Contratos e estado Proposed

Porta semântica recebe empresa, ator/interessado, fluxo, cursor/NSU e política; retorna cobertura, página/unidades originais, próximo estado e resultado tipado. Endpoint/leiaute/limites são **Open** e versionados. Coleta é dona do cursor por empresa+ADN+ator+fluxo+mecanismo; Empresas, da indicação de cobertura; Documentos, de categoria/vínculos. **Proposed:** snapshot de cobertura com fonte, status, verificado em e evidência segura; índices por empresa/status e fluxo/NSU.

## Regras e comportamento visível

Classificar tomada, prestada, evento/substituição apenas com identificadores suficientes. Original sempre precede parsing. Estados são mutuamente distinguíveis:

- `vazio`: consulta válida concluída, mostra exatamente “Nenhum documento encontrado” e não afirma ausência absoluta;
- `sem_cobertura`: ADN não cobre, com limitação e nenhuma mensagem de vazio;
- `indisponível`: fonte falhou, preserva cursor e prevê retry;
- `parcial`: itens duráveis + lacunas, sem avanço inseguro;
- `desconhecido/quarentena`: original preservado, sucesso não completo.

UI de empresa/coleta mostra cobertura e ação recomendada; detalhe fiscal posterior mostra categoria/vínculos. Admin/Operador controlam fluxo; Visualizador apenas consulta quando disponível.

## Segurança, auditoria e observabilidade

Worker revalida A1/fluxo/destino. Parser limita tamanho, XXE/XML bomb e leiaute; payload não entra em logs. Auditar coleta/resultados; métricas de cobertura, vazio, indisponível, desconhecido, NSU e lag sem CNPJ como label.

## Falhas, testes e recovery

Fixtures simulam cada estado, ator, paginação, replay, substituição, evento sem pai, leiaute desconhecido e restart. Verificar que mensagens não se cruzam, original não é descartado e cursor não avança em parcial/erro. Policy rollback desativa versão sem reescrever histórico.

## Aceite e DoD

- [ ] Vazio, sem cobertura, indisponível e parcial têm contrato/UI distintos.
- [ ] Empresa sem cobertura continua cadastrável.
- [ ] Tomada/prestada/evento e substituição são vinculados quando comprováveis.
- [ ] Desconhecido preserva original e não conclui integralmente.
- [ ] Nenhuma fonte municipal fora do ADN é chamada.

DoD simulada: porta, adapter, estado, UI, auditoria/métricas e testes verdes. **Blocker local:** detalhes oficiais Open bloqueiam somente transporte real/homologação.
