# Ingestão fiscal comum e integridade

## Metadados

- **Fase/status:** P4 — pronta após P2/P3.
- **Backlog:** P4-01, P4-02, P4-03, P4-04.
- **Dependências:** P1-01/05/06, P2-03, P3-01/03.
- **PRD:** BR-INT-001, BR-INT-002, BR-INT-003, BR-INT-004, BR-INT-005, BR-INT-006, BR-INT-007, BR-INT-008; BR-COLL-006, BR-COLL-008, BR-COLL-009; FR-DOC-001, FR-DOC-005; NFR-004, NFR-005, NFR-008; AUD-005. **Aceite:** AC-005, AC-006, AC-007, AC-008, AC-009, AC-017.
- **Arquitetura:** ADR-003/004/007; seções 14–22, 27, 28, 32, 36, 37 e 40.

## Propósito e resultado

Converter uma unidade simulada em original durável e em documento/evento classificado ou estado explícito de quarentena/conflito. Cursor/NSU avança somente depois de todas as unidades da janela estarem duravelmente tratadas.

## Baseline, escopo e não escopo

Usa objetos, jobs, simuladores, empresa e certificado. Cria modelo fiscal comum, pipeline, reconciliação e API/UI mínima de status/lista. Não implementa adapters oficiais, busca avançada/download, PDF, ZIP ou resolução manual de conflitos.

## Propriedade e schema Proposed

Coleta é dona de execução/cursor/checkpoint/unidade; Documentos, de identidade/vínculos; Artefatos, dos bytes. **Proposed:** documento com empresa, família, papel/categoria, identidade externa normalizada, emissão, autorização, competência, situação, fonte e execução; evento/substituição com vínculo opcional; unidade recebida com cursor/NSU, objeto original, hash, classificação e checkpoint; conflito/quarentena com motivos/evidências. Constraints de identidade usam conjunto oficial mais forte + contexto; índices por empresa/competência/emissão/identificador/situação/direção/categoria. Detalhes físicos são locais e não podem tratar UUID interno como identidade fiscal.

## Pipeline e invariantes

1. Registrar execução/página. 2. Para cada unidade, criar referência pendente e gravar original. 3. Confirmar hash/tamanho. 4. Em transação, deduplicar/classificar, criar documento/evento ou quarentena/conflito e checkpoint. 5. Somente quando a página estiver integralmente tratada, avançar cursor e resultado.

Mesmo identity+hash é replay e não duplica. Identity igual+hash diferente preserva ambas evidências e cria conflito; identidade insuficiente vai à quarentena. Original é imutável; XML completo posterior é artefato relacionado. Competência vem da emissão, nunca coleta; evento não altera competência do pai.

## Contratos, frontend e autorização

Porta de ingestão recebe unidade e contexto, retorna `persistida|replay|quarentena|conflito` e checkpoint. API mínima lista documentos e expõe estado por empresa/fluxo com estados completos. UI mostra sucesso, vazio, parcial, retry, bloqueado, indisponível, sem cobertura, desconhecido, quarentena e conflito; “Nenhum documento encontrado” apenas para consulta válida vazia. Todos autenticados podem ver dados conforme política global; controles de coleta seguem P3-05.

## Segurança, auditoria e observabilidade

Parser trata resposta externa como não confiável: limites, MIME, XXE/XML bomb e redaction. Auditar execução, retry/bloqueio/falha/reprocessamento; log apenas IDs/hash parcial seguro, nunca original. Métricas: unidades recebidas/persistidas/replay/quarentena/conflito, idade de checkpoint e divergência de objeto.

## Falhas, recovery e testes

Injetar falha antes/depois de objeto, transação, checkpoint e cursor; restart/replay deve convergir. MinIO/DB indisponível não avança. Página parcial preserva itens e pendências. Testar unicidade concorrente, competência, vínculo, malformado, identidade insuficiente, mesmo/diferente hash, vazio vs falha e browser. Fixtures P3 exclusivamente sintéticas.

## Aceite e DoD

- [ ] Cursor/NSU só avança após tratamento durável de toda unidade.
- [ ] Retry/replay não duplica documento, evento ou progresso.
- [ ] Conflito/quarentena preservam evidência sem sobrescrita.
- [ ] Estados vazios/degradados são semanticamente distintos.
- [ ] Reconciliador converge após cada ponto de falha exercitado.

DoD: migrações, portas, pipeline, UI mínima, telemetria/auditoria e matriz de fault injection verdes. **Proposed:** esquema/contratos físicos; implementação decide localmente sob estes invariantes.
