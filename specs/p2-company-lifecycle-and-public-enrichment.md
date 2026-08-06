# Empresas, fluxos e enriquecimento público

## Metadados

- **Fase/status:** P2 — concluída em 2026-08-06.
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

- [x] Duplicidade é rejeitada claramente e por constraint.
- [x] CNPJ com documento/coleta durável não muda.
- [x] Desativação motivada preserva todos os estados e impede agenda automática.
- [x] Fluxos podem ser pausados/habilitados independentemente.
- [x] OpenCNPJ envia somente CNPJ e nunca bloqueia operação.

DoD: migrações, domínio, APIs, UI, auditoria, métricas e testes verdes. **Concluído em 2026-08-06.**

## Decisões de implementação e evidências

- **Accepted (Proposed resolvido):** `Company`, `CompanyFlow` e `EnrichmentSnapshot` pertencem a
  `nfx.companies`; usam UUID na empresa, `version` para mutações concorrentes, CNPJ normalizado
  armazenado em `CharField(64)` e uma constraint única persistente. O validador vigente aceita
  CNPJ numérico de 14 posições com dígitos verificadores; a coluna já comporta a futura forma
  alfanumérica sem presumir que ela seja válida hoje.
- **Accepted (Proposed resolvido):** cada empresa nasce com NF-e e NFS-e independentes em
  `habilitado`; a desativação altera apenas o estado da empresa, preservando fluxos, acervo e
  futuros cursores. `can_execute_flow()` exige empresa ativa, fluxo habilitado e certificado
  válido, deixando a integração do certificado para P2-03/P3.
- **Accepted (Proposed resolvido):** os contratos HTTP internos são `GET /api/companies`,
  `POST /api/companies/create`, `GET/PATCH /api/companies/<id>`, ações explícitas
  `activate/deactivate`, `flows/<family>` e `enrichment`. Desativação exige `confirmed: true` e
  motivo; não existe rota DELETE. A política server-side usa `Action.ADMINISTER_COMPANIES`.
- **Accepted (Proposed resolvido):** snapshots guardam `source`, CNPJ solicitado, instante,
  status, payload JSON público e `public_non_authoritative=true`; o payload não entra em logs ou
  auditoria. `OpenCnpjClient` recebe somente o CNPJ normalizado, tem transporte HTTP opcional
  injetável e o endpoint local padrão é um cliente indisponível seguro. Timeout, 404, vazio,
  indisponibilidade e conteúdo malformado viram snapshot informativo e não alteram dados da
  empresa nem estado fiscal.
- **Implementação:** domínio e casos de uso em `backend/nfx/companies/{models,services,metrics}.py`,
  contrato/adaptador em `backend/nfx/adapters/opencnpj.py`, endpoints em
  `backend/nfx/companies/views.py` e `backend/nfx/urls.py`, registro em `backend/nfx/models.py`,
  e migração `backend/nfx/migrations/0006_company_lifecycle.py`.
- **UI:** `frontend/src/main.tsx` adiciona lista, cadastro, edição, detalhe, estados de
  carregamento/vazio/erro, confirmação/motivo de desativação, controle independente dos fluxos e
  indicação pública não autoritativa do enriquecimento, mantendo Visualizador sem administração.
- **Auditoria/observabilidade:** criar, editar, ativar, desativar, alterar fluxo e enriquecer usam
  `AuditService`; métricas de resultado/duração de OpenCNPJ, empresas por estado e fluxos pausados
  ficam em `CompanyMetrics`. Payload público integral e identificadores desnecessários não são
  registrados.
- **Validação:** `tests/unit/test_company_lifecycle.py` cobre CNPJ válido/inválido/duplicado,
  constraint, imutabilidade antes/depois da primeira coleta durável, desativação/reativação,
  preservação de fluxo, RBAC, ausência de DELETE, fake OpenCNPJ, somente-CNPJ, sucesso e timeout.
  `tests/integration/test_migrations.py` cobre instalação limpa, rerun, falha/recovery e dois
  migradores concorrentes incluindo `0006_company_lifecycle`. Docker integration: 18 testes
  verdes; foco P2 + regressões: 38 testes verdes; frontend lint/build verdes; Ruff verde.
- **Graphify:** `graphify . --update --code-only` e `graphify cluster-only .` atualizaram o grafo,
  relatório, manifest e HTML; a consulta posterior encontrou os nós de empresa, enriquecimento,
  adaptador, serviços, testes e migração. A atualização semântica completa foi tentada e falhou
  somente porque não há chave LLM configurada (`5 doc/paper/image file(s) need semantic extraction`);
  por isso a representação AST/código está atualizada, mas a camada semântica dos documentos não é
  declarada como sincronizada nesta sessão.
