# PRD — NFX INOV

## 1. Controle do documento

| Campo | Valor |
|---|---|
| Produto | NFX INOV |
| Organização | INOV Contabilidade |
| Tipo | Aplicação web interna |
| Versão | 1.0 — MVP |
| Status | Proposto para aprovação |
| Idioma da interface | Português brasileiro |
| Fuso horário | Brasília |
| Público inicial | Guilherme, equipe fiscal e sócios da INOV |
| Escala de referência | Aproximadamente 200 empresas em dois anos |
| Plataforma inicial | Implantação local com Docker |

Este documento define o produto e seu comportamento esperado. Não define arquitetura detalhada, topologia de containers, banco de dados, migrações, contratos de API ou tarefas de implementação.

## 2. Resumo executivo

O NFX INOV será a plataforma interna da INOV para cadastrar empresas e certificados digitais A1, coletar documentos fiscais eletrônicos disponibilizados pelos serviços oficiais, organizá-los por empresa e competência, consultar seus dados, gerar representações fiscais em PDF e permitir downloads individuais ou em lote com controle e auditoria.

O MVP atenderá Administradores, Operadores e Visualizadores. Todos os usuários autenticados poderão consultar todas as empresas cadastradas, mas cada ação será limitada ao papel do usuário. O sistema priorizará integridade fiscal, recuperação segura e rastreabilidade sobre velocidade máxima de coleta.

Para NFS-e, o MVP cobrirá exclusivamente o Portal Nacional da NFS-e/ADN. Municípios que não disponibilizarem seus documentos por esse padrão ficarão fora da cobertura automática, e essa limitação deverá ser visível aos usuários.

## 3. Visão do produto

Oferecer à INOV uma fonte interna, confiável e auditável para acompanhar documentos fiscais de suas empresas, reduzindo trabalho manual, evitando perda ou duplicidade de documentos e tornando claras as situações de coleta, disponibilidade, processamento, retenção e exportação.

## 4. Problema

A equipe fiscal precisa acompanhar múltiplas empresas, certificados, fontes fiscais, competências, eventos e artefatos XML/PDF. Sem uma visão centralizada, há risco de lacunas de coleta, repetição de documentos, dificuldade para identificar bloqueios, exposição de dados sensíveis e ausência de evidência sobre quem consultou, baixou ou excluiu informações.

## 5. Objetivos

- Registrar e manter cerca de 200 empresas, seus certificados A1 e estados independentes de coleta de NF-e e NFS-e.
- Coletar automaticamente a história ainda disponibilizada pelas fontes oficiais e continuar coletando 24 horas por dia, respeitando suas regras vigentes.
- Preservar documentos, eventos, payloads originais, cursores e histórico de execução sem perda por retry, reinício ou substituição de certificado.
- Permitir consulta, filtros, detalhamento, download XML e geração/fornecimento de DANFE e DANFSe.
- Permitir exportações ZIP assíncronas, auditadas e com controle de acesso.
- Tornar visíveis falhas, atrasos, bloqueios, certificados e saúde operacional.
- Aplicar retenção e exclusão administrativa somente quando permitidas.

## 6. Não objetivos

Não fazem parte do MVP: operação SaaS ou multiempresa contábil; portal para clientes; acesso externo à aplicação; interface mobile ou aplicativo mobile; integrações com Domínio, Acessórias ou outros sistemas contábeis; migração de dados legados; upload manual de XML; notificações; recuperação de senha por e-mail; 2FA; exportação Excel/CSV; relatórios especializados; filtro por faixa de valores; exclusão automática; restrição de empresas por usuário; API pública; integração direta com sistemas municipais de NFS-e fora do Portal Nacional/ADN.

## 7. Usuários e papéis

### 7.1 Administrador

Pode gerenciar usuários, empresas, certificados, fluxos de coleta, documentos, exportações, auditoria completa, retenção e exclusão elegível, configurações operacionais, status de backup e informações técnicas de saúde.

### 7.2 Operador

Pode gerenciar empresas e certificados, ativar ou desativar empresas, pausar ou habilitar fluxos, iniciar coletas completa/NF-e/NFS-e, repetir coletas falhas, consultar documentos, baixar documentos individuais e solicitar ZIPs. Não pode gerenciar usuários, alterar papéis, acessar a auditoria administrativa completa, excluir documentos ou acessar configurações restritas e administração de backups.

### 7.3 Visualizador

Pode consultar documentos, baixar documentos individuais e solicitar exportações em lote permitidas. Não pode gerenciar usuários, empresas, certificados, coletas, retenção, exclusão, backups ou configurações operacionais.

### 7.4 Regra global

Todos os usuários autenticados podem acessar todas as empresas registradas. Não existe segregação de empresas por carteira, departamento, time ou usuário no MVP. A autorização é por ação e papel.

## 8. Escopo do MVP

O MVP compreende autenticação por e-mail e senha, administração de usuários, cadastro e ciclo de vida de empresas, certificados A1 `.pfx`, coleta de NF-e recebida e emitida e eventos suportados, coleta de NFS-e tomada e prestada e eventos pelo Portal Nacional/ADN, organização por competência, consulta e busca global, XML, DANFE/DANFSe, ZIP assíncrono, dashboard, auditoria permanente, retenção, exclusão manual elegível, backup, recuperação e saúde operacional.

## 9. Requisitos funcionais e regras de negócio

### 9.1 Usuários, autenticação e autorização

