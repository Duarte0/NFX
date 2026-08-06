# Graph Report - workspace  (2026-08-04)

## Corpus Check
- 105 files · ~49,557 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 863 nodes · 1131 edges · 82 communities (59 shown, 23 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 45 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b3ca0290`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Arquitetura técnica — NFX INOV
- load_settings
- Plano de implementação — NFX INOV
- schema_status
- devDependencies
- http.py
- dependencies.py
- What You Must Do When Invoked
- PRD — NFX INOV
- compilerOptions
- 9. Requisitos funcionais e regras de negócio
- Ingestão fiscal comum e integridade
- Fundação do projeto
- Configuração segura e isolamento fiscal de testes
- Fundação de auditoria append-only
- Armazenamento de objetos e integridade
- Persistência relacional e migrações
- Certificados A1 e criptografia por envelope
- Empresas, fluxos e enriquecimento público
- Jobs duráveis, leases, políticas e observabilidade inicial
- Consulta de documentos e download individual
- Elegibilidade de retenção e prévia administrativa
- Exportação ZIP assíncrona
- graphify reference: extra exports and benchmark
- Autenticação, sessões, RBAC e shell web
- Administração de usuários
- Simuladores fiscais e fixtures seguras
- Controle manual de coleta
- Distribuição NF-e e manifestação
- Distribuição NFS-e/ADN e cobertura
- Dashboard e saúde operacional
- Exclusão definitiva controlada
- Runtime interno e HTTPS
- ArtifactStorageService
- Renderização de DANFE e DANFSe
- Backup e restauração comprovada
- Hardening, ameaças e testes de falha
- Piloto interno e homologação segregada
- Índice de implementação das specs
- graphify reference: query, path, explain
- Fundação P0
- Migration
- 10. Arquitetura de componentes
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- smoke.sh
- test-integration.sh
- AGENTS.md
- adapters/__init__.py
- artifacts/__init__.py
- audit/services.py
- certificates/__init__.py
- collection/__init__.py
- companies/__init__.py
- documents/__init__.py
- exports/__init__.py
- identity/services.py
- infrastructure/__init__.py
- nfx/__init__.py
- migrations/__init__.py
- operations/__init__.py
- retention/__init__.py
- extraction-spec.md
- main.tsx
- 19. Jornadas principais
- 7. Usuários e papéis
- 12. Autenticação e autorização
- 0002_artifact.py
- 0003_identity.py
- 0004_audit_foundation.py

## God Nodes (most connected - your core abstractions)
1. `Arquitetura técnica — NFX INOV` - 47 edges
2. `PRD — NFX INOV` - 28 edges
3. `Plano de implementação — NFX INOV` - 26 edges
4. `ArtifactStorageService` - 21 edges
5. `MemoryObjectStore` - 21 edges
6. `Artifact` - 20 edges
7. `load_settings()` - 20 edges
8. `compilerOptions` - 16 edges
9. `dependencies_from_environment()` - 14 edges
10. `schema_status()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `test_minio_adapter_writes_and_verifies_synthetic_bytes()` --calls--> `dependencies_from_environment()`  [INFERRED]
  tests/integration/test_artifact_storage.py → backend/nfx/infrastructure/dependencies.py
- `MemoryObjectStore` --uses--> `ArtifactState`  [INFERRED]
  tests/integration/test_artifact_storage.py → backend/nfx/artifacts/models.py
- `MemoryObjectStore` --uses--> `Artifact`  [INFERRED]
  tests/integration/test_artifact_storage.py → backend/nfx/artifacts/models.py
- `MemoryObjectStore` --uses--> `ArtifactNotReadable`  [INFERRED]
  tests/integration/test_artifact_storage.py → backend/nfx/artifacts/storage.py
- `MemoryObjectStore` --uses--> `ArtifactTooLarge`  [INFERRED]
  tests/integration/test_artifact_storage.py → backend/nfx/artifacts/storage.py

## Import Cycles
- None detected.

## Communities (82 total, 23 thin omitted)

### Community 0 - "Arquitetura técnica — NFX INOV"
Cohesion: 0.04
Nodes (46): 11. Organização do repositório, 12. Stack selecionada e justificativa, 13. Alternativas consideradas e rejeitadas, 14. Responsabilidade e propriedade de estado, 15. Estratégia de dados e persistência, 16. Responsabilidades do PostgreSQL, 17. Responsabilidades do armazenamento de objetos, 18. Identidade fiscal de documentos (+38 more)

### Community 1 - "load_settings"
Cohesion: 0.11
Nodes (32): EmptyFiscalSimulator, FiscalDestinationError, FiscalDestinationGuard, RuntimeError, P0 fiscal boundary: validate every destination before a transport can run., Safe rejection that intentionally contains no destination value., The sole initial fiscal transport; it always produces an empty result., Validate the configured URL and every declared redirect before I/O. (+24 more)

### Community 2 - "Plano de implementação — NFX INOV"
Cohesion: 0.05
Nodes (37): 10. Fases detalhadas e backlog estável, 11. Dependências, caminho crítico e paralelismo, 12. Estratégia de testes e validação, 13. Estratégia de segurança fiscal, 14. Banco e migrações, 15. Sequência de frontend, 16. Observabilidade, backup e restore, 17. Mapa de specs (+29 more)

### Community 3 - "schema_status"
Cohesion: 0.11
Nodes (23): _migration_names(), MigrationOutcome, RuntimeError, Schema compatibility and serialized migration support. This module deliberately…, Raised when the database cannot safely serve this application version., Compare the installed NFX migration graph with its persisted history., Run Django migrations once at a time and report only safe metadata., schema_status() (+15 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (32): eslint, @eslint/js, eslint-plugin-react-hooks, dependencies, react, react-dom, vite, @vitejs/plugin-react (+24 more)

### Community 5 - "http.py"
Cohesion: 0.11
Nodes (16): configure_logging(), CorrelationIdMiddleware, JsonFormatter, HttpRequest, HttpResponse, Any, One redaction boundary for logs, audit payloads and error rendering., redact() (+8 more)

### Community 6 - "dependencies.py"
Cohesion: 0.11
Nodes (20): Append-only audit trail, integrity verifier, and administrative query boundary., Identity boundary (no domain implementation in P0)., dependencies_from_environment(), DependencyCheck, _object_probe(), _postgres_probe(), _schema_probe(), ServiceDependencies (+12 more)

### Community 7 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 8 - "PRD — NFX INOV"
Cohesion: 0.08
Nodes (24): 10. Ciclo de vida de empresa, 11. Ciclo de vida de certificado, 13. Retenção e exclusão, 14. Auditoria, 15. Backup e recuperação, 16. Requisitos operacionais e observabilidade, 17. Requisitos não funcionais, 18. Estados de erro, vazio, bloqueio e degradação (+16 more)

### Community 9 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+13 more)

### Community 10 - "9. Requisitos funcionais e regras de negócio"
Cohesion: 0.15
Nodes (13): 9.10 XML, DANFE e DANFSe, 9.11 Exportação ZIP, 9.12 Dashboard, 9.1 Usuários, autenticação e autorização, 9.2 Empresas, 9.3 Enriquecimento OpenCNPJ, 9.4 Certificados, 9.5 Coleta geral (+5 more)

### Community 11 - "Ingestão fiscal comum e integridade"
Cohesion: 0.18
Nodes (10): Aceite e DoD, Baseline, escopo e não escopo, Contratos, frontend e autorização, Falhas, recovery e testes, Ingestão fiscal comum e integridade, Metadados, Pipeline e invariantes, Propriedade e schema Proposed (+2 more)

### Community 12 - "Fundação do projeto"
Cohesion: 0.20
Nodes (9): Baseline, escopo e não escopo, Decisões e detalhes Proposed, Fundação do projeto, Metadados, Módulos, contratos e estado, Propósito e resultado observável, Segurança, observabilidade e falhas, Sequência, aceite e DoD (+1 more)

### Community 13 - "Configuração segura e isolamento fiscal de testes"
Cohesion: 0.20
Nodes (9): Baseline, escopo e não escopo, Configuração segura e isolamento fiscal de testes, Decisões e propostas, Estado, falhas e observabilidade, Metadados, Propósito e resultado observável, Segurança, redaction e interfaces, Sequência, aceite e DoD (+1 more)

### Community 14 - "Fundação de auditoria append-only"
Cohesion: 0.18
Nodes (10): Aceite e DoD, Baseline, escopo e não escopo, Contratos, comportamento e autorização, Decisões de implementação e evidências, Estado e schema Proposed, Falhas, segurança e observabilidade, Fundação de auditoria append-only, Metadados (+2 more)

### Community 15 - "Armazenamento de objetos e integridade"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Armazenamento de objetos e integridade, Baseline, escopo e não escopo, Decisões de implementação, Interfaces e responsabilidades implementadas, Metadados, Migração, testes e evidência, Propósito e resultado (+1 more)

### Community 16 - "Persistência relacional e migrações"
Cohesion: 0.17
Nodes (11): Aceite e DoD, Baseline e escopo, Contratos e operação, Decisões de implementação, Decisões e Proposed, Falha, recuperação e compatibilidade, Implementação e evidências, Metadados (+3 more)

### Community 17 - "Certificados A1 e criptografia por envelope"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Certificados A1 e criptografia por envelope, Estado e schema Proposed, Falhas, testes e recovery, Metadados, Propósito e resultado, Regras, interfaces e UI (+1 more)

### Community 18 - "Empresas, fluxos e enriquecimento público"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Autorização, auditoria e observabilidade, Baseline, escopo e não escopo, Empresas, fluxos e enriquecimento público, Estado e schema Proposed, Falhas, testes e recovery, Metadados, Propósito e resultado (+1 more)

### Community 19 - "Jobs duráveis, leases, políticas e observabilidade inicial"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos e comportamento, Estado e schema Proposed, Falhas e testes, Jobs duráveis, leases, políticas e observabilidade inicial, Metadados, Propósito e resultado (+1 more)

### Community 20 - "Consulta de documentos e download individual"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Consulta de documentos e download individual, Dados, índices e contratos Proposed, Falhas e testes, Metadados, Propósito e resultado, Segurança, auditoria e observabilidade (+1 more)

### Community 21 - "Elegibilidade de retenção e prévia administrativa"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos, UI e autorização, Elegibilidade de retenção e prévia administrativa, Metadados, Propósito e resultado, Regras e estado, Segurança, auditoria e observabilidade (+1 more)

### Community 22 - "Exportação ZIP assíncrona"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Estado e contratos Proposed, Exportação ZIP assíncrona, Falhas, recovery e testes, Metadados, Propósito e resultado, Segurança, auditoria, observabilidade (+1 more)

### Community 23 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 24 - "Autenticação, sessões, RBAC e shell web"
Cohesion: 0.18
Nodes (10): Aceite e DoD, Autenticação, sessões, RBAC e shell web, Baseline, escopo e não escopo, Decisões de implementação e evidências, Estado e contratos Proposed, Metadados, Propósito e resultado, Regras, UI e autorização (+2 more)

### Community 25 - "Administração de usuários"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Administração de usuários, Baseline, escopo e não escopo, Estado, backend, auditoria e segurança, Falhas, testes e recovery, Metadados, Propósito e resultado, Regras, contratos e UI

### Community 26 - "Simuladores fiscais e fixtures seguras"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Contratos Proposed e cenários, Metadados, Observabilidade, falha e testes, Propósito e resultado, Segurança e fixtures, Simuladores fiscais e fixtures seguras

### Community 27 - "Controle manual de coleta"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Controle manual de coleta, Estado e contratos Proposed, Falhas, observabilidade e testes, Metadados, Propósito e resultado, UI, permissões e comportamento visível

### Community 28 - "Distribuição NF-e e manifestação"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Decisões e contratos, Distribuição NF-e e manifestação, Estado e comportamento, Falhas, testes e recovery, Metadados, Propósito, baseline e limites, UI, autorização, segurança e auditoria

### Community 29 - "Distribuição NFS-e/ADN e cobertura"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Contratos e estado Proposed, Distribuição NFS-e/ADN e cobertura, Falhas, testes e recovery, Metadados, Propósito, baseline, escopo, Regras e comportamento visível, Segurança, auditoria e observabilidade

### Community 30 - "Dashboard e saúde operacional"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Contratos e dados Proposed, Dashboard e saúde operacional, Falhas e testes, Metadados, Propósito e resultado, UI, autorização e observabilidade

### Community 31 - "Exclusão definitiva controlada"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e gate local, Estado e contrato Proposed, Exclusão definitiva controlada, Falhas, recovery e testes, Metadados, Propósito e resultado, UI, segurança e observabilidade

### Community 32 - "Runtime interno e HTTPS"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Decisões e configuração Proposed, Metadados, Propósito e resultado, Runtime interno e HTTPS, Segurança, observabilidade e falhas, Testes, rollback e evidência

### Community 33 - "ArtifactStorageService"
Cohesion: 0.08
Nodes (42): Artifact, ArtifactState, Meta, Relational reference to one opaque object-store key. The logical key belongs to…, ArtifactConflict, ArtifactError, ArtifactMetrics, ArtifactNotReadable (+34 more)

### Community 34 - "Renderização de DANFE e DANFSe"
Cohesion: 0.25
Nodes (7): Auditoria, observabilidade e falhas, Contrato e estado requerido, Metadados, Propósito, baseline e blocker, Renderização de DANFE e DANFSe, Testes e aceite futuro, UI, autorização e segurança

### Community 35 - "Backup e restauração comprovada"
Cohesion: 0.25
Nodes (7): Aceite e DoD, Backup e restauração comprovada, Estado e contratos Proposed, Metadados, Propósito, baseline e exceção, Segurança, observabilidade e falhas, Testes e evidência

### Community 36 - "Hardening, ameaças e testes de falha"
Cohesion: 0.25
Nodes (7): Aceite e DoD, Baseline, escopo e não escopo, Hardening, ameaças e testes de falha, Metadados, Método e contratos de evidência, Propósito e resultado, Testes, observabilidade e capacidade

### Community 37 - "Piloto interno e homologação segregada"
Cohesion: 0.25
Nodes (7): Baseline, escopo e não escopo, Falhas, observabilidade e recovery, Metadados, Piloto interno e homologação segregada, Plano e decisões, Propósito e resultado, Testes/evidências e aceite

### Community 38 - "Índice de implementação das specs"
Cohesion: 0.29
Nodes (6): Autoridade, baseline e regra de uso, Como escolher a próxima spec, Decisões Open, Blocked, Deferred e Proposed, Ordem, cobertura e dependências diretas, Paralelismo e conclusão de fase, Índice de implementação das specs

### Community 39 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 40 - "Fundação P0"
Cohesion: 0.29
Nodes (6): Configuração segura e isolamento fiscal (P0-02/P0-04), Contratos dos comandos, Decisões Proposed adotadas, Fundação P0, Persistência e migrações (P1-01), Scope boundary

### Community 42 - "10. Arquitetura de componentes"
Cohesion: 0.50
Nodes (4): 10.1 Módulos de domínio, 10.2 Adaptadores, 10.3 Serviços transversais, 10. Arquitetura de componentes

### Community 43 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 44 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 45 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 55 - "audit/services.py"
Cohesion: 0.12
Nodes (24): AuditEvent, AuditChain, AuditEvent, Meta, The single stream serializes appends without allowing event rewrites., AuditService, AuditUnavailable, _canonical() (+16 more)

### Community 61 - "identity/services.py"
Cohesion: 0.06
Nodes (59): AuditVerifier, events(), _integer(), HttpRequest, JsonResponse, require_GET, IdentitySession, LoginThrottle (+51 more)

### Community 68 - "main.tsx"
Cohesion: 0.33
Nodes (3): AuditEvent, root, User

### Community 69 - "19. Jornadas principais"
Cohesion: 0.25
Nodes (8): 19. Jornadas principais, J1 — Primeiro acesso, J2 — Cadastro e coleta inicial, J3 — Operação recorrente, J4 — Consulta fiscal, J5 — Exportação em lote, J6 — Administração e auditoria, J7 — Exclusão após retenção

### Community 77 - "7. Usuários e papéis"
Cohesion: 0.40
Nodes (5): 7.1 Administrador, 7.2 Operador, 7.3 Visualizador, 7.4 Regra global, 7. Usuários e papéis

## Knowledge Gaps
- **415 isolated node(s):** `Meta`, `Migration`, `Migration`, `Migration`, `name` (+410 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `dependencies_from_environment()` connect `dependencies.py` to `ArtifactStorageService`, `load_settings`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `load_settings()` connect `load_settings` to `dependencies.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `schema_status()` connect `schema_status` to `dependencies.py`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ArtifactStorageService` (e.g. with `Artifact` and `ArtifactState`) actually correct?**
  _`ArtifactStorageService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `MemoryObjectStore` (e.g. with `Artifact` and `ArtifactState`) actually correct?**
  _`MemoryObjectStore` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Meta`, `Migration`, `Migration` to the rest of the system?**
  _415 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Arquitetura técnica — NFX INOV` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._