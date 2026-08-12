## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Frontend Work and Available Skills

For interface creation, redesign, modernization, or significant visual frontend changes — including changes to layout, components, visual flows, responsiveness, or the design system — the agent must use the available skills/plugins that are applicable to the required capabilities.

Before starting, the agent must identify the required capabilities (for example, visual concepting, design system work, React implementation, browser validation, and browser debugging), select the applicable skills/plugins, and read their instructions in full. The workflow defined by the selected skills is mandatory and includes visual concepting, concept/design approval when required by the skill, definition or adoption of the design system, implementation, browser validation, and visual refinement. When a selected skill requires concept/design approval before implementation — especially for interface creation, redesign, modernization, or significant visual changes — the agent must not skip that step or begin implementation before approval is obtained.

Specialized skills/plugins complement, but never replace, `PRD.md`, `ARCHITECTURE.md`, specs, issues, and existing contracts. Design decisions must not silently change endpoints, HTTP contracts, RBAC, business rules, functional states, URLs/anchors, or architectural boundaries. Any functional change requires an approved spec/issue.

The frontend must preserve `App.tsx` as the composition root, the `App → features → shared` dependency direction, `shared/http`, `shared/ui`, and the existing boundaries of each feature. Do not introduce a router, global state management, or a UI library outside an approved scope. This rule is part of the standard execution process for every applicable frontend issue and does not depend on a manual instruction from the user.
