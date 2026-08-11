# Renderização de DANFE e DANFSe

## Metadados

- **Fase/status:** P7 — **implementada no issue 0023**; renderer pinado, worker, persistência,
  API, UI e evidência de conformidade entregues.
- **Backlog:** P7-03 concluído. **Dependências:** P3-01, P4-01 e P7-01; as dependências estão
  implementadas. Não há blocker local de renderer.
- **PRD:** FR-ART-002, FR-ART-003; BR-ART-001, BR-ART-002, BR-ART-003; NFR-006,
  AUD-006. **Aceite:** AC-006, AC-010, AC-014.
- **Arquitetura:** ADR-011; seções 14, 17, 20, 26–29, 33, 36, 37, 40 e 41.

## Decisão técnica aprovada

O renderer de P7-03 é [Engenere/BrazilFiscalReport](https://github.com/Engenere/BrazilFiscalReport),
integrado como biblioteca Python no worker do NFX:

| Representação | Módulo Python | Entrada canônica |
|---|---|---|
| DANFE de NF-e | `brazilfiscalreport.danfe` | XML fiscal original preservado |
| DANFSe Nacional/ADN | `brazilfiscalreport.danfse` | XML fiscal original preservado |

As referências de uso são a [documentação de DANFE](https://engenere.github.io/BrazilFiscalReport/danfe/)
e a [documentação de DANFSe](https://engenere.github.io/BrazilFiscalReport/danfse/). O runtime não
executa `bfrep` nem qualquer subprocess/shell. O CLI é ferramenta opcional de desenvolvimento ou
diagnóstico, fora do contrato de produção. A integração deve chamar diretamente a API Python; o
padrão hoje documentado é conceitualmente `Danfe(xml=...)` ou `Danfse(xml=...)` seguido da operação
de saída PDF. A assinatura e a forma de obter bytes devem ser confirmadas contra a versão concreta
pinada no issue de implementação, e não inferidas deste exemplo.

## Escopo e invariantes preservados

PDF é derivado: XML/payload oficial permanece o artefato fiscal primário, imutável e disponível
quando o PDF falha, é desconhecido ou é regenerado. P7-03 não cria transporte fiscal, coleta,
retenção, exclusão, armazenamento, auditoria, jobs ou idempotência paralelos; reutiliza os owners
canônicos de P3/P4/P7. Acesso, auditoria, retenção e exclusão do PDF seguem o documento pai.

Fluxo aprovado:

1. Usuário autorizado solicita DANFE ou DANFSe para um documento suportado; autorização é sempre
   server-side.
2. Se já existir artefato finalizado, íntegro e compatível com a identidade abaixo, ele é reutilizado.
3. Caso contrário, cria-se ou reutiliza-se o job persistente de renderização já canônico. O worker
   recupera o XML/payload original verificado do storage e chama a biblioteca em processo, sem rede
   fiscal e sem shell.
4. O worker somente declara sucesso depois de persistir os bytes PDF e confirmar hash, tamanho,
   MIME/tipo, documento pai, renderer e versão pelo contrato de artefatos existente.
5. Falha, timeout, morte do worker ou saída incompleta deixa o original intocado e produz somente o
   estado derivado seguro; lease/retry/recovery existentes retomam o job. Regeneração permitida cria
   ou reutiliza o mesmo trabalho e é auditada.

O PDF derivado registra `renderer_id = "brazilfiscalreport"` (ou o nome equivalente já adotado
uniformemente), `renderer_version` igual à versão efetivamente instalada e a representação
`danfe` ou `danfse`. A identidade/idempotência é documento lógico + tipo de PDF + representação +
`renderer_id` + `renderer_version`, pelos mecanismos canônicos existentes. Não sobrescrever uma
representação anterior: mudança de renderer ou versão cria identidade nova e preserva o histórico.

## Dependência, versão e licença

O issue 0023 adiciona ao runtime a versão concreta `BrazilFiscalReport[danfse]==1.0.1`, nunca
`latest`, intervalo aberto ou extra `cli`. DANFE é coberto pelo núcleo; para DANFSe foi usado apenas
o extra `danfse` realmente necessário à API (a documentação do projeto informa que ele traz
`qrcode`). A versão instalada deve ser lida/registrada no artefato e usada na chave de idempotência.

A fonte canônica de licença no repositório oficial — o arquivo
[LICENSE](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE) — é **GNU Lesser General
Public License v3.0 (LGPL-3.0)**; README e metadado `license` do
[PyPI](https://pypi.org/pypi/BrazilFiscalReport/json) também a identificam assim. **Observação
factual não bloqueante:** o classificador `License :: ... GNU Affero General Public License v3` no
`pyproject.toml` oficial e no PyPI é inconsistente com essas referências práticas. Isso não reabre
a decisão, nem condiciona spec, issues, implementação ou pinagem.

## Conformidade DANFSe Nacional/ADN — NT 008/2026 v1.02

A implementação e seus testes devem tomar como referência a [Nota Técnica nº 008, versão
1.02](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc/nt-008-se-cgnfse-danfse-20260714-v1-02.pdf),
sem copiar a nota inteira. Os itens abaixo são o recorte de implementação/aceite de P7-03.

### Obrigatório pela NT

- Gerar DANFSe v2.0 somente das informações presentes no XML da NFS-e; não inventar, enriquecer ou
  imprimir conteúdo externo. Campos podem quebrar em linhas apenas mantendo leitura clara.
- Produzir uma única página, em A4 mínimo (210 x 297 mm), retrato, com margens de 0,15 a 0,20 cm em
  todos os lados, contraste que permita ler o QR Code, borda de 1 pt e divisórias de 0,5 pt.
- Obedecer ao modelo do Anexo I e à disposição obrigatória dos blocos: identificação, prestador,
  tomador, destinatário, intermediário, serviço, ISSQN, tributação federal exceto CBS, IBS/CBS,
  totais e informações complementares; canhoto só quando escolhido. Mapear e testar os campos
  obrigatórios aplicáveis de cada bloco, inclusive identificação (chave de 50 dígitos, NFS-e, DPS,
  competência, emissão, emitente, situação e finalidade).
- Incluir IBS/CBS quando presente no XML, com CST/cClassTrib, operação/local, bases/reduções,
  alíquotas e valores IBS/CBS, e os totais `Total do IBS/CBS` e `Valor Líquido da NFS-e + IBS/CBS`.
  Cobrir o ajuste v1.02: se `tpRetPisCofins=1`, `Contribuições Sociais – Retidas` é a soma de
  `vRetCSLL` + `vPis` + `vCofins` e os campos próprios PIS/COFINS mostram `0,00`; nos demais
  casos, seguem os valores XML aplicáveis.
- Incluir QR Code com a URL nacional `https://www.nfse.gov.br/ConsultaPublica/?tpc=1&chave=<chave>`;
  testar conteúdo, decodificação e dimensão mínima de 1,52 cm. No cabeçalho, respeitar `DANFSe
  v2.0`, logomarca/títulos/ambiente e a indicação obrigatória de homologação `tpAmb=2`: “NFS-e SEM
  VALIDADE JURÍDICA”.
- Usar Arial para títulos/labels e Microsoft Sans Serif para conteúdo, preto sólido e espaçamento
  normal; mínimos: título de bloco 7 pt negrito/caixa alta, label de campo 6 pt negrito, labels de
  identificação 7 pt e conteúdo 7 pt. Respeitar ainda os sombreamentos obrigatórios do cabeçalho,
  títulos de bloco, emitente e valor líquido + IBS/CBS.
- Para cancelamento/substituição, usar respectivamente marca d’água diagonal `CANCELADA` ou
  `SUBSTITUÍDA`, Arial, cinza K35 e ao menos 50 pt, quando aplicável ao XML. Informações
  complementares devem preservar a ordem/itens aplicáveis, inclusive referência de NFS-e
  substituída, obra/imóvel/evento/documento técnico, pedido e totais aproximados de tributos;
  campos sem informação XML são preenchidos com `-` conforme a NT.

### Permitido ou recomendação da NT, não requisito adicional do NFX

- As dimensões/posições e quantidades de caracteres do item 2.4.5 são sugestivas, não um limite
  rígido; se o campo não comportar o texto, usar reticências conforme a NT, preservando o modelo e
  os mínimos de fonte.
- Podem ser suprimidos os blocos de tomador, destinatário, intermediário e ISSQN quando não
  preenchidos/não aplicáveis, com o texto prescrito e redistribuição de espaço somente para descrição
  do serviço e/ou informações complementares. Destinatário igual ao tomador pode usar o texto
  prescrito. Canhoto é opcional e sua ausência pode ampliar apenas os blocos permitidos.
- Papel diverso de jornal e a impressão em uma única via são regras de impressão da NT; no NFX o
  produto é PDF, mas a renderização deve manter o contraste e a geometria que viabilizam essa
  impressão.

### Comportamento próprio do renderer, sujeito à validação

Seleção de fonte substituta métrica, configuração de margens/precisão, marcas d’água auxiliares,
quebra de linhas e a própria técnica de geração são comportamentos do BrazilFiscalReport, não
substituem a NT. A implementação deve fixar uma configuração que cumpra a NT e provar o resultado
com fixtures; não tratar configuração default ou “PDF gerado” como prova de conformidade.

## Segurança, auditoria, operações e aceite

Todos os papéis que já podem baixar o documento podem baixar PDF autorizado; a política atual de
regeneração é a dos usuários autorizados a consultar o documento, revalidada pelo worker. Não logar
XML, payload, PDF, chave de objeto, PFX ou exceção externa crua. Auditar solicitação, deduplicação,
início, sucesso, falha, regeneração e download com IDs seguros, representação, renderer/versão,
resultado e correlação. Métricas incluem fila, duração, falha e deduplicação por renderer e
representação.

O issue deve adicionar fixtures estritamente sintéticas/anonimizadas e testes que comprovem, além
da geração de PDF:

- DANFE NF-e válido/assinado, cancelado, incompleto, desconhecido e campos ausentes; DANFSe
  Nacional/ADN válido, homologação, cancelamento, substituição, campos opcionais/supressões e
  IBS/CBS, incluindo `vPis`/`vCofins`/`tpRetPisCofins` v1.02;
- uma página A4 retrato, margens, fontes/tamanhos mínimos, blocos e campos aplicáveis, QR
  decodificável com URL/chave correta, indicação de homologação, marcação de situação e ausência de
  conteúdo não presente no XML;
- pin/versionamento, identidade/idempotência, concorrência, reuso, nova versão do renderer,
  persistência/hash/tamanho, PDF interrompido/ausente/divergente, timeout/limites e recovery;
- RBAC/revalidação no worker, auditoria/redaction, XML disponível em toda falha do PDF e herança de
  retenção/exclusão pelo pai.

### Critérios de aceite

- [x] DANFE e DANFSe são artefatos derivados versionados e ligados ao original, gerados pela API
  Python do BrazilFiscalReport no worker, sem CLI/subprocess em runtime.
- [x] Um artefato íntegro equivalente é reutilizado; mesma identidade não duplica PDF, e mudança de
  renderer/versão não sobrescreve o histórico.
- [x] Sucesso só ocorre após objeto e metadados verificados; falha nunca oculta, invalida ou remove
  XML/payload original; regeneração é auditada, autorizada e recuperável.
- [x] Fixtures e testes demonstram as regras relevantes da NT 008/2026 v1.02, não apenas que o PDF
  abriu.
- [x] Runtime usa versão pinada e extra mínimo; `renderer_id`, `renderer_version` e representação
  são persistidos na identidade do artefato derivado.

DoD: concluído no issue 0023 com os owners existentes de P3/P4/P7, UI de disponibilidade e
regeneração, auditoria/métricas, testes de conformidade e recovery. Não há blocker local de
renderer.

## Implementação e evidência — issue 0023

- `requirements.txt` fixa `BrazilFiscalReport[danfse]==1.0.1`; `renderer_metadata()` rejeita
  ausência ou divergência da versão instalada e expõe somente ID, versão e representação.
- `DocumentRender` e a migração `0019_document_render` separam XML original e PDF derivado,
  preservam versões históricas e impõem a identidade completa e MIME PDF. `request_render()` usa
  a autorização existente, escolhe a representação pela família, verifica a evidência XML e
  enfileira `document.render_pdf` idempotentemente.
- `render_pdf_job()` usa o `ArtifactStorageService`, chama `Danfe`/`Danfse` em processo, aplica os
  parâmetros DANFSe da NT e a regra `tpRetPisCofins=1`, e finaliza apenas após hash, tamanho, MIME
  e integridade PDF verificados. Falhas classificam apenas o derivado e preservam o XML.
- Rotas, status/lista, detalhe, download e UI expõem estados seguros; auditoria e métricas cobrem
  solicitação, negação, reuso, fila, início, sucesso, falha, regeneração e download. A capacidade
  de rendering do dashboard/health deixa de ser falsamente `unavailable` quando a versão está
  instalada.
- `tests/unit/test_document_rendering.py` usa fixtures sintéticas NF-e/NFS-e. A fixture NFS-e
  verifica A4 retrato em uma página, homologação, blocos/IBS-CBS, regra de retenção, URL e tamanho
  do QR, e marcas de cancelamento/substituição; a fixture NF-e verifica a chamada real do DANFE.
  O teste de persistência cobre reuso, job durável, autorização do worker, vínculo ao original e
  hash final.

Validação final e comandos executados ficam registrados na resolução do issue 0023 e no commit
focado desta passagem. A implementação não habilita transporte fiscal, CLI, exclusão, retenção
paralela, backup ou homologação externa.
