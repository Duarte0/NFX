# Experiência de empresas, certificados e coletas

## Metadados

- **Fase/status/versão:** P10-05 — implementação concluída e verificada no issue 0038 — v1.1.
- **Dependências:** P10-01, P10-02; specs P2, P3-05, P5 e P6.
- **Fontes:** PRD FR-COMP-001..005, FR-CERT-001..004, FR-COLL-001..005, NFR-008..012, AC-001/002/018/019/026; Plano P10-05.

## Objetivo e limites

Modernizar cadastro/ciclo de vida de empresas, certificado A1, cobertura e controle de coletas. Não altera owners de estado, transições, cursor/NSU, envelope criptográfico, confirmação de ação administrativa, jobs, adapters nem contratos HTTP.

## Estado atual, regras e contratos preservados

Empresas e certificados permanecem visíveis/gerenciáveis apenas pelos papéis atuais; Coletas preserva seus controles por papel. A UI deve distinguir empresa ativa/inativa, enriquecimento público não autoritativo, certificado ausente/válido/próximo do vencimento/expirado, cobertura ADN ausente, coleta pendente/em execução/parcial/falha/bloqueio e indisponibilidade transitória. Ausência de cobertura, erro transitório e bloqueio de política não podem compartilhar texto ou cor sem rótulo semântico.

Criação, edição, ativação/desativação, pausa/habilitação de fluxo, enriquecimento, upload/substituição de certificado, solicitação e retry de coleta mantêm payload, confirmação/motivo quando existente, feedback seguro e estado durável retornado pelo owner. A proteção contra duplo envio é de interação: não inventa sucesso nem substitui idempotência/reexecução do servidor. Filtros/drill-down de empresa, certificado e execução continuam URL-endereçáveis, allowlisted e reconciliados pelos owners canônicos. A seção/certificado deve fornecer o destino único `#certificados` definido em P10-02.

## Segurança, observabilidade e validação

Nunca exibir certificado, senha, chave, payload de adapter, CNPJ de fixture real ou detalhe interno de falha. Preservar auditoria e métricas existentes sem criar escrita em leitura. Testar matriz RBAC/acesso direto, transições permitidas/recusadas, confirmação/repetição/reload, cada estado acima, cobertura ausente versus erro, filtros/deep links, falha de rede e TypeScript/lint/build com dados sintéticos.

## Aceite

- [x] Estados de empresa, certificado e coleta são claros e não confundem ausência, bloqueio e erro.
- [x] Mutação preserva confirmação, autorização, auditoria e idempotência do servidor.
- [x] Filtros e drill-downs permanecem canônicos e sem cálculo local de domínio.
- [x] Nenhum segredo ou detalhe fiscal indevido é apresentado.

## Evidência de implementação e validação

O issue 0038 modernizou `CompaniesSection`, `CertificateInventoryPanel`, `CertificatePanel` e
`CollectionsSection` usando os primitives P10-01. A apresentação mantém os estados owner-provided,
filtros/deep links allowlisted, totais/limites/truncamento e cursor opaco; conserva a última leitura
segura durante refresh/erro; e protege leituras, listeners e mutações contra respostas fora de ordem
ou cliques repetidos. Certificados e enriquecimento renderizam somente metadados seguros, enquanto
as ações continuam usando as APIs, confirmações, motivos, versões e autorização existentes. O
contrato UI e o fixture sintético cobrem os papéis autenticados, sessões negativas, foco, overflow,
stale/error/retry, cobertura, execução, cursor e redaction.

Validação executada no issue 0038:

- `npm --prefix frontend run test:ui-contract` — passou.
- `npm --prefix frontend run lint` e `npm --prefix frontend run build` — passaram.
- `make test-browser` após reconstruir a imagem efêmera `browser-tests` — 180/180 passaram em
  Chrome, Firefox e Edge nas larguras 1024, 1280 e 1440 px.
- `make lint`, `make test-unit`, `make build` e `make smoke` — passaram.

Não houve mudança de backend, endpoint, payload HTTP, dependência ou migration. O Graphify foi
atualizado pelo workflow do repositório.
