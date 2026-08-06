# Empresas, fluxos e enriquecimento público

## Metadados

- **Fase/status:** P2 — pronta após núcleo P1.
- **Backlog:** P2-01, P2-02, parte de UI de P2-04.
- **Dependências:** P0-04, P1-03 e P1-05.
- **PRD:** FR-COMP-001, FR-COMP-002, FR-COMP-003, FR-COMP-004, FR-COMP-005; BR-COMP-001, BR-COMP-002, BR-COMP-003, BR-COMP-004, BR-COMP-005, BR-COMP-006, BR-COMP-007, BR-COMP-008; AUD-004, AUD-008, AUD-009; NFR-001, NFR-002. **Aceite:** AC-001, AC-019, AC-020, AC-023.
- **Arquitetura:** seções 10.1, 10.2, 14–16, 26, 27, 32, 36 e 37.

## Propósito e resultado

Entregar cadastro e ciclo de vida de empresa, controle independente dos fluxos NF-e/NFS-e e enriquecimento OpenCNPJ opcional. Admin/Operador concluem a jornada; Visualizador não altera. Falha de enriquecimento nunca impede cadastro ou coleta.

## Baseline, escopo e não escopo

Não há entidades de empresa. Criar domínio, persistência, casos de uso e telas. Certificado pertence à spec P2-03; integração fiscal e cobertura efetiva pertencem P5/P6; não excluir empresa, importar legado, segmentar por usuário ou integrar município fora do ADN.

## Estado e schema Proposed

Empresas é dona de empresa, enriquecimento e habilitação de fluxos. **Proposed:** empresa com ID, CNPJ informado/normalizado, razão social, estado `cadastrada|ativa|desativada`, `first_collection_at`, motivo/timestamps; configuração por família com `habilitado|pausado`; snapshots de enriquecimento com fonte, obtido em, conteúdo público e status. Constraints: CNPJ normalizado único; motivo obrigatório quando desativada; índices por razão social, estado e CNPJ. O formato físico deve aceitar futura forma alfanumérica; não assumir somente dígitos fora do validador vigente.

## Regras e contratos

Cadastro exige CNPJ e razão social. Antes da primeira coleta durável, CNPJ pode ser corrigido; depois, é imutável. Desativar exige confirmação e motivo, pausa agendamento automático e preserva acervo/cursor/histórico/download; reativar retoma do estado persistido. Fluxos NF-e e NFS-e são independentes e só executam se empresa ativa, fluxo habilitado e certificado válido. Empresa nunca possui endpoint DELETE.

Contratos HTTP internos Proposed: listar/detalhar/criar/editar; ativar/desativar; habilitar/pausar família; solicitar/atualizar enriquecimento. OpenCNPJ recebe somente CNPJ, tem timeout e resposta marcada `público, não autoritativo`; erro não altera dados fiscais. UI: lista, formulário, detalhe com estado/fluxos/cobertura, confirmação de desativação e indicação visual da origem pública.

## Autorização, auditoria e observabilidade

Admin/Operador: leitura e mutações; Visualizador: nenhuma administração. Todos autenticados futuramente consultam documentos de todas empresas. Auditar criar/editar/ativar/desativar/fluxo/enriquecimento, com motivo quando exigido. Logs/métricas: resultado, duração OpenCNPJ, empresas por estado e fluxos pausados; não logar payload público inteiro nem identificadores pessoais desnecessários.

## Falhas, testes e recovery

Constraint vence corrida de CNPJ duplicado. Timeout/404 OpenCNPJ gera estado informativo e permite continuar. Falha ao pausar não apaga state. Testes: CNPJ válido/inválido/duplicado; fronteira antes/depois da primeira coleta; desativação/reativação; fluxos independentes; RBAC; fake OpenCNPJ sucesso/vazio/timeout/conteúdo malformado; browser loading/vazio/erro. Fixture usa CNPJ sintético válido.

## Aceite e DoD

- [ ] Duplicidade é rejeitada claramente e por constraint.
- [ ] CNPJ com documento/coleta durável não muda.
- [ ] Desativação motivada preserva todos os estados e impede agenda automática.
- [ ] Fluxos podem ser pausados/habilitados independentemente.
- [ ] OpenCNPJ envia somente CNPJ e nunca bloqueia operação.

DoD: migrações, domínio, APIs, UI, auditoria, métricas e testes verdes. **Proposed:** shape dos snapshots/URLs; escolha local deve preservar invariantes.