- **FR-AUTH-001** — O sistema deve autenticar usuário por e-mail e senha e permitir acesso somente a usuário ativo com credenciais válidas.
- **FR-AUTH-002** — Somente Administrador pode criar usuário informando nome, e-mail, papel e senha inicial.
- **BR-AUTH-001** — A senha inicial não exige troca no primeiro login; o usuário pode alterá-la voluntariamente.
- **FR-AUTH-003** — Somente Administrador pode redefinir a senha de outro usuário; recuperação por e-mail não existe no MVP.
- **FR-AUTH-004** — O sistema deve permitir ativar e desativar usuários e alterar seus papéis somente a Administradores.
- **BR-AUTH-002** — A desativação deve bloquear imediatamente novo acesso e terminar todas as sessões ativas do usuário, preservando seu histórico de auditoria.
- **FR-AUTH-005** — O primeiro Administrador deve ser criado na instalação usando o e-mail `guilherme.duarte@inovssc.com.br`; a senha deve vir de segredo seguro de instalação e ser armazenada apenas como hash.
- **FR-AUTH-006** — O sistema deve encerrar a sessão após 30 minutos de inatividade e permitir nova autenticação.
- **FR-AUTH-007** — O sistema deve aplicar proteção contra tentativas repetidas de login, sem revelar se um e-mail existe.

### 9.2 Empresas

- **FR-COMP-001** — Administradores e Operadores devem cadastrar empresa com CNPJ e razão social obrigatórios.
- **BR-COMP-001** — O CNPJ deve ser normalizado para comparação, validado conforme formato vigente e não pode ser duplicado; a mensagem de duplicidade deve informar claramente que já existe empresa com aquele CNPJ.
- **BR-COMP-002** — Após a primeira coleta de documentos, o CNPJ torna-se imutável; razão social e dados complementares não-chave continuam editáveis.
- **FR-COMP-002** — Administradores e Operadores devem visualizar e editar empresas, ativá-las e desativá-las.
- **BR-COMP-003** — Empresa não pode ser excluída diretamente. Desativação não remove documentos, cursores, histórico ou downloads.
- **BR-COMP-004** — Empresa desativada não executa coletas automáticas; ao ser reativada, retoma do estado persistido anterior.
- **FR-COMP-003** — O sistema deve permitir habilitar e pausar separadamente os fluxos NF-e e NFS-e enquanto a empresa estiver ativa.
- **BR-COMP-005** — Concluir cadastro com certificado válido ativa automaticamente a coleta inicial.
- **BR-COMP-006** — Desativação de empresa exige confirmação explícita e motivo obrigatório.

### 9.3 Enriquecimento OpenCNPJ

- **FR-COMP-004** — O sistema pode consultar dados públicos do OpenCNPJ enviando somente o CNPJ e deve manter esses dados separados e identificados como enriquecimento público não autoritativo.
- **BR-COMP-007** — Falha, indisponibilidade ou ausência de dados do OpenCNPJ não pode impedir cadastro, coleta ou correção fiscal.
- **FR-COMP-005** — O sistema pode atualizar o enriquecimento posteriormente e deve considerar a futura transição para CNPJ alfanumérico.
- **BR-COMP-008** — Implantação ou hospedagem própria do OpenCNPJ não é requisito obrigatório do MVP.

### 9.4 Certificados

- **FR-CERT-001** — Administradores e Operadores devem incluir ou substituir o certificado corrente de uma empresa, informando arquivo `.pfx` e sua senha.
- **BR-CERT-001** — A relação é estritamente um certificado corrente por empresa e um certificado não pode ser compartilhado entre empresas.
- **FR-CERT-002** — O sistema deve validar formato, senha, legibilidade, datas de validade, CNPJ contido e correspondência exata com a empresa.
- **BR-CERT-002** — Em CNPJ incompatível, a associação deve ser bloqueada e explicar o motivo.
- **BR-CERT-003** — Certificado expirado, inválido, ilegível ou com senha incorreta deve bloquear a coleta.
- **BR-CERT-004** — Certificado com 30 dias ou menos restantes deve aparecer como próximo do vencimento; certificado expirado deve aparecer separadamente.
- **BR-CERT-005** — Substituição preserva documentos, estado fiscal, histórico de coletas e auditoria anteriores.
- **BR-CERT-006** — Enquanto houver falha permanente do certificado, não devem ocorrer retries repetidos contra o serviço fiscal; após correção ou substituição, a coleta pode ser retomada.
- **BR-CERT-007** — O arquivo do certificado e sua senha devem permanecer criptografados em repouso; a senha nunca pode constar em logs, auditoria, respostas, código-fonte ou configuração versionada.

### 9.5 Coleta geral

- **FR-COLL-001** — Ao existir empresa ativa e certificado válido, o sistema deve iniciar automaticamente a coleta inicial.
- **BR-COLL-001** — Coleta inicial tenta recuperar toda a história ainda disponibilizada por cada fonte oficial e exibe cobertura obtida e limitações oficiais conhecidas.
- **BR-COLL-002** — Limites, intervalos, cooldowns e regras de consumo oficiais devem ser configuráveis ou revalidáveis e não podem ser tratados como constantes imutáveis do produto.
- **FR-COLL-002** — O sistema deve executar coleta automática 24 horas por dia, respeitando limites, intervalos, cooldowns, consumo, disponibilidade e sequenciamento oficiais.
- **BR-COLL-003** — Administradores e Operadores podem iniciar coleta completa, somente NF-e ou somente NFS-e, respeitando bloqueios e cooldowns oficiais.
- **BR-COLL-004** — Administradores e Operadores podem repetir execuções falhas quando o bloqueio permitir.
- **BR-COLL-005** — Não podem existir duas execuções ativas para a mesma empresa e o mesmo fluxo; requisição duplicada deve informar que já existe execução ativa.
- **BR-COLL-006** — Uma consulta válida e concluída à fonte, sem documentos disponibilizados naquela consulta, deve terminar com sucesso e a mensagem “Nenhum documento encontrado”; essa mensagem não confirma ausência de movimento fiscal fora da cobertura ou disponibilidade da fonte consultada.
- **BR-COLL-007** — Falhas temporárias devem usar retry automático com intervalos progressivos seguros; falhas permanentes de certificado suspendem retry até correção.
- **BR-COLL-008** — Cada empresa deve manter estado independente para NF-e e NFS-e, incluindo tentativa, sucesso, próximo agendamento, erro, bloqueio, cooldown e progresso.
- **BR-COLL-009** — O produto deve distinguir execução concluída, vazia, parcial, em retry, bloqueada e falha.
- **BR-COLL-010** — Reinício de processo ou servidor deve permitir retomar com segurança a partir de estado persistido.

