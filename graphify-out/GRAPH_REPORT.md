# Graph Report - workspace  (2026-08-10)

## Corpus Check
- 213 files · ~118,747 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2203 nodes · 5068 edges · 168 communities (125 shown, 43 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 595 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `75d8bfa1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- identity/services.py
- Artifact
- load_settings
- Graphify Skill Instructions
- Arquitetura técnica — NFX INOV
- Plano de implementação — NFX INOV
- audit/services.py
- status.py
- certificates/services.py
- FiscalOutcome
- AuditService
- devDependencies
- documents/services.py
- What You Must Do When Invoked
- PRD — NFX INOV
- compilerOptions
- HeartbeatService
- 9. Requisitos funcionais e regras de negócio
- Persistência relacional e migrações
- Fundação de auditoria append-only
- Autenticação, sessões, RBAC e shell web
- Ingestão fiscal comum e integridade
- CompaniesSection.tsx
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
- MemoryObjectStore
- 19. Jornadas principais
- Renderização de DANFE e DANFSe
- Dashboard e saúde operacional
- Backup e restauração comprovada
- Exclusão definitiva controlada
- adn.py
- Fundação P0
- collection/services.py
- schema_status
- graphify reference: query, path, explain
- test_safe_configuration.py
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
- 0005_-_manual-collection-control.md
- urls.py
- dependencies.py
- exports/__init__.py
- JobEngine
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
- Operating Principles
- 0000_-_ISSUE_TEMPLATE.md
- jobs/__init__.py
- 0008_durable_jobs.py
- loop.sh
- operational
- 0006_-_fiscal-document-identity-and-persistence.md
- 0007_-_remove_literal-secrets-from-env-example.md
- 0008_-_reproducible-clean-checkout-build.md
- .save
- Update Reference
- 0004_-_job-observability-and-initial-health.md
- /graphify
- 0010_process_heartbeats.py
- OPERATIONS.md
- fiscal.py
- ingestion.py
- Exports Reference
- Runtime interno e HTTPS
- Query Reference
- Hardening, ameaças e testes de falha
- Piloto interno e homologação segregada
- Índice de implementação das specs
- DependencyCheck
- GitHub and Merge Reference
- MemoryObjectStore
- ArtifactStorageService
- integration/test_document_status.py
- 0011_document_documentevent_documenteventevidence_and_more.py
- 0012_companyflow_blocked_reason_and_more.py
- test_build_contract.py
- 0009_-_durable-ingestion-pipeline-and-cursor.md
- 0010_-_minimum-document-status-and-list-contract.md
- HandlerOutcome
- 10. Fases detalhadas e backlog estável
- Administração de usuários
- Consulta de documentos e download individual
- 0013_ingestionpage_ingestioncheckpoint_receivedunit_and_more.py
- Elegibilidade de retenção e prévia administrativa
- P4 Ingestão comum
- 0011_-_frontend-architecture-refactor.md
- test_documents.py
- 0012_-_fiscal-ingestion-failure-state-matrix.md
- 0013_-_nfe-distribution-adapter-and-simulator.md
- 0014_-_adn-distribution-adapter-and-coverage.md
- 0015_-_document-consultation-and-secure-individual-download.md
- 0016_-_internal-runtime-and-https.md
- 0017_-_verifiable-backup-and-isolated-restore.md
- 0018_-_initial-dashboard-and-operational-health.md
- 0019_-_retention-eligibility-and-preview.md
- 0014_ingestion_failure_state_contract.py
- Distribuição NF-e e manifestação
- README.md
- Distribuição NFS-e/ADN e cobertura
- FiscalIdentity
- 0015_adn_coverage_snapshot.py

## God Nodes (most connected - your core abstractions)
1. `AuditService` - 80 edges
2. `ArtifactStorageService` - 65 edges
3. `FiscalResponse` - 62 edges
4. `Action` - 56 edges
5. `FiscalUnit` - 50 edges
6. `IngestionContext` - 50 edges
7. `Artifact` - 48 edges
8. `HandlerOutcome` - 47 edges
9. `Arquitetura técnica — NFX INOV` - 47 edges
10. `FiscalOutcome` - 43 edges

## Surprising Connections (you probably didn't know these)
- `MemoryObjectStore` --uses--> `AdnFlow`  [INFERRED]
  tests/integration/test_adn_distribution.py → backend/nfx/adapters/adn.py
- `MemoryObjectStore` --uses--> `AdnPosition`  [INFERRED]
  tests/integration/test_adn_distribution.py → backend/nfx/adapters/adn.py
- `MemoryObjectStore` --uses--> `AdnDistributionRequest`  [INFERRED]
  tests/integration/test_adn_distribution.py → backend/nfx/adapters/adn.py
- `MemoryObjectStore` --uses--> `AdnDistributionSimulator`  [INFERRED]
  tests/integration/test_adn_distribution.py → backend/nfx/adapters/adn.py
- `MemoryObjectStore` --uses--> `NFeFlow`  [INFERRED]
  tests/integration/test_ingestion.py → backend/nfx/adapters/nfe.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Operational Workflow** — _codex_skills_graphify_skill_document, _codex_skills_graphify_references_query_document, _codex_skills_graphify_references_update_document [INFERRED 0.85]
- **NFX Implementation Phases** — p0_fundacao, p1_nucleo_seguro, p2_empresas_certificados, p3_jobs_simuladores, p4_ingestao_comum, p5_nfe, p6_nfse_adn, p7_consulta_artefatos, p8_zip_dashboard_retencao, p9_operacao_piloto [EXTRACTED 1.00]
- **NFX Core Documentation** — prd_nfx_inov, architecture_nfx_inov, implementation_plan [EXTRACTED 1.00]
- **Docker Infrastructure Stack** — docker_compose_app, docker_compose_test, docker_compose_dev [EXTRACTED 0.95]
- **Fiscal Ingestion Flow** — specs_p3_fiscal_adapter_simulation_and_fixtures_fiscal_adapter_port, specs_p4_fiscal_document_ingestion_and_integrity_document, specs_p1_object_storage_and_integrity_artifact_storage_service [EXTRACTED 0.90]

## Communities (168 total, 43 thin omitted)

### Community 0 - "identity/services.py"
Cohesion: 0.07
Nodes (90): IdentitySession, LoginThrottle, Meta, A keyed subject digest avoids retaining an account identifier on failed logins., Role, User, _admin_event(), _assert_not_last_administrator() (+82 more)

### Community 1 - "Artifact"
Cohesion: 0.09
Nodes (27): Artifact, ArtifactState, Meta, Relational reference to one opaque object-store key. The logical key belongs to…, ArtifactConflict, ArtifactError, ArtifactMetrics, ArtifactNotReadable (+19 more)

### Community 2 - "load_settings"
Cohesion: 0.25
Nodes (15): ConfigurationError, _duration_seconds(), _error(), load_settings(), OperationalSettings, RuntimeError, Validated, fail-closed process configuration. Only this module reads deployment…, A safe configuration error: its message never contains supplied values. (+7 more)

### Community 3 - "Graphify Skill Instructions"
Cohesion: 0.13
Nodes (20): Add and Watch Reference, URL Ingestion, Watch Mode, Confidence Audit Trail, Extraction Specification, Extraction Subagent Prompt, Transcription Reference, Whisper Domain Hint (+12 more)

### Community 4 - "Arquitetura técnica — NFX INOV"
Cohesion: 0.04
Nodes (46): 11. Organização do repositório, 12. Stack selecionada e justificativa, 13. Alternativas consideradas e rejeitadas, 14. Responsabilidade e propriedade de estado, 15. Estratégia de dados e persistência, 16. Responsabilidades do PostgreSQL, 17. Responsabilidades do armazenamento de objetos, 18. Identidade fiscal de documentos (+38 more)

### Community 5 - "Plano de implementação — NFX INOV"
Cohesion: 0.08
Nodes (26): 11. Dependências, caminho crítico e paralelismo, 12. Estratégia de testes e validação, 13. Estratégia de segurança fiscal, 14. Banco e migrações, 15. Sequência de frontend, 16. Observabilidade, backup e restore, 17. Mapa de specs, 18. Rastreabilidade do PRD (+18 more)

### Community 6 - "audit/services.py"
Cohesion: 0.08
Nodes (35): AuditEvent, AuditChain, AuditEvent, Meta, The single stream serializes appends without allowing event rewrites., AuditUnavailable, AuditVerifier, _canonical() (+27 more)

### Community 7 - "status.py"
Cohesion: 0.11
Nodes (31): ReceivedUnitState, Document, Fiscal identity and metadata; payload bytes remain owned by artifacts., _aggregate_status(), collection_status(), CollectionStatus, _document_payload(), DocumentListParams (+23 more)

### Community 8 - "certificates/services.py"
Cohesion: 0.07
Nodes (72): object_store_from_environment(), ObjectStore, Protocol, Build the adapter at the infrastructure edge, not in a domain caller., Certificate, CertificateState, Meta, Certificate metadata plus ciphertext references; plaintext never persists. (+64 more)

### Community 9 - "FiscalOutcome"
Cohesion: 0.09
Nodes (50): AdnAuditCallback, AuditCallback, AdnDistributionMetrics, AdnDistributionMetricsSnapshot, AdnDistributionPolicy, Versioned synthetic policy; official limits and layouts remain open., _code(), _flow() (+42 more)

### Community 10 - "AuditService"
Cohesion: 0.06
Nodes (89): HttpOpenCnpjClient, _HttpResponse, OpenCnpjClient, OpenCnpjResponse, Protocol, A safe adapter value; payload is public data and never fiscal authority., The only input exposed to OpenCNPJ is the normalized CNPJ., Optional public-source transport with an injected opener for tests. (+81 more)

### Community 11 - "devDependencies"
Cohesion: 0.06
Nodes (32): eslint, @eslint/js, eslint-plugin-react-hooks, dependencies, react, react-dom, vite, @vitejs/plugin-react (+24 more)

### Community 12 - "documents/services.py"
Cohesion: 0.23
Nodes (22): _artifact(), _artifact_size(), _audit(), derive_competence(), DocumentInput, DocumentPersistenceResult, DocumentPersistenceStatus, _identity_key() (+14 more)

### Community 13 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Ensure graphify is installed, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 14 - "PRD — NFX INOV"
Cohesion: 0.08
Nodes (24): 10. Ciclo de vida de empresa, 11. Ciclo de vida de certificado, 13. Retenção e exclusão, 14. Auditoria, 15. Backup e recuperação, 16. Requisitos operacionais e observabilidade, 17. Requisitos não funcionais, 18. Estados de erro, vazio, bloqueio e degradação (+16 more)

### Community 15 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+13 more)

### Community 16 - "HeartbeatService"
Cohesion: 0.10
Nodes (24): ensure_collection_handler(), configure_logging(), JsonFormatter, Any, Emit bounded structured fields without making logging part of a state…, safe_log(), HeartbeatService, Write only this process's identity and read the freshest component evidence. (+16 more)

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

### Community 22 - "CompaniesSection.tsx"
Cohesion: 0.05
Nodes (63): App(), Section, listAuditEvents(), AuditSection(), AuditSectionProps, AuditEvent, getSession(), login() (+55 more)

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
Cohesion: 0.12
Nodes (22): Job, A safe, referential unit of background work and its current lease., InvalidJobPayload, InvalidTransition, JobEngineError, LeaseLost, process_one(), Any (+14 more)

### Community 33 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 34 - "Simuladores fiscais e fixtures seguras"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Contratos Proposed e cenários, Metadados, Observabilidade, falha e testes, Propósito e resultado, Segurança e fixtures, Simuladores fiscais e fixtures seguras

### Community 35 - "Controle manual de coleta"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Controle manual de coleta, Estado e contratos Proposed, Falhas, observabilidade e testes, Metadados, Propósito e resultado, UI, permissões e comportamento visível

### Community 36 - "MemoryObjectStore"
Cohesion: 0.15
Nodes (18): MemoryObjectStore, BytesIO, django_db, fixture, MonkeyPatch, parametrize, Exercise the production S3 adapter against the isolated Compose bucket., Synthetic isolated object store; it deliberately exposes fault injection. (+10 more)

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

### Community 42 - "adn.py"
Cohesion: 0.11
Nodes (31): AdnDistributionAdapter, AdnDistributionAudit, AdnDistributionError, AdnDistributionRequest, AdnDistributionResult, AdnDistributionSimulator, AdnFlow, AdnPosition (+23 more)

### Community 43 - "Fundação P0"
Cohesion: 0.29
Nodes (6): Configuração segura e isolamento fiscal (P0-02/P0-04), Contratos dos comandos, Decisões Proposed adotadas, Fundação P0, Persistência e migrações (P1-01), Scope boundary

### Community 44 - "collection/services.py"
Cohesion: 0.07
Nodes (70): CollectionExecution, CollectionExecutionState, CollectionOrigin, CollectionScope, IngestionCheckpoint, InitialCollectionRequest, InitialCollectionRequestState, Meta (+62 more)

### Community 45 - "schema_status"
Cohesion: 0.10
Nodes (25): _migration_names(), MigrationOutcome, RuntimeError, Schema compatibility and serialized migration support. This module deliberately…, Raised when the database cannot safely serve this application version., Compare the installed NFX migration graph with its persisted history., Run Django migrations once at a time and report only safe metadata., schema_status() (+17 more)

### Community 46 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 47 - "test_safe_configuration.py"
Cohesion: 0.24
Nodes (17): environment(), parametrize, Path, template_assignments(), test_both_secret_sources_are_rejected_and_certificate_file_is_supported(), test_certificate_master_key_requires_external_base64url_32_byte_material(), test_empty_allowlist_is_not_valid_for_runtime(), test_environment_template_uses_external_secret_placeholders_once() (+9 more)

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

### Community 67 - "0005_-_manual-collection-control.md"
Cohesion: 0.20
Nodes (9): Acceptance Criteria, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References, Resolution (+1 more)

### Community 68 - "urls.py"
Cohesion: 0.13
Nodes (11): Append-only audit trail, integrity verifier, and administrative query boundary., Certificate lifecycle and envelope-encryption domain boundary., Durable collection request boundary used by certificate activation., Company lifecycle, flow configuration, and public enrichment boundary., Document boundary (no domain implementation in P0)., Identity boundary (no domain implementation in P0)., index(), live() (+3 more)

### Community 69 - "dependencies.py"
Cohesion: 0.22
Nodes (9): dependencies_from_environment(), _object_probe(), _postgres_probe(), _schema_probe(), ServiceDependencies, Command, BaseCommand, test_dependency_check_is_injectable_and_reports_only_service_names() (+1 more)

### Community 71 - "JobEngine"
Cohesion: 0.25
Nodes (17): create_policy(), JobEngine, Owns all durable state transitions for background jobs., FrozenClock, datetime, django_db, test_claim_renew_complete_and_stale_owner_rejection_are_atomic(), test_cooldown_precedes_local_backoff_and_permanent_outcome_blocks() (+9 more)

### Community 88 - "jobs/services.py"
Cohesion: 0.11
Nodes (20): clear_handlers(), get_handler(), Explicit handler boundary used by the worker and synthetic tests., register_handler(), JobOutcomeKind, JobPolicy, JobState, Meta (+12 more)

### Community 90 - "Build Pass"
Cohesion: 0.12
Nodes (15): Baseline and TDD, Build Pass, Closing the issue, Deliverable, Dependencies and third-party docs, Implementing, One focused commit, Problems outside the issue (+7 more)

### Community 91 - "Specification Pass"
Cohesion: 0.22
Nodes (8): Deliverables, Determine the required specification set, Report, Scope, Specification Pass, Synchronize `IMPLEMENTATION_PLAN.md`, Update `specs/README.md`, Writing specs

### Community 92 - "Issue Creation Pass"
Cohesion: 0.25
Nodes (7): Deliverable, Issue Creation Pass, Report, Scope, Selecting the next issue, This pass runs repeatedly — design for that, Writing the issue

### Community 93 - "0002_-_policy-driven-job-retry-and-blocking.md"
Cohesion: 0.25
Nodes (7): Acceptance Criteria, Description, Implementation Plan, Out of Scope, References, Resolution, Tests

### Community 94 - "Planning Pass"
Cohesion: 0.25
Nodes (7): Deliverable, Planning Pass, Report, Required analysis, Scope, Technical decisions, Updating `IMPLEMENTATION_PLAN.md`

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
Cohesion: 0.08
Nodes (40): build_scenario(), _code(), DeterministicFiscalSimulator, FakeFiscalTransport, FiscalRequest, make_simulator_handler(), NFeSimulator, Any (+32 more)

### Community 112 - "Operating Principles"
Cohesion: 0.22
Nodes (8): File reading strategy, Final verification (every pass), Graphify, Non-interactive mode, Operating Principles, Repository inspection, Scope discipline, Sources of truth

### Community 113 - "0000_-_ISSUE_TEMPLATE.md"
Cohesion: 0.29
Nodes (6): Acceptance Criteria, Description, Implementation Plan, References, Resolution, Tests

### Community 116 - "loop.sh"
Cohesion: 0.30
Nodes (8): err(), info(), log(), ok(), print_summary(), render_stream(), loop.sh script, warn()

### Community 117 - "operational"
Cohesion: 0.25
Nodes (8): operational(), HttpRequest, JsonResponse, require_GET, JobObservability, Compute bounded aggregates without mutating jobs or leases., django_db, test_job_metrics_aggregate_safe_durable_states_without_mutating_jobs()

### Community 118 - "0006_-_fiscal-document-identity-and-persistence.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Data, Migration, Compatibility, Security, and Observability Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 119 - "0007_-_remove_literal-secrets-from-env-example.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 120 - "0008_-_reproducible-clean-checkout-build.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 121 - ".save"
Cohesion: 0.50
Nodes (3): Any, Keep the policy captured at enqueue time immutable for this job., Keep effective policy versions immutable after they are published.

### Community 122 - "Update Reference"
Cohesion: 0.20
Nodes (10): CLAUDE.md Integration, Hooks Reference, Post-Commit Hook, Change Detection, Deleted Source Pruning, Directed Graph Preservation, Update Reference, Incremental Update (+2 more)

### Community 123 - "0004_-_job-observability-and-initial-health.md"
Cohesion: 0.25
Nodes (7): Acceptance Criteria, Description, Implementation Plan, Out of Scope, References, Resolution, Tests

### Community 124 - "/graphify"
Cohesion: 0.20
Nodes (9): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Usage (+1 more)

### Community 127 - "fiscal.py"
Cohesion: 0.17
Nodes (11): EmptyFiscalSimulator, FiscalDestinationError, FiscalDestinationGuard, RuntimeError, P0 fiscal boundary: validate every destination before a transport can run., Safe rejection that intentionally contains no destination value., The sole initial fiscal transport; it always produces an empty result., Validate the configured URL and every declared redirect before I/O. (+3 more)

### Community 128 - "ingestion.py"
Cohesion: 0.08
Nodes (49): FiscalUnit, Synthetic identity and hash references; no fiscal content is carried., classify_page_response(), classify_unit_treatments(), _default_metadata(), _document_family(), FiscalIngestionService, ingest_collection_response() (+41 more)

### Community 129 - "Exports Reference"
Cohesion: 0.25
Nodes (8): Exports Reference, FalkorDB Export, GraphML Export, MCP Server, Neo4j Export, SVG Export, Token Reduction Benchmark, Wiki Export

### Community 130 - "Runtime interno e HTTPS"
Cohesion: 0.25
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Decisões e configuração Proposed, Metadados, Propósito e resultado, Runtime interno e HTTPS, Segurança, observabilidade e falhas, Testes, rollback e evidência

### Community 131 - "Query Reference"
Cohesion: 0.33
Nodes (7): BFS Traversal, Query Reference, Query Feedback Loop, Graph Explain, Shortest Path, Constrained Query Expansion, Knowledge Graph

### Community 132 - "Hardening, ameaças e testes de falha"
Cohesion: 0.29
Nodes (7): Aceite e DoD, Baseline, escopo e não escopo, Hardening, ameaças e testes de falha, Metadados, Método e contratos de evidência, Propósito e resultado, Testes, observabilidade e capacidade

### Community 133 - "Piloto interno e homologação segregada"
Cohesion: 0.29
Nodes (7): Baseline, escopo e não escopo, Falhas, observabilidade e recovery, Metadados, Piloto interno e homologação segregada, Plano e decisões, Propósito e resultado, Testes/evidências e aceite

### Community 134 - "Índice de implementação das specs"
Cohesion: 0.29
Nodes (7): Autoridade, baseline e regra de uso, Como escolher a próxima spec, Decisões Open, Blocked, Deferred e Proposed, Fluxo de entrega, Ordem, cobertura e dependências diretas, Paralelismo e conclusão de fase, Índice de implementação das specs

### Community 135 - "DependencyCheck"
Cohesion: 0.15
Nodes (13): DependencyCheck, ComponentHealth, JobMetricsSnapshot, OperationalHealth, datetime, timedelta, Evaluate dependency, process freshness, and overdue durable backlog., _components() (+5 more)

### Community 136 - "GitHub and Merge Reference"
Cohesion: 0.83
Nodes (4): Cross-Repository Graph Merge, GitHub and Merge Reference, GitHub Clone, Monorepo Graph Merge

### Community 137 - "MemoryObjectStore"
Cohesion: 0.22
Nodes (10): company(), MemoryObjectStore, BytesIO, django_db, fixture, _request(), storage(), test_actor_and_flow_checkpoints_are_independent() (+2 more)

### Community 138 - "ArtifactStorageService"
Cohesion: 0.25
Nodes (23): FiscalResponse, Typed adapter response containing only safe references and metadata., ArtifactStorageService, Creates pending metadata, verifies bytes, and finalizes atomically., ingest_page(), Convenience port used by workers and deterministic integration tests., company(), _context() (+15 more)

### Community 139 - "integration/test_document_status.py"
Cohesion: 0.35
Nodes (11): _artifact(), _client(), _document(), Company, django_db, parametrize, test_all_authenticated_roles_can_read_the_global_document_scope(), test_document_list_is_authenticated_and_valid_empty_is_not_unavailable() (+3 more)

### Community 142 - "test_build_contract.py"
Cohesion: 0.70
Nodes (4): clean_build_environment(), Path, test_invalid_build_configuration_fails_before_frontend_step(), test_make_build_succeeds_without_services_or_ambient_configuration()

### Community 143 - "0009_-_durable-ingestion-pipeline-and-cursor.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 144 - "0010_-_minimum-document-status-and-list-contract.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 145 - "HandlerOutcome"
Cohesion: 0.36
Nodes (6): Translate a synthetic response at the generic jobs handler seam., collection_handler(), HandlerOutcome, Any, datetime, Safe, classified result returned by a registered handler.

### Community 146 - "10. Fases detalhadas e backlog estável"
Cohesion: 0.18
Nodes (11): 10. Fases detalhadas e backlog estável, P0 — Fundação de projeto e isolamento seguro, P1 — Núcleo seguro, persistente e auditável, P2 — Empresas, cobertura e certificados, P3 — Jobs, scheduler, políticas e simuladores, P4 — Ingestão fiscal comum e integridade, P5 — Adaptador e fluxos NF-e, P6 — Adaptador e fluxos NFS-e/ADN (+3 more)

### Community 147 - "Administração de usuários"
Cohesion: 0.22
Nodes (9): Aceite e DoD, Administração de usuários, Baseline, escopo e não escopo, Decisões de implementação e evidências, Estado, backend, auditoria e segurança, Falhas, testes e recovery, Metadados, Propósito e resultado (+1 more)

### Community 148 - "Consulta de documentos e download individual"
Cohesion: 0.22
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Consulta de documentos e download individual, Dados, índices e contratos Proposed, Falhas e testes, Metadados, Propósito e resultado, Segurança, auditoria e observabilidade (+1 more)

### Community 150 - "Elegibilidade de retenção e prévia administrativa"
Cohesion: 0.22
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos, UI e autorização, Elegibilidade de retenção e prévia administrativa, Metadados, Propósito e resultado, Regras e estado, Segurança, auditoria e observabilidade (+1 more)

### Community 151 - "P4 Ingestão comum"
Cohesion: 0.19
Nodes (8): P0 Fundação, P1 Núcleo seguro, P2 Empresas e certificados, P3 Jobs e simuladores, P4 Ingestão comum, P5 NF-e, P6 NFS-e/ADN, P7 Consulta e artefatos

### Community 152 - "0011_-_frontend-architecture-refactor.md"
Cohesion: 0.20
Nodes (9): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Out of Scope, References, Resolution (+1 more)

### Community 153 - "test_documents.py"
Cohesion: 0.55
Nodes (11): _artifact(), company(), _input(), django_db, fixture, test_concurrent_same_identity_is_one_document_and_two_replays(), test_document_persistence_replay_and_conflict_preserve_evidence(), test_event_replay_and_conflict_preserve_event_evidence() (+3 more)

### Community 154 - "0012_-_fiscal-ingestion-failure-state-matrix.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 155 - "0013_-_nfe-distribution-adapter-and-simulator.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 156 - "0014_-_adn-distribution-adapter-and-coverage.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 157 - "0015_-_document-consultation-and-secure-individual-download.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 158 - "0016_-_internal-runtime-and-https.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 159 - "0017_-_verifiable-backup-and-isolated-restore.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 160 - "0018_-_initial-dashboard-and-operational-health.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 161 - "0019_-_retention-eligibility-and-preview.md"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Dependencies and Notes, Description, Implementation Plan, In Scope, Objective and Expected Outcome, Out of Scope, References (+2 more)

### Community 163 - "Distribuição NF-e e manifestação"
Cohesion: 0.22
Nodes (9): Aceite e DoD, Decisões e contratos, Distribuição NF-e e manifestação, Estado e comportamento, Evidência do incremento P5-01 (issue 0013), Falhas, testes e recovery, Metadados, Propósito, baseline e limites (+1 more)

### Community 165 - "Distribuição NFS-e/ADN e cobertura"
Cohesion: 0.25
Nodes (8): Aceite e DoD, Contratos e estado Proposed, Distribuição NFS-e/ADN e cobertura, Falhas, testes e recovery, Metadados, Propósito, baseline, escopo, Regras e comportamento visível, Segurança, auditoria e observabilidade

### Community 166 - "FiscalIdentity"
Cohesion: 0.57
Nodes (6): FiscalIdentity, select_strongest_identity(), test_compound_identity_is_used_when_no_single_official_id_exists(), test_document_input_rejects_unbounded_or_payload_like_references(), test_identity_without_official_components_is_rejected(), test_strongest_official_identity_is_selected_and_normalized()

## Knowledge Gaps
- **707 isolated node(s):** `Meta`, `Meta`, `Migration`, `Migration`, `Migration` (+702 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **43 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AuditService` connect `AuditService` to `ingestion.py`, `identity/services.py`, `audit/services.py`, `FiscalIdentity`, `certificates/services.py`, `adn.py`, `collection/services.py`, `documents/services.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `ArtifactStorageService` connect `ArtifactStorageService` to `ingestion.py`, `Artifact`, `MemoryObjectStore`, `certificates/services.py`, `MemoryObjectStore`, `adn.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `HandlerOutcome` connect `HandlerOutcome` to `ingestion.py`, `JobEngine`, `FiscalOutcome`, `adn.py`, `ArtifactStorageService`, `collection/services.py`, `simulation.py`, `jobs/services.py`, `Job`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `AuditService` (e.g. with `CertificateAccessDenied` and `CertificateAlreadyAssigned`) actually correct?**
  _`AuditService` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `ArtifactStorageService` (e.g. with `Artifact` and `ArtifactState`) actually correct?**
  _`ArtifactStorageService` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `FiscalResponse` (e.g. with `AdnDistributionAdapter` and `AdnDistributionAudit`) actually correct?**
  _`FiscalResponse` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `Action` (e.g. with `CertificateAccessDenied` and `CertificateAlreadyAssigned`) actually correct?**
  _`Action` has 39 INFERRED edges - model-reasoned connections that need verification._