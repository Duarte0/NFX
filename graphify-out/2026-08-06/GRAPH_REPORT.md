# Graph Report - .  (2026-08-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1109 nodes · 1701 edges · 115 communities (64 shown, 51 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 63 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c000eef4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- identity/services.py
- ArtifactStorageService
- load_settings
- Graphify Skill Instructions
- Arquitetura técnica — NFX INOV
- Plano de implementação — NFX INOV
- audit/services.py
- dependencies.py
- identity/views.py
- Consulta de documentos e download individual
- companies/views.py
- devDependencies
- OpenCnpjResponse
- What You Must Do When Invoked
- PRD — NFX INOV
- compilerOptions
- companies/models.py
- 9. Requisitos funcionais e regras de negócio
- Persistência relacional e migrações
- Fundação de auditoria append-only
- Autenticação, sessões, RBAC e shell web
- Ingestão fiscal comum e integridade
- main.tsx
- Fundação do projeto
- Configuração segura e isolamento fiscal de testes
- Armazenamento de objetos e integridade
- Certificados A1 e criptografia por envelope
- Empresas, fluxos e enriquecimento público
- Jobs duráveis, leases, políticas e observabilidade inicial
- Exportação ZIP assíncrona
- Technical Architecture - NFX INOV
- urls.py
- test_migrations.py
- graphify reference: extra exports and benchmark
- Simuladores fiscais e fixtures seguras
- Controle manual de coleta
- Elegibilidade de retenção e prévia administrativa
- 19. Jornadas principais
- Renderização de DANFE e DANFSe
- Dashboard e saúde operacional
- Backup e restauração comprovada
- Exclusão definitiva controlada
- Runtime interno e HTTPS
- Fundação P0
- Hardening, ameaças e testes de falha
- Piloto interno e homologação segregada
- graphify reference: query, path, explain
- P9 Operação e piloto
- 7. Usuários e papéis
- 10. Arquitetura de componentes
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- Frontend HTML Entry
- Artifact Model
- Migration
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- smoke.sh
- test-integration.sh
- Durable Job Engine
- AGENTS.md
- adapters/__init__.py
- artifacts/__init__.py
- audit/__init__.py
- certificates/__init__.py
- collection/__init__.py
- documents/__init__.py
- exports/__init__.py
- identity/__init__.py
- infrastructure/__init__.py
- nfx/__init__.py
- 0002_artifact.py
- 0003_identity.py
- 0004_audit_foundation.py
- 0005_user_administration_version.py
- migrations/__init__.py
- operations/__init__.py
- retention/__init__.py
- extraction-spec.md
- Docker Compose App Configuration
- Docker Compose Test Configuration
- 12. Autenticação e autorização
- Schema Contract
- Any
- SessionIdentity
- HttpRequest
- JsonResponse
- ValueError
- HttpRequest
- HttpResponse
- JsonResponse
- require_GET
- BaseCommand
- HttpResponse
- Docker Compose Development Configuration
- Authorize Policy
- Identity Session
- User Model
- Artifact Storage Service
- Company Model
- Fiscal Adapter Port
- django_db
- SessionIdentity
- django_db
- User