### 9.6 NF-e

- **FR-NFE-001** — Coletar NF-e recebida/entrada, emitida/saída e eventos fiscais disponibilizados pelos serviços oficiais suportados.
- **BR-NFE-001** — Entrada e saída são categorias distintas, e o papel da empresa no documento deve ser preservado.
- **FR-NFE-002** — Executar Ciência da Operação quando necessária para obtenção do XML completo, preservando manifestação e resultado.
- **FR-NFE-003** — Recuperar e preservar XML completo autorizado quando disponível, além de representar explicitamente resumo, documento completo e eventos.
- **FR-NFE-004** — Vincular evento aplicável à NF-e principal e exibir situações fornecidas pela fonte, incluindo autorizado, cancelado, denegado, inutilizado, corrigido e outras suportadas.
- **BR-NFE-002** — Fluxos, endpoints, NSUs, cursores, consumo e sequenciamento devem ser tratados conforme cada fluxo oficial aplicável; o produto não pode assumir mecanismo único.
- **BR-NFE-003** — Manifestação e armazenamento devem ser idempotentes; repetição não pode duplicar manifestação, documento, evento ou progresso.

### 9.7 NFS-e

- **FR-NFSE-001** — No MVP, coletar exclusivamente pelo Portal Nacional da NFS-e/ADN, conforme disponibilidade oficial para a empresa.
- **BR-NFSE-001** — A cobertura inclui NFS-e tomada/recebida, prestada/emitida e eventos, substituições, cancelamentos e demais tipos suportados pelo ADN.
- **BR-NFSE-002** — Empresas de municípios sem cobertura no Portal Nacional/ADN devem permanecer cadastráveis, mas a ausência de cobertura automática deve ser visível e não pode ser confundida com consulta válida vazia, indisponibilidade transitória da fonte ou sucesso de coleta.
- **FR-NFSE-002** — Classificar explicitamente documentos tomados, prestados e eventos, vinculando eventos e substituições ao principal quando houver identificadores suficientes.
- **FR-NFSE-003** — Preservar payloads originais necessários à rastreabilidade e tornar desconhecidos ou não suportados visíveis para análise controlada.
- **BR-NFSE-003** — Falha de classificação, renderização ou suporte não pode descartar o payload original nem marcar processamento como sucesso completo.

### 9.8 Integridade fiscal e idempotência

- **BR-INT-001** — Cada documento lógico deve possuir identidade fiscal única no contexto aplicável, baseada nos identificadores oficiais disponíveis e na empresa/fluxo quando necessário.
- **BR-INT-002** — Colisões de identidade, divergências de conteúdo ou identificadores conflitantes devem gerar estado explícito de conflito para análise, nunca sobrescrita silenciosa.
- **BR-INT-003** — O progresso só pode avançar após armazenamento durável do payload ou tratamento explícito e auditável da unidade recebida.
- **BR-INT-004** — Cursores e estados de empresa/fluxo devem ser independentes, persistentes e recuperáveis; nenhuma execução pode avançar de modo a perder item não armazenado.
- **BR-INT-005** — O sistema deve prevenir duplicidade em retries e replay e preservar hash de conteúdo quando aplicável para detectar alteração, repetição e integridade.
- **BR-INT-006** — Cada documento deve ser rastreável à fonte, identificador original e execução de coleta que o recebeu.
- **BR-INT-007** — Documento principal, eventos, XMLs, PDFs e artefatos derivados devem manter relacionamentos explícitos.
- **BR-INT-008** — Conteúdo original nunca deve ser substituído por representação derivada; payload malformado, desconhecido, duplicado ou conflitante deve permanecer visível em estado controlado.

### 9.9 Organização, consulta e filtros

- **FR-DOC-001** — Organizar documentos por empresa e competência derivada da data de emissão; data de coleta nunca define competência.
- **BR-DOC-001** — Preservar data de autorização separadamente e manter a data relevante de eventos sem alterar a competência do documento principal.
- **FR-DOC-002** — Exibir detalhes padronizados com empresa, família/categoria, chave ou identificador oficial, número, série, emissor, destinatário/tomador/prestador, CNPJ/CPF quando aplicável, emissão, autorização, competência, valor total, situação fiscal, fonte, coleta, eventos relacionados e disponibilidade de XML/PDF.
- **FR-DOC-003** — Permitir busca global por chave/identificador, CNPJ, razão social, número e nome do emissor ou destinatário quando disponível.
- **FR-DOC-004** — Oferecer filtros por empresa, competência, período de emissão, família NF-e/NFS-e, direção NF-e, categoria NFS-e e tipo de evento aplicável.
- **BR-DOC-002** — Não oferecer filtro por faixa de valor nem exportação Excel/CSV no MVP.
- **FR-DOC-005** — Exibir NF-e como entrada/recebida ou saída/emitida e NFS-e como tomada, prestada ou evento.

### 9.10 XML, DANFE e DANFSe

- **FR-ART-001** — O XML ou payload fiscal oficial equivalente deve ser o artefato fiscal primário e permitir download individual autorizado.
- **FR-ART-002** — Disponibilizar ou gerar DANFE para NF-e e DANFSe para NFS-e suportadas.
- **BR-ART-001** — PDF é artefato derivado vinculado ao documento original; falha de geração não oculta, invalida ou remove XML/payload.
- **FR-ART-003** — Usuário autorizado pode solicitar nova geração quando o PDF falhar.
- **BR-ART-002** — Registrar identidade de renderer/versão para reprodução ou invalidação e evitar PDFs equivalentes duplicados para o mesmo documento e versão.
- **BR-ART-003** — PDFs seguem acesso, auditoria, retenção e exclusão do documento pai.

