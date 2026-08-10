# Consulta de documentos e download individual

## Metadados

- **Fase/status:** P7 — pronta após P4; cobertura completa cresce com P5/P6.
- **Backlog:** P7-01, P7-02. **Dependências:** P1-03/04, P4-01/04.
- **Implementação:** P7-01/P7-02 concluídos no issue 0015. A consulta usa filtros bounded,
  cursor opaco assinado e detalhe seguro; o download individual revalida artefato, digest e
  tamanho antes do streaming. PDF/DANFE/DANFSe continua no slice P7-03 bloqueado localmente.
- **PRD:** FR-DOC-001, FR-DOC-002, FR-DOC-003, FR-DOC-004, FR-DOC-005; BR-DOC-001, BR-DOC-002; FR-ART-001; NFR-001, NFR-002, NFR-006; AUD-006. **Aceite:** AC-004, AC-005, AC-010, AC-011, AC-014.
- **Arquitetura:** seções 14–18, 26–28, 32, 33, 36 e 37.

## Propósito e resultado

Oferecer acervo global pesquisável, detalhe padronizado e download do XML/payload primário finalizado. Consulta é somente leitura e não depende de PDF.

## Baseline, escopo e não escopo

P4 oferece modelo/lista mínima; P5/P6 populam categorias. Esta spec cria busca, filtros, paginação, detalhe/eventos e streaming seguro. Não inclui filtro por valor, CSV/Excel, relatórios, API pública, PDF ou ZIP.

## Dados, índices e contratos Proposed

Documentos permanece dono dos metadados; Artefatos, dos bytes. Adicionar apenas campos/índices indispensáveis: empresa+competência; emissão; família/direção/categoria; situação; identificadores; número; nomes normalizados disponíveis; disponibilidade de artefato. Estratégia de busca e paginação é **Proposed**; deve ser determinística, limitada e não exigir novo serviço.

Contrato de lista aceita exatamente empresa(s), competência, período de emissão, família, direção NF-e, categoria NFS-e, tipo de evento e busca global por campos PRD. Detalhe retorna empresa, identidade, número/série, partes, datas de emissão/autorização/evento, competência, valor, situação, fonte/coleta, vínculos e disponibilidade XML/PDF. Download recebe ID do artefato/documento, revalida permissão e transmite objeto verificado sem chave MinIO.

## UI e autorização

Rotas Proposed: acervo/lista e detalhe. Todos os três papéis autenticados veem todas as empresas e baixam individualmente; anônimo e sessão revogada são recusados. Tela oferece loading, vazio, erro/degradado, paginação, filtros persistidos na URL e evento relacionado. Não exibe ações administrativas por papel, mas servidor decide.

## Segurança, auditoria e observabilidade

Validar parâmetros, limites, ordenação allowlisted e evitar enumeração via respostas uniformes. `Content-Disposition` usa nome seguro; stream não loga conteúdo. Auditar consulta conforme política de volume definida localmente e todo download, com ator/IP/alvo/resultado/correlação. Métricas: latência/erros/zero resultados/download negado/objeto ausente.

## Falhas e testes

Objeto pendente/ausente/divergente não é servido e UI mantém metadado com indisponibilidade. Testar cada filtro isolado/combinado, busca multiempresa, datas/competência, Unicode, paginação estável, entrada/saída/tomada/prestada/evento, ausência de filtros proibidos, RBAC direto, stream interrompido, auditoria e browsers. Fixtures sintéticas.

## Aceite e DoD

- [ ] Todos e somente os filtros PRD funcionam.
- [ ] Detalhe preserva datas, competência, categoria e vínculos.
- [ ] Download revalida autorização e integridade no servidor.
- [ ] XML continua disponível quando PDF falha.
- [ ] Consulta não altera documento/cursor/artefato.

DoD: migrações/índices, contratos, UI, download, auditoria e matriz browser verdes. **Proposed:** URLs/payload/paginação e política de granularidade de auditoria de consultas.

## Notas de implementação — issue 0015

- `GET /api/documents` preserva os estados do contrato P4 e acrescenta empresa múltipla,
  competência, período de emissão, família, direção NF-e, categoria NFS-e, tipo de evento e
  busca global. O cursor de continuação é assinado e limitado ao identificador interno.
- `GET /api/documents/<id>` retorna metadados, eventos/substituições e disponibilidade de
  artefatos sem chaves de objeto ou payloads. `GET /api/documents/<id>/download` e
  `GET /api/artifacts/<id>/download` servem somente evidência finalizada e verificada.
- Consulta e download geram auditoria bounded. A verificação HTTP usa uma leitura não mutante;
  reconciliação continua sendo a dona das transições `missing`/`divergent` do artefato.
- O repositório não possui runner de browser; a validação de UI desta entrega é feita pelo
  contrato React compilado/lintado e pelos estados de detalhe/download, enquanto a cobertura
  HTTP/integridade/RBAC usa fixtures sintéticas.
