# Elegibilidade de retenção e prévia administrativa

## Metadados

- **Fase/status:** P8 — P8-03 implementada e verificada; exclusão permanece desabilitada.
- **Backlog:** P8-03. **Dependências:** P1-05, P4-01 e P7-03 para incluir PDFs existentes.
- **PRD:** RET-001, RET-002, RET-003, RET-004, RET-007, RET-008; AUD-006. **Aceite:** AC-015 parcial e AC-014.
- **Arquitetura:** seções 14, 28, 31, 37, 40 e 41.

## Propósito e resultado

Calcular elegibilidade fiscal, impedir exclusão prematura e produzir prévia administrativa estável do documento e artefatos, sem remover qualquer dado.

## Baseline, escopo e não escopo

P4 fornece datas e vínculos fiscais; P7 fornece artefatos. Esta spec cria cálculo, estado e prévia, mas deliberadamente não cria comando, rota ou job de exclusão. Não altera regras por desativação, certificado ou preferência administrativa.

## Regras e estado

NF-e: 132 meses completos desde autorização; 15/08/2026 → 15/08/2037. NFS-e: ano de emissão + cinco anos-calendário, elegível em 1º de janeiro do sexto ano seguinte; qualquer data de 2026 → 01/01/2032. Empresa/usuário desativado ou certificado expirado/substituído não muda prazo. Nunca há exclusão automática.

Retenção é dona da elegibilidade/decisão. **Proposed:** regra versionada, data-base, `eligible_at`, cálculo em, estado e prévia com ID/hash/versão do escopo; índices por família/elegibilidade/estado. A implementação calcula sob demanda com `retention-v1`, `scope-v1` e hash SHA-256 do escopo de evidências; mudanças de evidência invalidam o hash sem reescrever fatos fiscais. A prévia enumera documento, eventos e original/XML sem copiar conteúdo; PDFs/derivados ficam para P7-03.

## Contratos, UI e autorização

Serviço calcula em UTC/datas civis apropriadas sem deslocar datas fiscais. Contratos: listar elegíveis/bloqueados, detalhar motivo/data e gerar prévia. Somente Admin acessa visão de retenção; Operador/Visualizador recebem 403 direto. Nenhuma rota/command delete existe nesta fase. UI exige estado claro `retido|elegível`, datas em Brasília e aviso de que prévia não exclui.

## Segurança, auditoria e observabilidade

Auditar consulta/geração de prévia com ator, escopo seguro, regra/versão e resultado, sem conteúdo. Métricas de cálculo falho, elegíveis e prévias; não expor documento em labels. Erro de data/artefato torna item não executável e visível, nunca elegível por padrão.

## Testes e recovery

Relógio congelado: instante anterior/exato/posterior dos exemplos; mês com 28/29/30/31 dias; NFS-e em 01/01 e 31/12; artefato adicionado após prévia; papéis; tentativa direta de delete inexistente. Migração/backfill deve ser reiniciável e comparado ao cálculo puro. Compliance produtivo é validação externa, não alteração desta regra Accepted.

## Aceite e DoD

- [x] Exemplos AC-015 resultam exatamente nas datas exigidas.
- [x] Nenhum papel exclui durante P8.
- [x] Prévia estável enumera todos os vínculos sem conteúdo fiscal.
- [x] Mudança de escopo invalida prévia antiga.
- [x] Estado externo da empresa/certificado não altera retenção.

DoD: regra, contratos/UI, auditoria, métricas e testes de fronteira verdes. Não houve migration/backfill: o cálculo-on-read é recalculável. Evidência: `backend/nfx/retention/services.py`/`views.py`, `frontend/src/features/retention/`, `tests/unit/test_retention.py`, `tests/integration/test_retention.py`, validações Ruff/mypy/TypeScript/ESLint e suite isolada de integração (61 testes).