### 9.11 Exportação ZIP

- **FR-ZIP-001** — Usuários autorizados podem solicitar ZIP após aplicar filtros, incluindo uma ou várias empresas.
- **FR-ZIP-002** — Exportações grandes devem ser assíncronas e registrar solicitante, filtros, quantidade de documentos e arquivos, tamanho, status, criação, expiração e resultado.
- **BR-ZIP-001** — ZIP fica disponível por 24 horas; sua exclusão automática não pode remover documentos, XMLs, PDFs, eventos ou registros fiscais de origem.
- **BR-ZIP-002** — Somente solicitante e Administradores podem baixar o ZIP; Operadores e Visualizadores não acessam ZIP de terceiros.
- **FR-ZIP-003** — Auditar solicitação e download.
- **BR-ZIP-003** — Usar nomes determinísticos e seguros para filesystem, com a estrutura: `empresa/competência/nfe/entradas/`, `empresa/competência/nfe/saidas/`, `empresa/competência/nfse/tomados/`, `empresa/competência/nfse/prestados/` e `empresa/competência/nfse/eventos/`.
- **BR-ZIP-004** — Falhas parciais de artefatos devem ser declaradas no status e resultado; o ZIP não pode afirmar completude silenciosamente.

### 9.12 Dashboard

- **FR-DASH-001** — Exibir empresas ativas/inativas, total de documentos, quantidades e valores no período, repartições NF-e/NFS-e, entrada/saída, tomada/prestada, certificados, vencidos, próximos do vencimento, coletas recentes/em execução, processamento pendente, falhas, bloqueios e atrasos.
- **FR-DASH-002** — Permitir selecionar período e comparar suas quantidades e valores com o período imediatamente anterior de mesma duração, usando limites temporais consecutivos e sem sobreposição.
- **FR-DASH-003** — Cada indicador clicável deve abrir a listagem correspondente com filtros já aplicados.
- **FR-OPS-001** — Administradores devem visualizar saúde operacional: espaço em disco, disponibilidade de banco e armazenamento fiscal, atrasos/falhas de coleta, falha/atraso de backup e serviços relevantes.
- **BR-OPS-001** — Detalhes técnicos e de backup são restritos a Administradores.
- **BR-DASH-001** — Não há notificações nem relatórios especializados no MVP.

## 10. Ciclo de vida de empresa

Estados funcionais: cadastrada, ativa, desativada e ativa com fluxos individuais habilitados/pausados. O cadastro exige CNPJ e razão social. Certificado válido concluindo o cadastro inicia a coleta. A primeira coleta torna o CNPJ imutável. Desativação exige motivo, interrompe apenas coletas automáticas e preserva todo o acervo e estado. Reativação retoma os estados persistidos. A ausência, expiração ou invalidez do certificado bloqueia os fluxos correspondentes, mas não desativa a empresa nem apaga documentos.

## 11. Ciclo de vida de certificado

Estados funcionais: ausente, válido, próximo do vencimento, expirado, inválido, ilegível, senha incorreta ou incompatível. Inclusão e substituição exigem validação completa antes de ativar o certificado. A substituição troca apenas o certificado corrente, preservando o acervo e o estado fiscal. Material secreto deve ser criptografado em repouso e nunca aparecer em telas administrativas, logs, auditoria, respostas, código ou backups em plaintext.

## 12. Autenticação e autorização

### Requisitos de segurança

- **SEC-001** — Armazenar somente hashes de senha adequados; nunca armazenar ou exibir senha em plaintext.
- **SEC-002** — Proteger contra força bruta, enumeração de usuários e reutilização indevida de sessão.
- **SEC-003** — Sessões devem usar cookies seguros, `HttpOnly`, `SameSite` apropriado, transporte HTTPS e expiração por inatividade de 30 minutos.
- **SEC-004** — Desativação de usuário revoga imediatamente suas sessões.
- **SEC-005** — Aplicar autorização no servidor para cada operação, inclusive downloads e jobs assíncronos.
- **SEC-006** — HTTPS é obrigatório na rede interna; proteger credenciais, certificados, documentos, sessões e downloads em trânsito.
- **SEC-007** — Não registrar segredos em logs, erros, auditoria, respostas, exemplos, configuração versionada ou PRD.
- **SEC-008** — Restringir a aplicação à rede interna da INOV, sem tratar essa rede como controle de segurança suficiente; permitir somente saídas necessárias para fontes fiscais e OpenCNPJ aprovado.

## 13. Retenção e exclusão

- **RET-001** — Reter XML de NF-e por 132 meses completos contados da data de autorização. Uma NF-e autorizada em 15/08/2026 torna-se elegível para exclusão em 15/08/2037, após completar os 132 meses.
- **RET-002** — Calcular a retenção da NFS-e pelo ano da data de emissão: o documento permanece retido durante o ano de emissão e durante os cinco anos-calendário seguintes, tornando-se elegível em 1º de janeiro do sexto ano seguinte. Uma NFS-e emitida em qualquer data de 2026 permanece retida em 2026 e de 2027 a 2031, tornando-se elegível em 01/01/2032.
- **RET-003** — Bloquear exclusão durante o prazo de retenção, inclusive para Administradores.
- **RET-004** — Após o prazo, marcar o documento como elegível para exclusão manual; nunca excluir automaticamente.
- **RET-005** — Somente Administrador pode excluir documentos elegíveis, após visualizar exatamente documentos e artefatos, confirmar explicitamente e fornecer motivo.
- **RET-006** — Excluir ou tratar consistentemente XML, PDFs, eventos e derivados relacionados, sem deixar artefatos órfãos ou registros enganosos.
- **RET-007** — Empresa desativada, usuário desativado, certificado expirado ou substituído não altera retenção.
- **RET-008** — A auditoria da exclusão permanece sem armazenar o conteúdo fiscal excluído no payload de auditoria.

