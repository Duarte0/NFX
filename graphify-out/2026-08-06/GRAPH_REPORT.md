# Graph Report - workspace  (2026-08-06)

## Corpus Check
- 141 files · ~77,122 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1468 nodes · 2749 edges · 122 communities (82 shown, 40 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 182 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b444fab2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- identity/services.py
- MemoryObjectStore
- load_settings
- Graphify Skill Instructions
- Arquitetura técnica — NFX INOV
- Plano de implementação — NFX INOV
- nfx/models.py
- dependencies.py
- certificates/services.py
- Administração de usuários
- companies/services.py
- devDependencies
- _HttpResponse
- What You Must Do When Invoked
- PRD — NFX INOV
- compilerOptions
- JobEngine
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
- Job
- 0006_company_lifecycle.py
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
- jobs/policy.py
- HandlerOutcome
- collection/__init__.py
- documents/__init__.py
- exports/__init__.py
- test_job_engine.py
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
- jobs/services.py
- 0007_certificate_lifecycle.py
- Build Pass
- Specification Pass
- Issue Creation Pass
- 0002_-_policy-driven-job-retry-and-blocking.md
- Planning Pass
- 0003_-_deterministic-fiscal-simulators-and-fixtures.md
- test_jobs.py
- 0009_job_policies.py
- 0001_-_durable-job-queue-and-leases.md
- Docker Compose Development Configuration
- Authorize Policy
- Identity Session
- User Model
- Artifact Storage Service
- Company Model
- Fiscal Adapter Port
- simulation.py
- Update Reference
- 0000_-_ISSUE_TEMPLATE.md
- jobs/__init__.py
- 0008_durable_jobs.py
- loop.sh
- /graphify
- Exports Reference
- Query Reference
- GitHub and Merge Reference
- .save

## God Nodes (most connected - your core abstractions)
1. `AuditService` - 48 edges
2. `Arquitetura técnica — NFX INOV` - 47 edges
3. `Action` - 41 edges
4. `ArtifactStorageService` - 38 edges
5. `JobEngine` - 36 edges
6. `HandlerOutcome` - 34 edges
7. `SessionIdentity` - 30 edges
8. `PRD — NFX INOV` - 28 edges
9. `add_certificate()` - 27 edges
10. `ObjectStore` - 26 edges

## Surprising Connections (you probably didn't know these)
- `MemoryObjectStore` --uses--> `ObjectMetadata`  [INFERRED]
  tests/unit/test_certificate_lifecycle.py → backend/nfx/artifacts/storage.py
- `MemoryObjectStore` --uses--> `ArtifactStorageService`  [INFERRED]
  tests/integration/test_artifact_storage.py → backend/nfx/artifacts/storage.py
- `test_minio_adapter_writes_and_verifies_synthetic_bytes()` --calls--> `dependencies_from_environment()`  [INFERRED]
  tests/integration/test_artifact_storage.py → backend/nfx/infrastructure/dependencies.py
- `FrozenClock` --uses--> `HandlerOutcome`  [INFERRED]
  tests/unit/test_job_engine.py → backend/nfx/jobs/handlers.py
- `test_simulator_handler_returns_only_safe_referential_outcome()` --calls--> `Job`  [INFERRED]
  tests/unit/test_fiscal_simulators.py → backend/nfx/jobs/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Operational Workflow** — _codex_skills_graphify_skill_document, _codex_skills_graphify_references_query_document, _codex_skills_graphify_references_update_document [INFERRED 0.85]
- **NFX Implementation Phases** — p0_fundacao, p1_nucleo_seguro, p2_empresas_certificados, p3_jobs_simuladores, p4_ingestao_comum, p5_nfe, p6_nfse_adn, p7_consulta_artefatos, p8_zip_dashboard_retencao, p9_operacao_piloto [EXTRACTED 1.00]
- **NFX Core Documentation** — prd_nfx_inov, architecture_nfx_inov, implementation_plan [EXTRACTED 1.00]
- **Docker Infrastructure Stack** — docker_compose_app, docker_compose_test, docker_compose_dev [EXTRACTED 0.95]
- **Fiscal Ingestion Flow** — specs_p3_fiscal_adapter_simulation_and_fixtures_fiscal_adapter_port, specs_p4_fiscal_document_ingestion_and_integrity_document, specs_p1_object_storage_and_integrity_artifact_storage_service [EXTRACTED 0.90]

## Communities (122 total, 40 thin omitted)

### Community 0 - "identity/services.py"
Cohesion: 0.08
Nodes (81): _admin_event(), _assert_not_last_administrator(), _assert_version(), authenticate(), bootstrap_first_administrator(), change_own_password(), change_user_role(), create_user() (+73 more)

### Community 1 - "MemoryObjectStore"
Cohesion: 0.07
Nodes (39): Artifact, ArtifactState, Meta, Relational reference to one opaque object-store key. The logical key belongs to…, ArtifactConflict, ArtifactError, ArtifactMetrics, ArtifactNotReadable (+31 more)

### Community 2 - "load_settings"
Cohesion: 0.10
Nodes (35): EmptyFiscalSimulator, FiscalDestinationError, FiscalDestinationGuard, RuntimeError, P0 fiscal boundary: validate every destination before a transport can run., Safe rejection that intentionally contains no destination value., The sole initial fiscal transport; it always produces an empty result., Validate the configured URL and every declared redirect before I/O. (+27 more)

### Community 3 - "Graphify Skill Instructions"
Cohesion: 0.13
Nodes (20): Add and Watch Reference, URL Ingestion, Watch Mode, Confidence Audit Trail, Extraction Specification, Extraction Subagent Prompt, Transcription Reference, Whisper Domain Hint (+12 more)

### Community 4 - "Arquitetura técnica — NFX INOV"
Cohesion: 0.04
Nodes (46): 11. Organização do repositório, 12. Stack selecionada e justificativa, 13. Alternativas consideradas e rejeitadas, 14. Responsabilidade e propriedade de estado, 15. Estratégia de dados e persistência, 16. Responsabilidades do PostgreSQL, 17. Responsabilidades do armazenamento de objetos, 18. Identidade fiscal de documentos (+38 more)

### Community 5 - "Plano de implementação — NFX INOV"
Cohesion: 0.04
Nodes (44): 10. Fases detalhadas e backlog estável, 11. Dependências, caminho crítico e paralelismo, 12. Estratégia de testes e validação, 13. Estratégia de segurança fiscal, 14. Banco e migrações, 15. Sequência de frontend, 16. Observabilidade, backup e restore, 17. Mapa de specs (+36 more)

### Community 6 - "nfx/models.py"
Cohesion: 0.06
Nodes (42): AuditEvent, AuditChain, AuditEvent, Meta, The single stream serializes appends without allowing event rewrites., AuditUnavailable, AuditVerifier, _canonical() (+34 more)

### Community 7 - "dependencies.py"
Cohesion: 0.05
Nodes (44): Append-only audit trail, integrity verifier, and administrative query boundary., Certificate lifecycle and envelope-encryption domain boundary., Company lifecycle, flow configuration, and public enrichment boundary., Identity boundary (no domain implementation in P0)., dependencies_from_environment(), DependencyCheck, _object_probe(), _postgres_probe() (+36 more)

### Community 8 - "certificates/services.py"
Cohesion: 0.07
Nodes (70): ArtifactStorageService, ObjectStore, Protocol, Creates pending metadata, verifies bytes, and finalizes atomically., Certificate, CertificateState, Meta, Certificate metadata plus ciphertext references; plaintext never persists. (+62 more)

### Community 9 - "Administração de usuários"
Cohesion: 0.05
Nodes (41): P1 Núcleo seguro, P2 Empresas e certificados, P3 Jobs e simuladores, P4 Ingestão comum, P5 NF-e, P6 NFS-e/ADN, P7 Consulta e artefatos, Aceite e DoD (+33 more)

### Community 10 - "companies/services.py"
Cohesion: 0.07
Nodes (86): OpenCnpjClient, OpenCnpjResponse, A safe adapter value; payload is public data and never fiscal authority., The only input exposed to OpenCNPJ is the normalized CNPJ., Default local/runtime adapter until an approved public endpoint is configured., UnavailableOpenCnpjClient, AuditService, CompanyMetrics (+78 more)

### Community 11 - "devDependencies"
Cohesion: 0.06
Nodes (32): eslint, @eslint/js, eslint-plugin-react-hooks, dependencies, react, react-dom, vite, @vitejs/plugin-react (+24 more)

### Community 12 - "_HttpResponse"
Cohesion: 0.19
Nodes (6): HttpOpenCnpjClient, _HttpResponse, Protocol, Optional public-source transport with an injected opener for tests., CorrelationIdMiddleware, HttpRequest

### Community 13 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Ensure graphify is installed, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 14 - "PRD — NFX INOV"
Cohesion: 0.08
Nodes (24): 10. Ciclo de vida de empresa, 11. Ciclo de vida de certificado, 13. Retenção e exclusão, 14. Auditoria, 15. Backup e recuperação, 16. Requisitos operacionais e observabilidade, 17. Requisitos não funcionais, 18. Estados de erro, vazio, bloqueio e degradação (+16 more)

### Community 15 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+13 more)

### Community 16 - "JobEngine"
Cohesion: 0.09
Nodes (21): configure_logging(), JsonFormatter, JobEngine, process_one(), Reclaim leases and report queued work due for a worker., Run one registered handler, finalizing only through the lease contract., Owns all durable state transitions for background jobs., run_scheduler_loop() (+13 more)

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
Cohesion: 0.20
Nodes (9): App(), AuditEvent, Certificate, Company, CompanyFlow, ManagedUser, root, statusLabel() (+1 more)

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
Cohesion: 0.29
Nodes (7): Technical Architecture - NFX INOV, Audit Chain Mechanism, Infrastructure Configuration Module, Product Requirements Document - NFX INOV, Spec: P0 Project Foundation, Spec: P0 Safe Configuration, Spec: P1 Audit Foundation

### Community 31 - "Job"
Cohesion: 0.13
Nodes (22): Job, JobPolicy, Meta, Versioned retry policy selected by a job and retained for its lifetime., A safe, referential unit of background work and its current lease., InvalidJobPayload, InvalidTransition, JobEngineError (+14 more)

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
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Contratos e dados Proposed, Dashboard e saúde operacional, Falhas e testes, Metadados, Propósito e resultado, UI, autorização e observabilidade

### Community 40 - "Backup e restauração comprovada"
Cohesion: 0.25
Nodes (7): Aceite e DoD, Backup e restauração comprovada, Estado e contratos Proposed, Metadados, Propósito, baseline e exceção, Segurança, observabilidade e falhas, Testes e evidência

### Community 41 - "Exclusão definitiva controlada"
Cohesion: 0.25
Nodes (8): Aceite e DoD, Baseline, escopo e gate local, Estado e contrato Proposed, Exclusão definitiva controlada, Falhas, recovery e testes, Metadados, Propósito e resultado, UI, segurança e observabilidade

### Community 42 - "Runtime interno e HTTPS"
Cohesion: 0.25
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Decisões e configuração Proposed, Metadados, Propósito e resultado, Runtime interno e HTTPS, Segurança, observabilidade e falhas, Testes, rollback e evidência

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

### Community 66 - "jobs/policy.py"
Cohesion: 0.22
Nodes (14): AmbiguousPolicy, InvalidPolicy, PolicyError, PolicyNotFound, datetime, RuntimeError, ValueError, Validated selection and creation of versioned job policies. (+6 more)

### Community 67 - "HandlerOutcome"
Cohesion: 0.33
Nodes (5): Translate a synthetic response at the generic jobs handler seam., HandlerOutcome, Any, datetime, Safe, classified result returned by a registered handler.

### Community 71 - "test_job_engine.py"
Cohesion: 0.29
Nodes (15): create_policy(), FrozenClock, datetime, django_db, test_claim_renew_complete_and_stale_owner_rejection_are_atomic(), test_cooldown_precedes_local_backoff_and_permanent_outcome_blocks(), test_effective_policy_cannot_change_after_job_is_scheduled(), test_enqueue_is_idempotent_only_while_the_key_is_active() (+7 more)

### Community 88 - "jobs/services.py"
Cohesion: 0.18
Nodes (12): clear_handlers(), get_handler(), Explicit handler boundary used by the worker and synthetic tests., register_handler(), JobOutcomeKind, JobState, Transactional contracts for durable jobs, leases, and safe handlers., JobHandler (+4 more)

### Community 90 - "Build Pass"
Cohesion: 0.12
Nodes (16): Build Pass, Close the selected issue, Create one focused commit, Dependencies and external documentation, Establish the baseline, Final verification, Graphify, Handle newly discovered problems (+8 more)

### Community 91 - "Specification Pass"
Cohesion: 0.15
Nodes (12): Create or update specifications, Determine the required specification set, Existing and implemented specs, Final verification, Graphify, Operating mode, Repository inspection, Scope boundaries (+4 more)

### Community 92 - "Issue Creation Pass"
Cohesion: 0.17
Nodes (11): Acceptance criteria, Create one issue, Final verification, Graphify, Implementation guidance quality, Issue Creation Pass, Operating mode, Repository inspection (+3 more)

### Community 93 - "0002_-_policy-driven-job-retry-and-blocking.md"
Cohesion: 0.25
Nodes (7): Acceptance Criteria, Description, Implementation Plan, Out of Scope, References, Resolution, Tests

### Community 94 - "Planning Pass"
Cohesion: 0.18
Nodes (10): Final verification, Graphify, Operating mode, Planning Pass, Repository inspection, Required analysis, Scope boundaries, Sources of truth (+2 more)

### Community 95 - "0003_-_deterministic-fiscal-simulators-and-fixtures.md"
Cohesion: 0.25
Nodes (7): Acceptance Criteria, Description, Implementation Plan, Out of Scope, References, Resolution, Tests

### Community 96 - "test_jobs.py"
Cohesion: 0.70
Nodes (4): django_db, test_job_migration_installs_claim_lease_target_and_idempotency_indexes(), test_policy_is_persisted_and_referenced_by_job(), test_two_postgres_workers_cannot_claim_one_job()

### Community 100 - "0001_-_durable-job-queue-and-leases.md"
Cohesion: 0.25
Nodes (7): Acceptance Criteria, Description, Implementation Plan, Out of Scope, References, Resolution, Tests

### Community 111 - "simulation.py"
Cohesion: 0.07
Nodes (53): AdnSimulator, build_scenario(), _code(), Coverage, DeterministicFiscalSimulator, FakeFiscalTransport, FiscalAdapter, FiscalFamily (+45 more)

### Community 112 - "Update Reference"
Cohesion: 0.20
Nodes (10): CLAUDE.md Integration, Hooks Reference, Post-Commit Hook, Change Detection, Deleted Source Pruning, Directed Graph Preservation, Update Reference, Incremental Update (+2 more)

### Community 113 - "0000_-_ISSUE_TEMPLATE.md"
Cohesion: 0.29
Nodes (6): Acceptance Criteria, Description, Implementation Plan, References, Resolution, Tests

### Community 117 - "/graphify"
Cohesion: 0.20
Nodes (9): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Usage (+1 more)

### Community 118 - "Exports Reference"
Cohesion: 0.25
Nodes (8): Exports Reference, FalkorDB Export, GraphML Export, MCP Server, Neo4j Export, SVG Export, Token Reduction Benchmark, Wiki Export

### Community 119 - "Query Reference"
Cohesion: 0.33
Nodes (7): BFS Traversal, Query Reference, Query Feedback Loop, Graph Explain, Shortest Path, Constrained Query Expansion, Knowledge Graph

### Community 120 - "GitHub and Merge Reference"
Cohesion: 0.83
Nodes (4): Cross-Repository Graph Merge, GitHub and Merge Reference, GitHub Clone, Monorepo Graph Merge

## Knowledge Gaps
- **545 isolated node(s):** `Meta`, `Meta`, `InitialCollectionRequestState`, `Meta`, `Migration` (+540 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HandlerOutcome` connect `HandlerOutcome` to `test_job_engine.py`, `simulation.py`, `JobEngine`, `jobs/services.py`, `Job`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `Job` connect `Job` to `jobs/services.py`, `JobEngine`, `nfx/models.py`, `simulation.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `AuditService` connect `companies/services.py` to `certificates/services.py`, `identity/services.py`, `nfx/models.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `AuditService` (e.g. with `CertificateAccessDenied` and `CertificateAlreadyAssigned`) actually correct?**
  _`AuditService` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `Action` (e.g. with `CertificateAccessDenied` and `CertificateAlreadyAssigned`) actually correct?**
  _`Action` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `ArtifactStorageService` (e.g. with `Artifact` and `ArtifactState`) actually correct?**
  _`ArtifactStorageService` has 17 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Meta`, `Meta`, `InitialCollectionRequestState` to the rest of the system?**
  _545 weakly-connected nodes found - possible documentation gaps or missing edges._