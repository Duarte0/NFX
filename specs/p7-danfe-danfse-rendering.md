# Renderização de DANFE e DANFSe

## Metadados

- **Fase/status:** P7 — **Blocked localmente** até seleção do renderer.
- **Backlog:** P7-03. **Dependências:** P3-01, P4-01, P7-01 e decisão da biblioteca.
- **PRD:** FR-ART-002, FR-ART-003; BR-ART-001, BR-ART-002, BR-ART-003; NFR-006, AUD-006. **Aceite:** AC-006, AC-010, AC-014.
- **Arquitetura:** ADR-011; seções 14, 17, 28, 29, 33, 36, 37, 40 e 41.

## Propósito, baseline e blocker

Gerar DANFE/DANFSe como PDF derivado, versionado e regenerável sem afetar original. Jobs/objetos/documentos existem nas dependências; biblioteca exata está Open em arquitetura 29/45 e plano 21. O blocker atinge somente início desta implementação, não consulta, XML ou outras specs.

## Contrato e estado requerido

Independentemente da biblioteca, porta de renderer recebe bytes verificados + tipo/leiaute e retorna PDF/diagnóstico sem acesso a banco/rede fiscal. Artefatos é dono do PDF; Jobs, da execução. **Proposed:** registro derivado com documento pai, tipo, objeto/hash, renderer ID/versão, estado, tentativa, resultado e timestamps; constraint única por documento+renderer+versão+variante. Índices por pai/estado/renderer.

Mudança de renderer cria versão nova ou invalida anterior explicitamente, nunca sobrescreve original/PDF histórico. Chave de job usa documento+renderer+versão. Falha deixa `indisponível/falho`, XML segue consultável e usuário autorizado pode solicitar regeneração; requests concorrentes retornam job/artefato existente.

## UI, autorização e segurança

Todos os papéis podem baixar PDF autorizado; regeneração segue política indicada pelo PRD como “usuário autorizado”, **Proposed** inicialmente para todos que podem consultar o documento, sempre revalidada pelo worker. Tela detalhe mostra disponível/processando/falho e ação de regenerar. Parser/renderer roda com limite CPU/memória/tempo, sem rede, entidades externas ou escrita arbitrária. PDF/XML não entram em log; filename seguro.

## Auditoria, observabilidade e falhas

Auditar gerar/regenerar/download com renderer/versão e resultado, sem conteúdo. Métricas: fila/duração/falha por renderer/leiaute, duplicata evitada. Morte do worker recupera lease; saída incompleta não finaliza objeto; retry idempotente. Renderer desconhecido não invalida XML.

## Testes e aceite futuro

Após decisão, fixtures sintéticas: válido, assinado, cancelado, incompleto, desconhecido e campos ausentes; validar determinismo esperado pela biblioteca, versão, concorrência, timeout/memória, PDF interrompido, objeto ausente, RBAC e redaction.

- [ ] PDF é derivado e ligado ao original.
- [ ] Falha não oculta/invalida XML.
- [ ] Mesmo documento+renderer+versão não duplica equivalente.
- [ ] Regeneração é job autorizado, auditado e retomável.
- [ ] Renderer não possui rede nem acesso irrestrito.

DoD: registrar decisão do renderer, modelo, job, sandbox, UI, auditoria e testes. **Open/Blocked:** biblioteca e cobertura de leiautes; selecionar com evidência técnica local.