A regra deve ser validada como atividade de compliance antes da operação produtiva, sem alterar o requisito de produto confirmado.

## 14. Auditoria

- **AUD-001** — Manter histórico permanente, append-only e imutável por operações normais; nem Administrador pode editar ou excluir.
- **AUD-002** — Auditar login, logout e autenticações bem-sucedidas/falhas com identidade, data/hora, IP e resultado.
- **AUD-003** — Auditar criação/edição, ativação/desativação de usuários, alteração de papel e reset de senha.
- **AUD-004** — Auditar criação/edição, ativação/desativação de empresas e inclusão/substituição de certificados sem segredos.
- **AUD-005** — Auditar início, conclusão, retry, bloqueio, falha e reprocessamento de coleta.
- **AUD-006** — Auditar consultas, downloads individuais, solicitações/downloads ZIP, geração/regeneração de PDF e exclusões elegíveis.
- **AUD-007** — Auditar alterações administrativas relevantes.
- **AUD-008** — Cada evento deve registrar, quando aplicável, ator, data/hora Brasília, IP, ação, entidade afetada, resultado, motivo e contexto seguro antes/depois.
- **AUD-009** — Exigir motivo para desativar empresa ou usuário, resetar senha, alterar papel e excluir documento.
- **AUD-010** — Exibir auditoria completa somente a Administradores; demais usuários veem apenas o resultado operacional permitido pela sua função.

## 15. Backup e recuperação

- **OPS-BKP-001** — Executar backup diário do banco, documentos fiscais/PDFs e material de certificado criptografado.
- **OPS-BKP-002** — Armazenar cópias separadas do servidor primário, com acesso físico e lógico restrito.
- **OPS-BKP-003** — Reter as 7 cópias diárias, 4 semanais e 12 mensais mais recentes.
- **OPS-BKP-004** — Manter procedimento manual de recuperação documentado para operador autorizado, incluindo data, escopo, resultado e falhas quando exercitado.
- **OPS-BKP-005** — Exibir para Administradores o último backup bem-sucedido e falhas/atrasos.
- **OPS-BKP-006** — Recuperação após falha do servidor primário deve ser possível até o próximo dia útil, preservando o máximo de dados duráveis possível.
- **BR-BKP-001** — Retenção operacional de backup é independente da retenção fiscal; expirar backup não exclui documento do acervo vivo.
- **SEC-009** — Backup não pode expor senhas em plaintext; criptografia integral do arquivo de backup não é requisito do MVP, sem reduzir as proteções de segredos armazenados pela aplicação.

## 16. Requisitos operacionais e observabilidade

- **OPS-001** — Coletores continuam operando sem usuário conectado.
- **OPS-002** — Exibir saúde de armazenamento fiscal, banco, espaço em disco, serviços externos, processamento, coletas e backups.
- **OPS-003** — Persistir todo progresso necessário; nenhum avanço fiscal pode depender apenas de memória volátil.
- **OPS-004** — Tornar visíveis falhas, cooldowns, bloqueios, atrasos, payloads desconhecidos e pendências de renderização.
- **OPS-005** — Após reinício, impedir concorrência indevida e retomar ou reprocessar com idempotência.
- **OPS-006** — Permitir configuração/revalidação de limites e intervalos oficiais sem transformá-los em constantes imutáveis do produto.
- **OPS-007** — O deployment inicial deve funcionar localmente com Docker, sem impor topologia detalhada.

## 17. Requisitos não funcionais

- **NFR-001** — Interface desktop, em português brasileiro, compatível com versões atuais de Chrome, Firefox e Edge.
- **NFR-002** — Valores monetários em reais brasileiros; datas e horários apresentados no fuso de Brasília.
- **NFR-003** — Suportar aproximadamente 200 empresas e crescimento de usuários sem limite comercial ou funcional imposto pelo produto.
- **NFR-004** — Priorizar consistência, durabilidade, recuperabilidade e rastreabilidade sobre throughput máximo.
- **NFR-005** — Não interromper coletores por ausência de usuários na interface.
- **NFR-006** — Todos os downloads devem respeitar autorização, expiração e auditoria.
- **NFR-007** — A aplicação deve permanecer acessível somente na rede interna; integrações de saída devem usar canais protegidos e destinos aprovados.
- **NFR-008** — O sistema deve representar claramente limitações de fonte, indisponibilidade, cobertura incompleta e estados degradados.
- **NFR-009** — A interface deve adotar identidade institucional sóbria e consistente, com vinho como cor primária, cinza como cor estrutural/neutra e branco como superfície principal; os tons auxiliares devem preservar contraste e legibilidade.
- **NFR-010** — A interface desktop-first deve oferecer navegação consistente entre Dashboard, Documentos, Exportações, Empresas, Certificados, Coletas, Usuários, Auditoria e Retenção, com hierarquia clara para títulos, ações, filtros, tabelas, estados e informações operacionais, sem padrões visuais incompatíveis entre funcionalidades.
- **NFR-011** — A experiência operacional deve manter densidade e legibilidade adequadas, padrões consistentes de loading, vazio válido, erro, indisponibilidade, degradação, bloqueio, sucesso e ações críticas, além de contraste, foco visível, labels e navegação por teclado quando aplicável; deve adaptar-se aos tamanhos usuais de desktop e notebook, sem ampliar o MVP para mobile.
- **NFR-012** — A modernização visual não pode, por si só, alterar comportamento fiscal, regra de negócio, papel, autorização server-side, contrato de backend ou informação operacional relevante; mensagens técnicas internas devem ser apresentadas de forma compreensível quando houver estado funcional equivalente, sem ocultar esse estado.
- **NFR-013** — A aplicação autenticada deve manter navegação por destinos URL-endereçáveis entre Dashboard, Documentos, Exportações, Empresas, Certificados, Coletas, Usuários, Auditoria e Retenção. Cada destino exibe uma área primária por vez dentro de uma estrutura persistente; refresh, deep link e Back/Forward preservam a localização, e filtros ou drill-downs já suportados permanecem representáveis na URL. Indicador clicável do dashboard abre o destino correspondente com seus filtros canônicos aplicados.

