# Graph Report - workspace  (2026-08-04)

## Corpus Check
- 82 files · ~41,792 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 641 nodes · 650 edges · 72 communities (52 shown, 20 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 6 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0a1e4a7f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Arquitetura técnica — NFX INOV
- PRD — NFX INOV
- What You Must Do When Invoked
- 9. Requisitos funcionais e regras de negócio
- Fundação do projeto
- graphify reference: extra exports and benchmark
- Controle manual de coleta
- graphify reference: query, path, explain
- Configuração segura e isolamento fiscal de testes
- 10. Arquitetura de componentes
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- AGENTS.md
- extraction-spec.md
- Plano de implementação — NFX INOV
- Persistência relacional e migrações
- Índice de implementação das specs
- Fundação de auditoria append-only
- Autenticação, sessões, RBAC e shell web
- Armazenamento de objetos e integridade
- Administração de usuários
- Certificados A1 e criptografia por envelope
- Empresas, fluxos e enriquecimento público
- Jobs duráveis, leases, políticas e observabilidade inicial
- Simuladores fiscais e fixtures seguras
- Ingestão fiscal comum e integridade
- Distribuição NF-e e manifestação
- Distribuição NFS-e/ADN e cobertura
- Renderização de DANFE e DANFSe
- Consulta de documentos e download individual
- Dashboard e saúde operacional
- Elegibilidade de retenção e prévia administrativa
- Exportação ZIP assíncrona
- Backup e restauração comprovada
- Exclusão definitiva controlada
- Hardening, ameaças e testes de falha
- Piloto interno e homologação segregada
- Runtime interno e HTTPS
- devDependencies
- dependencies.py
- compilerOptions
- http.py
- Fundação P0
- smoke.sh
- test-integration.sh
- adapters/__init__.py
- artifacts/__init__.py
- audit/__init__.py
- certificates/__init__.py
- collection/__init__.py
- companies/__init__.py
- documents/__init__.py
- exports/__init__.py
- identity/__init__.py
- infrastructure/__init__.py
- nfx/__init__.py
- operations/__init__.py
- retention/__init__.py
- load_settings
- main.tsx

## God Nodes (most connected - your core abstractions)
1. `Arquitetura técnica — NFX INOV` - 47 edges
2. `PRD — NFX INOV` - 28 edges
3. `Plano de implementação — NFX INOV` - 26 edges
4. `load_settings()` - 20 edges
5. `compilerOptions` - 16 edges
6. `9. Requisitos funcionais e regras de negócio` - 13 edges
7. `What You Must Do When Invoked` - 12 edges
8. `10. Fases detalhadas e backlog estável` - 11 edges
9. `dependencies_from_environment()` - 10 edges
10. `/graphify` - 10 edges

## Surprising Connections (you probably didn't know these)
- `test_postgres_and_minio_are_reachable_in_an_isolated_run()` --calls--> `dependencies_from_environment()`  [EXTRACTED]
  tests/integration/test_services.py → backend/nfx/infrastructure/dependencies.py
- `test_redaction_handles_nested_values_exceptions_urls_and_binary_payloads()` --calls--> `redact()`  [EXTRACTED]
  tests/unit/test_safe_configuration.py → backend/nfx/infrastructure/redaction.py
- `test_local_profiles_default_to_the_empty_simulator()` --calls--> `EmptyFiscalSimulator`  [EXTRACTED]
  tests/unit/test_safe_configuration.py → backend/nfx/adapters/fiscal.py
- `test_equivalent_or_changed_simulator_urls_are_rejected()` --calls--> `FiscalDestinationGuard`  [EXTRACTED]
  tests/unit/test_safe_configuration.py → backend/nfx/adapters/fiscal.py
- `test_prohibited_destination_and_redirect_make_zero_network_calls()` --calls--> `FiscalDestinationGuard`  [EXTRACTED]
  tests/unit/test_safe_configuration.py → backend/nfx/adapters/fiscal.py

## Import Cycles
- None detected.

## Communities (72 total, 20 thin omitted)

### Community 0 - "Arquitetura técnica — NFX INOV"
Cohesion: 0.04
Nodes (46): 11. Organização do repositório, 12. Stack selecionada e justificativa, 13. Alternativas consideradas e rejeitadas, 14. Responsabilidade e propriedade de estado, 15. Estratégia de dados e persistência, 16. Responsabilidades do PostgreSQL, 17. Responsabilidades do armazenamento de objetos, 18. Identidade fiscal de documentos (+38 more)

### Community 1 - "PRD — NFX INOV"
Cohesion: 0.05
Nodes (39): 10. Ciclo de vida de empresa, 11. Ciclo de vida de certificado, 12. Autenticação e autorização, 13. Retenção e exclusão, 14. Auditoria, 15. Backup e recuperação, 16. Requisitos operacionais e observabilidade, 17. Requisitos não funcionais (+31 more)

### Community 2 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 3 - "9. Requisitos funcionais e regras de negócio"
Cohesion: 0.15
Nodes (13): 9.10 XML, DANFE e DANFSe, 9.11 Exportação ZIP, 9.12 Dashboard, 9.1 Usuários, autenticação e autorização, 9.2 Empresas, 9.3 Enriquecimento OpenCNPJ, 9.4 Certificados, 9.5 Coleta geral (+5 more)

### Community 4 - "Fundação do projeto"
Cohesion: 0.20
Nodes (9): Baseline, escopo e não escopo, Decisões e detalhes Proposed, Fundação do projeto, Metadados, Módulos, contratos e estado, Propósito e resultado observável, Segurança, observabilidade e falhas, Sequência, aceite e DoD (+1 more)

### Community 5 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 6 - "Controle manual de coleta"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Controle manual de coleta, Estado e contratos Proposed, Falhas, observabilidade e testes, Metadados, Propósito e resultado, UI, permissões e comportamento visível

### Community 7 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 8 - "Configuração segura e isolamento fiscal de testes"
Cohesion: 0.20
Nodes (9): Baseline, escopo e não escopo, Configuração segura e isolamento fiscal de testes, Decisões e propostas, Estado, falhas e observabilidade, Metadados, Propósito e resultado observável, Segurança, redaction e interfaces, Sequência, aceite e DoD (+1 more)

### Community 9 - "10. Arquitetura de componentes"
Cohesion: 0.50
Nodes (4): 10.1 Módulos de domínio, 10.2 Adaptadores, 10.3 Serviços transversais, 10. Arquitetura de componentes

### Community 10 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 11 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 12 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 17 - "Plano de implementação — NFX INOV"
Cohesion: 0.05
Nodes (37): 10. Fases detalhadas e backlog estável, 11. Dependências, caminho crítico e paralelismo, 12. Estratégia de testes e validação, 13. Estratégia de segurança fiscal, 14. Banco e migrações, 15. Sequência de frontend, 16. Observabilidade, backup e restore, 17. Mapa de specs (+29 more)

### Community 19 - "Persistência relacional e migrações"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline e escopo, Contratos e operação, Decisões e Proposed, Falha, recuperação e compatibilidade, Metadados, Persistência relacional e migrações, Propósito e resultado (+1 more)

### Community 20 - "Índice de implementação das specs"
Cohesion: 0.29
Nodes (6): Autoridade, baseline e regra de uso, Como escolher a próxima spec, Decisões Open, Blocked, Deferred e Proposed, Ordem, cobertura e dependências diretas, Paralelismo e conclusão de fase, Índice de implementação das specs

### Community 21 - "Fundação de auditoria append-only"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos, comportamento e autorização, Estado e schema Proposed, Falhas, segurança e observabilidade, Fundação de auditoria append-only, Metadados, Propósito e resultado (+1 more)

### Community 22 - "Autenticação, sessões, RBAC e shell web"
Cohesion: 0.22
Nodes (8): Autenticação, sessões, RBAC e shell web, Baseline, escopo e não escopo, Estado e contratos Proposed, Metadados, Propósito e resultado, Regras, UI e autorização, Segurança, auditoria e observabilidade, Testes, sequência e aceite

### Community 23 - "Armazenamento de objetos e integridade"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Armazenamento de objetos e integridade, Baseline, escopo e não escopo, Estado e schema Proposed, Interfaces e responsabilidades, Metadados, Propósito e resultado, Segurança, observabilidade e falhas (+1 more)

### Community 24 - "Administração de usuários"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Administração de usuários, Baseline, escopo e não escopo, Estado, backend, auditoria e segurança, Falhas, testes e recovery, Metadados, Propósito e resultado, Regras, contratos e UI

### Community 25 - "Certificados A1 e criptografia por envelope"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Certificados A1 e criptografia por envelope, Estado e schema Proposed, Falhas, testes e recovery, Metadados, Propósito e resultado, Regras, interfaces e UI (+1 more)

### Community 26 - "Empresas, fluxos e enriquecimento público"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Autorização, auditoria e observabilidade, Baseline, escopo e não escopo, Empresas, fluxos e enriquecimento público, Estado e schema Proposed, Falhas, testes e recovery, Metadados, Propósito e resultado (+1 more)

### Community 27 - "Jobs duráveis, leases, políticas e observabilidade inicial"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos e comportamento, Estado e schema Proposed, Falhas e testes, Jobs duráveis, leases, políticas e observabilidade inicial, Metadados, Propósito e resultado (+1 more)

### Community 28 - "Simuladores fiscais e fixtures seguras"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Contratos Proposed e cenários, Metadados, Observabilidade, falha e testes, Propósito e resultado, Segurança e fixtures, Simuladores fiscais e fixtures seguras

### Community 29 - "Ingestão fiscal comum e integridade"
Cohesion: 0.18
Nodes (10): Aceite e DoD, Baseline, escopo e não escopo, Contratos, frontend e autorização, Falhas, recovery e testes, Ingestão fiscal comum e integridade, Metadados, Pipeline e invariantes, Propriedade e schema Proposed (+2 more)

### Community 30 - "Distribuição NF-e e manifestação"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Decisões e contratos, Distribuição NF-e e manifestação, Estado e comportamento, Falhas, testes e recovery, Metadados, Propósito, baseline e limites, UI, autorização, segurança e auditoria

### Community 31 - "Distribuição NFS-e/ADN e cobertura"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Contratos e estado Proposed, Distribuição NFS-e/ADN e cobertura, Falhas, testes e recovery, Metadados, Propósito, baseline, escopo, Regras e comportamento visível, Segurança, auditoria e observabilidade

### Community 32 - "Renderização de DANFE e DANFSe"
Cohesion: 0.25
Nodes (7): Auditoria, observabilidade e falhas, Contrato e estado requerido, Metadados, Propósito, baseline e blocker, Renderização de DANFE e DANFSe, Testes e aceite futuro, UI, autorização e segurança

### Community 33 - "Consulta de documentos e download individual"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Consulta de documentos e download individual, Dados, índices e contratos Proposed, Falhas e testes, Metadados, Propósito e resultado, Segurança, auditoria e observabilidade (+1 more)

### Community 34 - "Dashboard e saúde operacional"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Contratos e dados Proposed, Dashboard e saúde operacional, Falhas e testes, Metadados, Propósito e resultado, UI, autorização e observabilidade

### Community 35 - "Elegibilidade de retenção e prévia administrativa"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Contratos, UI e autorização, Elegibilidade de retenção e prévia administrativa, Metadados, Propósito e resultado, Regras e estado, Segurança, auditoria e observabilidade (+1 more)

### Community 36 - "Exportação ZIP assíncrona"
Cohesion: 0.20
Nodes (9): Aceite e DoD, Baseline, escopo e não escopo, Estado e contratos Proposed, Exportação ZIP assíncrona, Falhas, recovery e testes, Metadados, Propósito e resultado, Segurança, auditoria, observabilidade (+1 more)

### Community 37 - "Backup e restauração comprovada"
Cohesion: 0.25
Nodes (7): Aceite e DoD, Backup e restauração comprovada, Estado e contratos Proposed, Metadados, Propósito, baseline e exceção, Segurança, observabilidade e falhas, Testes e evidência

### Community 38 - "Exclusão definitiva controlada"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e gate local, Estado e contrato Proposed, Exclusão definitiva controlada, Falhas, recovery e testes, Metadados, Propósito e resultado, UI, segurança e observabilidade

### Community 39 - "Hardening, ameaças e testes de falha"
Cohesion: 0.25
Nodes (7): Aceite e DoD, Baseline, escopo e não escopo, Hardening, ameaças e testes de falha, Metadados, Método e contratos de evidência, Propósito e resultado, Testes, observabilidade e capacidade

### Community 40 - "Piloto interno e homologação segregada"
Cohesion: 0.25
Nodes (7): Baseline, escopo e não escopo, Falhas, observabilidade e recovery, Metadados, Piloto interno e homologação segregada, Plano e decisões, Propósito e resultado, Testes/evidências e aceite

### Community 41 - "Runtime interno e HTTPS"
Cohesion: 0.22
Nodes (8): Aceite e DoD, Baseline, escopo e não escopo, Decisões e configuração Proposed, Metadados, Propósito e resultado, Runtime interno e HTTPS, Segurança, observabilidade e falhas, Testes, rollback e evidência

### Community 42 - "devDependencies"
Cohesion: 0.06
Nodes (32): eslint, @eslint/js, eslint-plugin-react-hooks, dependencies, react, react-dom, vite, @vitejs/plugin-react (+24 more)

### Community 43 - "dependencies.py"
Cohesion: 0.15
Nodes (15): dependencies_from_environment(), DependencyCheck, _object_probe(), _postgres_probe(), ServiceDependencies, Command, BaseCommand, index() (+7 more)

### Community 44 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+13 more)

### Community 45 - "http.py"
Cohesion: 0.11
Nodes (16): Any, configure_logging(), CorrelationIdMiddleware, JsonFormatter, HttpRequest, HttpResponse, One redaction boundary for logs, audit payloads and error rendering., redact() (+8 more)

### Community 46 - "Fundação P0"
Cohesion: 0.33
Nodes (5): Configuração segura e isolamento fiscal (P0-02/P0-04), Contratos dos comandos, Decisões Proposed adotadas, Fundação P0, Scope boundary

### Community 64 - "load_settings"
Cohesion: 0.11
Nodes (32): EmptyFiscalSimulator, FiscalDestinationError, FiscalDestinationGuard, RuntimeError, P0 fiscal boundary: validate every destination before a transport can run., Safe rejection that intentionally contains no destination value., The sole initial fiscal transport; it always produces an empty result., Validate the configured URL and every declared redirect before I/O. (+24 more)

## Knowledge Gaps
- **403 isolated node(s):** `name`, `private`, `version`, `type`, `build` (+398 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Arquitetura técnica — NFX INOV` connect `Arquitetura técnica — NFX INOV` to `10. Arquitetura de componentes`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Why does `PRD — NFX INOV` connect `PRD — NFX INOV` to `9. Requisitos funcionais e regras de negócio`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Why does `load_settings()` connect `load_settings` to `dependencies.py`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _403 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Arquitetura técnica — NFX INOV` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._
- **Should `PRD — NFX INOV` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._
- **Should `What You Must Do When Invoked` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._