## God Nodes (most connected - your core abstractions)
1. `Arquitetura técnica — NFX INOV` - 47 edges
2. `PRD — NFX INOV` - 28 edges
3. `Plano de implementação — NFX INOV` - 26 edges
4. `ArtifactStorageService` - 21 edges
5. `MemoryObjectStore` - 21 edges
6. `Graphify Skill Instructions` - 21 edges
7. `load_settings()` - 19 edges
8. `Artifact` - 19 edges
9. `UserAdministrationError` - 17 edges
10. `set_user_active()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `test_dependency_check_is_injectable_and_reports_only_service_names()` --calls--> `ServiceDependencies`  [EXTRACTED]
  tests/unit/test_dependencies.py → backend/nfx/infrastructure/dependencies.py
- `test_schema_incompatibility_makes_readiness_fail_without_details()` --calls--> `ServiceDependencies`  [EXTRACTED]
  tests/unit/test_dependencies.py → backend/nfx/infrastructure/dependencies.py
- `test_redaction_handles_nested_values_exceptions_urls_and_binary_payloads()` --calls--> `redact()`  [EXTRACTED]
  tests/unit/test_safe_configuration.py → backend/nfx/infrastructure/redaction.py
- `Dashboard e saúde operacional` --references--> `P8 ZIP, dashboard e retenção`  [EXTRACTED]
  specs/p8-dashboard-and-operational-health.md → IMPLEMENTATION_PLAN.md
- `Runtime interno e HTTPS` --references--> `P9 Operação e piloto`  [EXTRACTED]
  specs/p9-runtime-and-https.md → IMPLEMENTATION_PLAN.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Operational Workflow** — _codex_skills_graphify_skill_document, _codex_skills_graphify_references_query_document, _codex_skills_graphify_references_update_document [INFERRED 0.85]
- **NFX Implementation Phases** — p0_fundacao, p1_nucleo_seguro, p2_empresas_certificados, p3_jobs_simuladores, p4_ingestao_comum, p5_nfe, p6_nfse_adn, p7_consulta_artefatos, p8_zip_dashboard_retencao, p9_operacao_piloto [EXTRACTED 1.00]
- **NFX Core Documentation** — prd_nfx_inov, architecture_nfx_inov, implementation_plan [EXTRACTED 1.00]
- **Docker Infrastructure Stack** — docker_compose_app, docker_compose_test, docker_compose_dev [EXTRACTED 0.95]
- **Fiscal Ingestion Flow** — specs_p3_fiscal_adapter_simulation_and_fixtures_fiscal_adapter_port, specs_p4_fiscal_document_ingestion_and_integrity_document, specs_p1_object_storage_and_integrity_artifact_storage_service [EXTRACTED 0.90]

## Communities (115 total, 51 thin omitted)

### Community 0 - "identity/services.py"
Cohesion: 0.09
Nodes (64): Action, authorize(), The single fail-closed policy used by HTTP handlers and future workers., _admin_event(), _assert_not_last_administrator(), _assert_version(), authenticate(), bootstrap_first_administrator() (+56 more)

### Community 1 - "ArtifactStorageService"
Cohesion: 0.08
Nodes (41): Artifact, ArtifactState, Meta, Relational reference to one opaque object-store key. The logical key belongs to…, ArtifactConflict, ArtifactError, ArtifactMetrics, ArtifactNotReadable (+33 more)

### Community 2 - "load_settings"
Cohesion: 0.06
Nodes (48): EmptyFiscalSimulator, FiscalDestinationError, FiscalDestinationGuard, RuntimeError, P0 fiscal boundary: validate every destination before a transport can run., Safe rejection that intentionally contains no destination value., The sole initial fiscal transport; it always produces an empty result., Validate the configured URL and every declared redirect before I/O. (+40 more)

### Community 3 - "Graphify Skill Instructions"
Cohesion: 0.05
Nodes (49): Add and Watch Reference, URL Ingestion, Watch Mode, Exports Reference, FalkorDB Export, GraphML Export, MCP Server, Neo4j Export (+41 more)

### Community 4 - "Arquitetura técnica — NFX INOV"
Cohesion: 0.04
Nodes (46): 11. Organização do repositório, 12. Stack selecionada e justificativa, 13. Alternativas consideradas e rejeitadas, 14. Responsabilidade e propriedade de estado, 15. Estratégia de dados e persistência, 16. Responsabilidades do PostgreSQL, 17. Responsabilidades do armazenamento de objetos, 18. Identidade fiscal de documentos (+38 more)

### Community 5 - "Plano de implementação — NFX INOV"
Cohesion: 0.04
Nodes (44): 10. Fases detalhadas e backlog estável, 11. Dependências, caminho crítico e paralelismo, 12. Estratégia de testes e validação, 13. Estratégia de segurança fiscal, 14. Banco e migrações, 15. Sequência de frontend, 16. Observabilidade, backup e restore, 17. Mapa de specs (+36 more)

### Community 6 - "audit/services.py"
Cohesion: 0.08
Nodes (36): Any, AuditEvent, AuditChain, AuditEvent, Meta, The single stream serializes appends without allowing event rewrites., AuditService, AuditUnavailable (+28 more)

### Community 7 - "dependencies.py"
Cohesion: 0.07
Nodes (29): dependencies_from_environment(), DependencyCheck, _object_probe(), _postgres_probe(), _schema_probe(), ServiceDependencies, _migration_names(), MigrationOutcome (+21 more)

### Community 8 - "identity/views.py"
Cohesion: 0.17
Nodes (42): companies(), company_activate(), company_create(), company_deactivate(), company_detail(), company_enrichment(), company_flow(), _company_payload() (+34 more)

### Community 9 - "Consulta de documentos e download individual"
Cohesion: 0.05
Nodes (40): P1 Núcleo seguro, P2 Empresas e certificados, P3 Jobs e simuladores, P4 Ingestão comum, P5 NF-e, P6 NFS-e/ADN, P7 Consulta e artefatos, Administração de usuários (+32 more)

### Community 10 - "companies/views.py"
Cohesion: 0.18
Nodes (30): activate_company(), _company(), CompanyCnpjImmutable, CompanyError, CompanyInactive, CompanyNotFound, CompanyVersionConflict, _context() (+22 more)

### Community 11 - "devDependencies"
Cohesion: 0.06
Nodes (32): eslint, @eslint/js, eslint-plugin-react-hooks, dependencies, react, react-dom, vite, @vitejs/plugin-react (+24 more)

### Community 12 - "OpenCnpjResponse"
Cohesion: 0.12
Nodes (18): HttpOpenCnpjClient, _HttpResponse, OpenCnpjClient, OpenCnpjResponse, A safe adapter value; payload is public data and never fiscal authority., The only input exposed to OpenCNPJ is the normalized CNPJ., Optional public-source transport with an injected opener for tests., Default local/runtime adapter until an approved public endpoint is configured. (+10 more)

### Community 13 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 14 - "PRD — NFX INOV"
Cohesion: 0.08
Nodes (24): 10. Ciclo de vida de empresa, 11. Ciclo de vida de certificado, 13. Retenção e exclusão, 14. Auditoria, 15. Backup e recuperação, 16. Requisitos operacionais e observabilidade, 17. Requisitos não funcionais, 18. Estados de erro, vazio, bloqueio e degradação (+16 more)

### Community 15 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+13 more)

### Community 16 - "companies/models.py"
Cohesion: 0.21
Nodes (13): CompanyMetrics, CompanyMetricsSnapshot, Small process metrics port; P3 can replace the sink without changing domain…, Company, CompanyFlow, CompanyStatus, EnrichmentSnapshot, EnrichmentStatus (+5 more)

### Community 17 - "9. Requisitos funcionais e regras de negócio"
Cohesion: 0.15
Nodes (13): 9.10 XML, DANFE e DANFSe, 9.11 Exportação ZIP, 9.12 Dashboard, 9.1 Usuários, autenticação e autorização, 9.2 Empresas, 9.3 Enriquecimento OpenCNPJ, 9.4 Certificados, 9.5 Coleta geral (+5 more)

### Community 18 - "Persistência relacional e migrações"
Cohesion: 0.17
Nodes (11): Aceite e DoD, Baseline e escopo, Contratos e operação, Decisões de implementação, Decisões e Proposed, Falha, recuperação e compatibilidade, Implementação e evidências, Metadados (+3 more)

### Community 19 - "Fundação de auditoria append-only"
Cohesion: 0.18
Nodes (10): Aceite e DoD, Baseline, escopo e não escopo, Contratos, comportamento e autorização, Decisões de implementação e evidências, Estado e schema Proposed, Falhas, segurança e observabilidade, Fundação de auditoria append-only, Metadados (+2 more)

### Community 20 - "Autenticação, sessões, RBAC e shell web"
Cohesion: 0.18
Nodes (10): Aceite e DoD, Autenticação, sessões, RBAC e shell web, Baseline, escopo e não escopo, Decisões de implementação e evidências, Estado e contratos Proposed, Metadados, Propósito e resultado, Regras, UI e autorização (+2 more)

### Community 21 - "Ingestão fiscal comum e integridade"
Cohesion: 0.18
Nodes (10): Aceite e DoD, Baseline, escopo e não escopo, Contratos, frontend e autorização, Falhas, recovery e testes, Ingestão fiscal comum e integridade, Metadados, Pipeline e invariantes, Propriedade e schema Proposed (+2 more)

### Community 22 - "main.tsx"
Cohesion: 0.22
Nodes (8): App(), AuditEvent, Company, CompanyFlow, ManagedUser, root, statusLabel(), User

### Community 23 - "Fundação do projeto"
Cohesion: 0.20
Nodes (9): Baseline, escopo e não escopo, Decisões e detalhes Proposed, Fundação do projeto, Metadados, Módulos, contratos e estado, Propósito e resultado observável, Segurança, observabilidade e falhas, Sequência, aceite e DoD (+1 more)

### Community 24 - "Configuração segura e isolamento fiscal de testes"
Cohesion: 0.20
Nodes (9): Baseline, escopo e não escopo, Configuração segura e isolamento fiscal de testes, Decisões e propostas, Estado, falhas e observabilidade, Metadados, Propósito e resultado observável, Segurança, redaction e interfaces, Sequência, aceite e DoD (+1 more)

### Community 25 - "Armazenamento de objetos e integridade"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Armazenamento de objetos e integridade, Baseline, escopo e não escopo, Decisões de implementação, Interfaces e responsabilidades implementadas, Metadados, Migração, testes e evidência, Propósito e resultado (+1 more)

### Community 26 - "Certificados A1 e criptografia por envelope"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Certificados A1 e criptografia por envelope, Estado e schema Proposed, Falhas, testes e recovery, Metadados, Propósito e resultado, Regras, interfaces e UI (+1 more)

### Community 27 - "Empresas, fluxos e enriquecimento público"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Autorização, auditoria e observabilidade, Baseline, escopo e não escopo, Empresas, fluxos e enriquecimento público, Estado e schema Proposed, Falhas, testes e recovery, Metadados, Propósito e resultado (+1 more)

### Community 28 - "Jobs duráveis, leases, políticas e observabilidade inicial"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos e comportamento, Estado e schema Proposed, Falhas e testes, Jobs duráveis, leases, políticas e observabilidade inicial, Metadados, Propósito e resultado (+1 more)

### Community 29 - "Exportação ZIP assíncrona"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Estado e contratos Proposed, Exportação ZIP assíncrona, Falhas, recovery e testes, Metadados, Propósito e resultado, Segurança, auditoria, observabilidade (+1 more)

### Community 30 - "Technical Architecture - NFX INOV"
Cohesion: 0.22
Nodes (7): Technical Architecture - NFX INOV, Audit Chain Mechanism, Infrastructure Configuration Module, Product Requirements Document - NFX INOV, Spec: P0 Project Foundation, Spec: P0 Safe Configuration, Spec: P1 Audit Foundation

### Community 31 - "urls.py"
Cohesion: 0.31
Nodes (7): Company lifecycle, flow configuration, and public enrichment boundary., index(), live(), HttpRequest, JsonResponse, ready(), HttpResponse

### Community 32 - "test_migrations.py"
Cohesion: 0.42
Nodes (7): Migration, django_db, test_clean_install_and_rerun_produce_the_same_schema(), test_failed_migration_is_not_recorded_and_a_safe_correction_can_continue(), test_schema_status_detects_ahead_incompatible_history(), test_two_migrators_are_serialized_and_only_one_applies_the_baseline(), _unapply_nfx_migrations()

### Community 33 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 34 - "Simuladores fiscais e fixtures seguras"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Contratos Proposed e cenários, Metadados, Observabilidade, falha e testes, Propósito e resultado, Segurança e fixtures, Simuladores fiscais e fixtures seguras

### Community 35 - "Controle manual de coleta"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Controle manual de coleta, Estado e contratos Proposed, Falhas, observabilidade e testes, Metadados, Propósito e resultado, UI, permissões e comportamento visível

### Community 36 - "Elegibilidade de retenção e prévia administrativa"
Cohesion: 0.22
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos, UI e autorização, Elegibilidade de retenção e prévia administrativa, Metadados, Propósito e resultado, Regras e estado, Segurança, auditoria e observabilidade (+1 more)

### Community 37 - "19. Jornadas principais"
Cohesion: 0.25
Nodes (8): 19. Jornadas principais, J1 — Primeiro acesso, J2 — Cadastro e coleta inicial, J3 — Operação recorrente, J4 — Consulta fiscal, J5 — Exportação em lote, J6 — Administração e auditoria, J7 — Exclusão após retenção

### Community 38 - "Renderização de DANFE e DANFSe"
Cohesion: 0.25
Nodes (7): Auditoria, observabilidade e falhas, Contrato e estado requerido, Metadados, Propósito, baseline e blocker, Renderização de DANFE e DANFSe, Testes e aceite futuro, UI, autorização e segurança

### Community 39 - "Dashboard e saúde operacional"
Cohesion: 0.25
Nodes (8): Dashboard e saúde operacional, Aceite e DoD, Baseline, escopo e não escopo, Contratos e dados Proposed, Falhas e testes, Metadados, Propósito e resultado, UI, autorização e observabilidade

### Community 40 - "Backup e restauração comprovada"
Cohesion: 0.25
Nodes (7): Aceite e DoD, Backup e restauração comprovada, Estado e contratos Proposed, Metadados, Propósito, baseline e exceção, Segurança, observabilidade e falhas, Testes e evidência

### Community 41 - "Exclusão definitiva controlada"
Cohesion: 0.25
Nodes (8): Aceite e DoD, Baseline, escopo e gate local, Estado e contrato Proposed, Exclusão definitiva controlada, Falhas, recovery e testes, Metadados, Propósito e resultado, UI, segurança e observabilidade

### Community 42 - "Runtime interno e HTTPS"
Cohesion: 0.25
Nodes (8): Runtime interno e HTTPS, Aceite e DoD, Baseline, escopo e não escopo, Decisões e configuração Proposed, Metadados, Propósito e resultado, Segurança, observabilidade e falhas, Testes, rollback e evidência

### Community 43 - "Fundação P0"
Cohesion: 0.29
Nodes (6): Configuração segura e isolamento fiscal (P0-02/P0-04), Contratos dos comandos, Decisões Proposed adotadas, Fundação P0, Persistência e migrações (P1-01), Scope boundary

### Community 44 - "Hardening, ameaças e testes de falha"
Cohesion: 0.29
Nodes (7): Aceite e DoD, Baseline, escopo e não escopo, Hardening, ameaças e testes de falha, Metadados, Método e contratos de evidência, Propósito e resultado, Testes, observabilidade e capacidade

### Community 45 - "Piloto interno e homologação segregada"
Cohesion: 0.29
Nodes (7): Baseline, escopo e não escopo, Falhas, observabilidade e recovery, Metadados, Piloto interno e homologação segregada, Plano e decisões, Propósito e resultado, Testes/evidências e aceite

### Community 46 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 48 - "7. Usuários e papéis"
Cohesion: 0.40
Nodes (5): 7.1 Administrador, 7.2 Operador, 7.3 Visualizador, 7.4 Regra global, 7. Usuários e papéis

### Community 49 - "10. Arquitetura de componentes"
Cohesion: 0.50
Nodes (4): 10.1 Módulos de domínio, 10.2 Adaptadores, 10.3 Serviços transversais, 10. Arquitetura de componentes

### Community 50 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 51 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 52 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 53 - "Frontend HTML Entry"
Cohesion: 0.50
Nodes (4): Frontend HTML Entry, src/main.tsx Entry Module, NFX INOV Application, Root Mount Element

### Community 54 - "Artifact Model"
Cohesion: 0.50
Nodes (4): Artifact Model, Certificate Model, Fiscal Document Model, PDF Renderer

### Community 60 - "Durable Job Engine"
Cohesion: 0.67
Nodes (3): Durable Job Engine, Collection Request Service, ZIP Export Service

## Knowledge Gaps
- **465 isolated node(s):** `name`, `private`, `version`, `type`, `build` (+460 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Are the 3 inferred relationships involving `ArtifactStorageService` (e.g. with `Artifact` and `ArtifactState`) actually correct?**
  _`ArtifactStorageService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _465 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `identity/services.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08737060041407868 - nodes in this community are weakly interconnected._
- **Should `ArtifactStorageService` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `load_settings` be split into smaller, more focused modules?**
  _Cohesion score 0.061507936507936505 - nodes in this community are weakly interconnected._
- **Should `Graphify Skill Instructions` be split into smaller, more focused modules?**
  _Cohesion score 0.05102040816326531 - nodes in this community are weakly interconnected._
- **Should `Arquitetura técnica — NFX INOV` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._