## 18. Estados de erro, vazio, bloqueio e degradação

| Estado | Comportamento mínimo |
|---|---|
| Sucesso com documentos | Exibir quantidade, cobertura, datas e estado atualizado. |
| Consulta válida e vazia ao ADN | Concluir com “Nenhum documento encontrado” somente quando a consulta válida terminar e o ADN não disponibilizar documentos naquela consulta; não inferir ausência absoluta de movimento fiscal fora do ADN. |
| Indisponibilidade da fonte | Informar indisponibilidade, manter cursor/progresso seguro e aplicar retry quando permitido; não apresentar “Nenhum documento encontrado”. |
| Ausência de cobertura no ADN | Informar que a empresa ou município não possui cobertura automática pelo ADN no MVP; não tratar como consulta vazia, indisponibilidade transitória ou sucesso de coleta. |
| Parcial | Preservar itens duráveis, informar lacunas/pendências e não avançar estado de forma insegura. |
| Retry | Exibir próxima tentativa e motivo sem duplicar processamento. |
| Bloqueado | Informar causa, ação corretiva e próximo momento permitido; não insistir contra bloqueio permanente. |
| Falha temporária | Registrar erro seguro, aplicar retry progressivo e permitir reprocessamento autorizado. |
| Falha permanente | Suspender retry automático quando aplicável e solicitar correção. |
| Payload desconhecido | Preservar original, sinalizar análise e não declarar sucesso completo. |
| Conflito de identidade | Preservar evidências, impedir sobrescrita e abrir estado de análise. |
| PDF indisponível | Manter XML visível e permitir nova geração. |
| ZIP parcial | Informar arquivos ausentes/falhos e nunca declarar completude sem comprovação. |
| Fonte indisponível | Mostrar degradação e manter progresso/cursor seguro para retomada. |

## 19. Jornadas principais

### J1 — Primeiro acesso

Instalação fornece o segredo inicial de forma segura, cria Guilherme como Administrador com hash da senha, registra o evento e permite autenticação. Tentativas válidas e inválidas ficam auditadas.

### J2 — Cadastro e coleta inicial

Administrador ou Operador cadastra CNPJ/razão social, opcionalmente consulta OpenCNPJ, envia `.pfx` e senha. O sistema valida tudo, associa o certificado, ativa a empresa, inicia os fluxos habilitados e mostra cobertura, progresso e impedimentos.

### J3 — Operação recorrente

O coletor executa em segundo plano conforme regras oficiais. O usuário consulta status independente de NF-e/NFS-e, identifica atrasos ou bloqueios e inicia ou repete uma coleta permitida.

### J4 — Consulta fiscal

Usuário autorizado busca por identificador, CNPJ, empresa, número ou nomes, aplica filtros, abre o detalhe padronizado, consulta eventos e baixa XML ou PDF disponível.

### J5 — Exportação em lote

Usuário aplica filtros, solicita ZIP, acompanha processamento, recebe status de completude/erros, baixa apenas seu próprio ZIP ou um ZIP como Administrador, e o arquivo expira após 24 horas.

### J6 — Administração e auditoria

Administrador gerencia usuários, configurações, saúde, backups e auditoria. Ações críticas exigem motivo e permanecem no histórico imutável.

### J7 — Exclusão após retenção

Administrador consulta documentos elegíveis, visualiza escopo e artefatos, confirma com motivo, o sistema exclui o conjunto coerente, preserva auditoria sem conteúdo fiscal e impede exclusões ainda retidas.

## 20. Critérios de aceitação

