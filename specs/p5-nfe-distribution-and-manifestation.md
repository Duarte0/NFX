# Distribuição NF-e e manifestação

## Metadados

- **Fase/status:** P5 — implementação com simulador pronta; conexão real localmente Open.
- **Backlog:** P5-01, P5-02, P5-03. **Dependências:** P2-03, P3-02, P3-03, P4-02.
- **PRD:** FR-NFE-001, FR-NFE-002, FR-NFE-003, FR-NFE-004; BR-NFE-001, BR-NFE-002, BR-NFE-003; BR-INT-003, BR-INT-004, BR-INT-005, BR-INT-006, BR-INT-007, BR-INT-008; AUD-005. **Aceite:** AC-005, AC-006, AC-007, AC-008, AC-009.
- **Arquitetura:** ADR-006/007; seções 10.2, 14, 19, 22, 23, 25, 28, 32, 33, 37, 38 e 40.

## Propósito, baseline e limites

Implementar adapter NF-e independente para recebida/entrada, emitida/saída, eventos, XML completo e Ciência da Operação, sempre via ingestão P4. Baseline possui portas/simuladores, jobs, A1 e pipeline; não possui SOAP/serviço oficial. Não incluir NFC-e/CT-e, upload manual, endpoints fixos ou produção antes de homologação.

## Decisões e contratos

É **Accepted** separar adapters/cursos e preservar bruto antes de mapear. Endpoint, envelope, NSU, sequência e limites são **Open** e política versionada; implementação simulada não espera esses valores. Porta semântica deve suportar consultar distribuição por fluxo/cursor, interpretar unidades, solicitar documento completo, listar/vincular eventos e manifestar. Tipos finais são **Proposed**, mas precisam retornar original, identidade oficial disponível, novo cursor, consumo/cooldown e resultado tipado.

## Estado e comportamento

Coleta possui estado/cursor; Documentos, NF-e/eventos; Certificados fornece handle temporário. **Proposed:** fluxo NF-e identifica empresa + papel `recebida|emitida` + mecanismo/fonte; manifestação registra documento, tipo, resultado oficial, certificado, data e chave idempotente. Constraints impedem manifestação lógica e documento/evento duplicados; índices por chave, empresa/direção e NSU.

Recebida e emitida não compartilham cursor. Resposta bruta é durável antes de resumo/XML/evento. Ciência da Operação é job próprio; só após resultado permitido solicitar XML completo. Repetição retorna efeito existente. Evento sem pai é preservado pendente/quarentenado; situação fiscal vem da fonte.

## UI, autorização, segurança e auditoria

Admin/Operador controlam fluxo via P3-05; todos autenticados consultam resultado conforme P7. Worker revalida empresa/fluxo/certificado antes de chamada. PFX/XML não entram em log/auditoria; adapter valida TLS/destino, tamanho/XML/XXE. Auditar início/conclusão/retry/bloqueio/manifestação; métricas por fluxo: página, NSU, unidades, manifestações, cooldown, erros seguros.

## Falhas, testes e recovery

Timeout/indisponível → retry; cooldown → agenda; A1 permanente → bloqueio; parser desconhecido → quarentena; falha após manifestação e antes de registro → consulta/replay idempotente, nunca repetir cegamente. Testar simulador paginado, dois fluxos, restart, replay, evento antes do pai, XML posterior, manifestação duplicada e destino proibido.

## Aceite e DoD

- [ ] Entrada/saída têm cursores e progresso independentes.
- [ ] Original precede classificação e avanço de cursor.
- [ ] Manifestação/documento/evento não duplicam em retry.
- [ ] XML completo e eventos mantêm vínculos explícitos.
- [ ] Produção permanece bloqueada sem política/homologação.

DoD simulada: adapter, políticas, jobs, estados/UI, auditoria e contratos verdes. **Blocker local:** detalhes oficiais Open bloqueiam somente transporte real/homologação, não domínio nem simulador.