- **AC-001** — Cadastro de CNPJ duplicado é rejeitado com mensagem clara; CNPJ de empresa com documentos não pode ser alterado.
- **AC-002** — Cadastro com certificado válido ativa coleta; certificado inválido, expirado, ilegível, com senha incorreta ou CNPJ divergente impede associação e explica o erro.
- **AC-003** — Usuário desativado não autentica e suas sessões existentes são terminadas; auditoria anterior permanece consultável.
- **AC-004** — Cada papel só executa as operações definidas; acesso direto a recurso não autorizado também é recusado.
- **AC-005** — NF-e entrada/saída, NFS-e tomada/prestada/evento, datas, competência, estados e vínculos aparecem corretamente no detalhe.
- **AC-006** — Repetição e retry de mesma unidade não produzem documento, evento, manifestação, PDF ou avanço duplicado.
- **AC-007** — Uma interrupção após recebimento durável permite retomada sem perda; item não durável não pode ser considerado consumido.
- **AC-008** — Uma consulta válida ao ADN sem documentos disponibilizados mostra exatamente “Nenhum documento encontrado”; indisponibilidade da fonte, ausência de cobertura no ADN e coleta parcial exibem estados distintos, sem usar essa mensagem nem afirmar ausência absoluta de movimento fiscal.
- **AC-009** — Payload desconhecido, malformado ou conflitante permanece preservado e visível para análise.
- **AC-010** — XML original continua baixável quando PDF falha; regeneração respeita renderer/versão e não cria equivalentes duplicados.
- **AC-011** — Busca e todos os filtros especificados funcionam entre empresas acessíveis; filtros de valor e Excel/CSV não aparecem.
- **AC-012** — ZIP multiempresa mantém estrutura segura, registra metadados, é assíncrono, restringe download e expira sem remover fonte; parcial não é declarado completo.
- **AC-013** — Indicadores do dashboard abrem listagens filtradas e refletem empresas, documentos, valores, certificados, coletas e saúde operacional; quantidades e valores do período selecionado são comparados com o período imediatamente anterior de mesma duração, consecutivo e sem sobreposição.
- **AC-014** — Todas as ações enumeradas em AUD-002 a AUD-007 geram auditoria com os campos aplicáveis de AUD-008 e sem segredos; toda ação crítica enumerada em AUD-009 é rejeitada sem motivo explícito.
- **AC-015** — Exclusão dentro da retenção é bloqueada; uma NF-e autorizada em 15/08/2026 somente é elegível em 15/08/2037, e uma NFS-e emitida em qualquer data de 2026 somente é elegível em 01/01/2032. Documento elegível exige escopo, confirmação e motivo, remove artefatos relacionados e preserva auditoria sem conteúdo fiscal.
- **AC-016** — Backup diário e políticas de retenção são observáveis por Administrador; o conjunto é verificável por manifesto, hashes e tamanhos, e há procedimento manual de recuperação documentado para restaurar documentos, PDFs, estado e material criptografado com a chave mestre disponibilizada externamente.
- **AC-017** — Após reinício, coletas não dependem de memória, não concorrem indevidamente e retomam com segurança.
- **AC-018** — Empresas sem cobertura NFS-e no Portal Nacional/ADN continuam cadastráveis e exibem a limitação como ausência de cobertura, sem falso sucesso, sem mensagem de consulta vazia e sem confundi-la com indisponibilidade transitória.
- **AC-019** — A consulta opcional ao OpenCNPJ envia somente o CNPJ, mantém os dados obtidos identificados como públicos e não autoritativos e, quando falha ou está indisponível, não impede cadastro nem coleta; validações e contratos pertinentes não pressupõem que o CNPJ permanecerá exclusivamente numérico.
- **AC-020** — Empresa não pode ser excluída diretamente; desativá-la exige motivo e interrompe coletas automáticas sem remover acervo ou estado; reativá-la retoma do estado persistido, e os fluxos NF-e e NFS-e podem ser habilitados ou pausados independentemente.
- **AC-021** — Certificado com 30 dias ou menos é sinalizado como próximo do vencimento; sua substituição preserva acervo, estados e históricos; arquivo e senha permanecem criptografados e nenhuma saída expõe a senha.
- **AC-022** — Login válido e inválido é auditado, tentativas repetidas são limitadas, a sessão expira após 30 minutos de inatividade e a instalação cria o primeiro Administrador usando segredo seguro sem registrar senha em plaintext.
- **AC-023** — A interface é integralmente apresentada em português brasileiro, usa horário de Brasília e real brasileiro e funciona nas versões desktop atuais de Chrome, Firefox e Edge.
- **AC-024** — Em ambiente interno com HTTPS, coletores continuam operando sem usuário conectado, falhas operacionais ficam visíveis a Administradores e reinícios preservam progresso durável e retomada idempotente.
- **AC-025** — A validação do MVP demonstra operação com aproximadamente 200 empresas e não encontra limite comercial ou funcional configurado para quantidade de contas de usuário.
- **AC-026** — A interface operacional apresenta identidade em vinho, cinza e branco, navegação consistente e estados visuais compreensíveis; mantém contraste, foco, labels e teclado aplicáveis em desktop/notebook, preservando os contratos funcionais e a autorização server-side existentes.
- **AC-027** — A sidebar navega para destinos, não para âncoras de um documento com todas as funcionalidades montadas. A estrutura autenticada permanece visível enquanto a área primária muda; navegação direta, refresh, deep links, Back/Forward e drill-downs do dashboard preservam a mesma intenção e continuam sujeitos à autorização do servidor.

## 21. Critérios de sucesso do produto

Metas iniciais de aceite, sujeitas a medição durante piloto:

- Operar aproximadamente 200 empresas sem limite comercial/funcional de usuários.
- Manter coleta segura 24 horas por dia, com falhas e bloqueios visíveis.
- Não haver perda conhecida de documento fiscal recebido e armazenado duravelmente.
- Não haver duplicidade de documento lógico após retries e reprocessamentos.
- Demonstrar enforcement correto dos três papéis.
- Completar onboarding de empresas e certificados válidos.
- Consultar e baixar XML/PDF individualmente.
- Gerar ZIP multiempresa com controle de acesso e resultado de completude explícito.
- Cobrir auditoria de todas as ações críticas.
- Manter backup verificável e procedimento manual de recuperação documentado.
- Impedir exclusão prematura e aplicar retenção corretamente.
- Recuperar coletas com segurança após reinício ou falha primária até o próximo dia útil.

Não são estabelecidas metas agressivas de latência, disponibilidade, throughput ou volume sem evidência operacional.

## 22. Riscos e mitigações

| Risco | Mitigação de produto |
|---|---|
| Mudança de regras/limites fiscais | Manter intervalos, cooldowns e capacidades revalidáveis/configuráveis; acompanhar documentação oficial. |
| Fonte oficial indisponível | Estado degradado visível, retry seguro, cursor persistido e nenhuma perda silenciosa. |
| Certificado inválido/expirado | Validação prévia, bloqueio explícito e suspensão de retry permanente. |
| NFS-e não disponível no município | Declarar cobertura limitada ao Portal Nacional/ADN e indicar limitação por empresa. |
| Duplicidade ou colisão de identidade | Identidade explícita, hashes, estados de conflito e idempotência. |
| Falha de PDF | XML primário preservado e regeneração controlada. |
| ZIP incompleto | Processamento assíncrono, metadados e status de completude explícito. |
| Exposição de segredos | Criptografia, HTTPS, autorização, cookies seguros e proibição de segredos em logs/auditoria. |
| Exclusão indevida | Retenção inviolável na interface, confirmação, motivo e auditoria. |
| Falha do servidor | Backups verificáveis, procedimento manual de recuperação e recuperação até o próximo dia útil. |

## 23. Dependências e restrições externas

- Disponibilidade, autenticação, autorização, limites, cooldowns, NSUs, cursores, manifestação, sequenciamento e formatos dos serviços oficiais SEFAZ e Portal Nacional/ADN.
- Certificados A1 válidos e correspondentes ao CNPJ cadastrado.
- Conectividade de saída da instalação para serviços fiscais e, opcionalmente, OpenCNPJ.
- OpenCNPJ como fonte complementar, pública e não autoritativa; seu funcionamento não pode afetar a coleta.
- HTTPS, rede interna da INOV, armazenamento fiscal, banco, backups separados e capacidade local compatível com a operação.
- Validação periódica de regras legais e técnicas junto a documentação oficial, Receita Federal, SEFAZ, Portal Nacional/ADN e compliance da INOV.

O PRD não fixa endpoints, intervalos voláteis ou mecanismo único de integração. Esses pontos devem ser revalidados no planejamento técnico.

## 24. Segurança e privacidade operacional

Além dos requisitos `SEC-*`, dados fiscais, identificadores pessoais, XMLs, PDFs, certificados e downloads devem ser tratados como restritos à operação da INOV. Erros exibidos ao usuário devem ser úteis sem revelar credenciais, material criptográfico, detalhes internos desnecessários ou dados de outra empresa. A autorização deve ser verificada tanto na interface quanto na execução de jobs, downloads e regenerações.

## 25. Glossário

- **A1** — Certificado digital armazenado em arquivo, neste produto exclusivamente `.pfx`.
- **ADN** — Ambiente de Dados Nacional associado ao Portal Nacional da NFS-e.
- **CNPJ** — Cadastro Nacional da Pessoa Jurídica.
- **Competência** — Período derivado da data de emissão do documento.
- **DANFE** — Documento Auxiliar da NF-e.
- **DANFSe** — Documento Auxiliar da NFS-e.
- **Evento** — Ocorrência fiscal vinculada a um documento principal.
- **NF-e** — Nota Fiscal eletrônica, incluindo documentos recebidos e emitidos.
- **NFS-e** — Nota Fiscal de serviço eletrônica.
- **NSU** — Número sequencial utilizado por alguns fluxos oficiais para consumo/distribuição.
- **Payload original** — Conteúdo recebido da fonte fiscal, preservado para rastreabilidade.
- **Renderer** — Identidade/versão do componente que produz PDF derivado.
- **Retry** — Nova tentativa automática ou manual após falha permitida.
- **Cursor** — Estado persistido de progresso de consumo de uma fonte/fluxo.

## 26. Rastreabilidade e cobertura

| Área confirmada | Requisitos principais | Critérios |
|---|---|---|
| Identidade, escala e interface | NFR-001 a NFR-003; NFR-009 a NFR-013 | AC-023, AC-025, AC-026, AC-027 |
| Papéis, usuários e autenticação | FR-AUTH-001 a FR-AUTH-007; BR-AUTH-001 e BR-AUTH-002 | AC-003, AC-004, AC-014, AC-022 |
| Empresas | FR-COMP-001 a FR-COMP-003; BR-COMP-001 a BR-COMP-006 | AC-001, AC-002, AC-020 |
| OpenCNPJ | FR-COMP-004 e FR-COMP-005; BR-COMP-007 e BR-COMP-008 | AC-019 |
| Certificados | FR-CERT-001 e FR-CERT-002; BR-CERT-001 a BR-CERT-007 | AC-002, AC-014, AC-021 |
| Coleta e retries | FR-COLL-001 e FR-COLL-002; BR-COLL-001 a BR-COLL-010 | AC-006 a AC-009, AC-017 |
| NF-e | FR-NFE-001 a FR-NFE-004; BR-NFE-001 a BR-NFE-003 | AC-005 a AC-009 |
| NFS-e/ADN | FR-NFSE-001 a FR-NFSE-003; BR-NFSE-001 a BR-NFSE-003 | AC-005, AC-008, AC-009, AC-018 |
| Integridade fiscal | BR-INT-001 a BR-INT-008 | AC-006, AC-007, AC-009, AC-017 |
| Consulta e filtros | FR-DOC-001 a FR-DOC-005; BR-DOC-001 e BR-DOC-002 | AC-005, AC-011 |
| XML/PDF | FR-ART-001 a FR-ART-003; BR-ART-001 a BR-ART-003 | AC-010 |
| ZIP | FR-ZIP-001 a FR-ZIP-003; BR-ZIP-001 a BR-ZIP-004 | AC-012 |
| Dashboard e saúde | FR-DASH-001 a FR-DASH-003; FR-OPS-001; BR-OPS-001; BR-DASH-001 | AC-013 |
| Retenção | RET-001 a RET-008 | AC-015 |
| Auditoria | AUD-001 a AUD-010 | AC-003, AC-012, AC-014, AC-015 |
| Backup | OPS-BKP-001 a OPS-BKP-006; BR-BKP-001; SEC-009 | AC-016 |
| Segurança | SEC-001 a SEC-008 | AC-002 a AC-004, AC-010, AC-012, AC-014, AC-021, AC-022 |
| Operação e recuperação | OPS-001 a OPS-007; NFR-004 a NFR-008 | AC-007 a AC-009, AC-012, AC-016 a AC-018, AC-024, AC-025 |
| Fora do MVP | Seção 6 | Verificação documental e de escopo |

## 27. Premissas registradas

- A aplicação começa com banco, armazenamento fiscal, empresas, certificados, documentos, cursores e estado operacional vazios; não existe migração.
- O primeiro Administrador é provisionado na instalação, sem senha registrada neste documento ou no repositório.
- O MVP é exclusivamente interno e desktop.
- O Portal Nacional/ADN é a única cobertura de NFS-e do MVP.
- A interpretação operacional da retenção é a descrita na seção 13.
- Metas numéricas de sucesso são alvos iniciais de aceite e podem ser refinadas por medição, sem reduzir os requisitos de integridade, segurança, auditoria e retenção.
