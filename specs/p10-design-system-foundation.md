# Fundação do design system

## Metadados

- **Fase/status/versão:** P10-01 — implementado e verificado no issue 0034 — v1.1.
- **Dependências:** baseline P1–P9; nenhuma spec P10 anterior. **Seguida por:** P10-02..07.
- **Fontes:** PRD NFR-009..012 e AC-026; Arquitetura §§10.4 e 11; Plano P10-01.

## Objetivo, escopo e não escopo

Estabelecer a linguagem visual reutilizável da aplicação desktop-first: vinho como primária, cinza como estrutura/neutro e branco como superfície. O contrato cobre tokens de tipografia, espaçamento, cor, superfícies, bordas, sombras e componentes transversais para ação, formulário, painel, tabela, badge e feedback. Não altera rotas, dados, chamadas HTTP, autorização, lógica fiscal, nem introduz biblioteca UI, router ou estado global.

## Contrato canônico de tokens

Tokens são a única fonte compartilhada de cor, tipografia, espaçamento, raio, borda, sombra e foco; uma feature pode compor primitives, mas não redefinir esses valores. P10-01 deve publicar os seguintes valores como contrato CSS/TypeScript agnóstico de implementação:

| Grupo | Token/valor | Uso normativo |
|---|---|---|
| Marca | `brand-700 #6B1E3B`, `brand-800 #4E132B`, `brand-050 #F9F1F4` | ação primária, foco e superfície institucional; texto branco sobre `brand-700`/`800` |
| Neutros | `ink #1F2937`, `muted #4B5563`, `line #D1D5DB`, `canvas #F5F5F5`, `surface #FFFFFF` | texto, borda, fundo e painel; não usar cinza claro como texto essencial |
| Estados | `success #166534`, `warning #92400E`, `danger #B91C1C`, `info #1D4ED8` | estado, ícone e ação semânticos; cada um deve ter superfície clara associada com texto no tom escuro |
| Escala | fonte 14/16/20/24/32 px; espaço 4/8/12/16/24/32 px; raio 6/10 px | densidade operacional desktop; texto corrente é ao menos 14 px |
| Foco | anel de 3 px `#1D4ED8`, offset de 2 px | todo elemento interativo recebe foco visível independente de cor de estado |

Texto normal e controles devem atingir contraste mínimo 4,5:1 contra sua superfície; texto grande, ícones informativos e bordas que delimitam controle devem atingir ao menos 3:1 quando essa for a regra aplicável. Cor nunca é o único portador de estado.

### Valores auxiliares e pares verificados

Os tokens de superfície clara usados com os tons semânticos são `success-surface #F0FDF4`,
`warning-surface #FFFBEB`, `danger-surface #FEF2F2` e `info-surface #EFF6FF`. A implementação
publica todos os tokens em `frontend/src/shared/ui/tokens.css`; primitives usam somente variáveis
CSS para valores de cor, tipografia, espaçamento, borda, sombra, raio e foco. A verificação
reprodutível mantém estes pares (razão mínima WCAG aplicável):

| Primeiro plano | Superfície | Mínimo |
|---|---|---:|
| `ink #1F2937` | `surface #FFFFFF` | 4,5:1 |
| `muted #4B5563` | `surface #FFFFFF` | 4,5:1 |
| `white #FFFFFF` | `brand-700 #6B1E3B` | 4,5:1 |
| `white #FFFFFF` | `brand-800 #4E132B` | 4,5:1 |
| `brand-800 #4E132B` | `brand-050 #F9F1F4` | 4,5:1 |
| `success #166534` | `success-surface #F0FDF4` | 4,5:1 |
| `warning #92400E` | `warning-surface #FFFBEB` | 4,5:1 |
| `danger #B91C1C` | `danger-surface #FEF2F2` | 4,5:1 |
| `info/focus #1D4ED8` | `info-surface #EFF6FF` / `surface #FFFFFF` | 4,5:1 / 3:1 |

As linhas `line #D1D5DB` delimitam superfícies e linhas de tabela; controles interativos usam
`ink` como borda e o anel de foco `focus` para manter a indicação aplicável acima de 3:1.

## Primitives e semântica compartilhada

O contrato canônico cobre botão (primário, secundário, perigo e desabilitado), campo/label/ajuda/erro, painel, tabela responsiva para desktop, badge de estado, aviso e feedback. Primitives devem preservar elementos HTML nativos; `aria-*` só complementa semântica nativa. Botão crítico deve ter variante visual explícita, mas confirmação e autorização continuam nos owners de domínio.

Cada feature deve mapear o estado recebido a exatamente uma das variantes: loading, vazio válido, erro, indisponível, degradado, bloqueado, sucesso ou ação crítica. Indisponível/degradado deve conservar dados seguros já recebidos, explicar a limitação e nunca parecer zero, vazio ou sucesso. Mensagens de erro só podem exibir texto seguro já exposto pelo contrato do owner; XML, segredo, path, stack trace e payload interno são proibidos.

## Compatibilidade, segurança, testes e aceite

A adoção deve preservar `App → features → shared`, `shared/http`, pt-BR, Brasília/BRL e IDs/âncoras publicados. Nenhum primitive pode tratar ocultação visual como autorização ou introduzir escrita durante leitura. A evidência deve incluir TypeScript/lint/build, verificação reproduzível dos pares de contraste, foco e teclado, e renderização de todas as variantes com dados sintéticos.

## Aceite e decisões

- [x] Tokens e primitives documentam propósito, variantes e estados sem duplicar regras de domínio.
- [x] As cores vinho/cinza/branco e os pares semânticos passam na verificação de contraste aplicável.
- [x] Estados comuns preservam semântica, foco e mensagens seguras.
- [x] Nenhum contrato HTTP, papel ou comportamento funcional é alterado.

**Decisão registrada:** os valores desta tabela resolvem o detalhe Proposed autorizado pelo plano; não há logo, fonte proprietária ou valor de marca adicional aprovado.

## Evidência de implementação

`frontend/src/shared/ui/tokens.css` é a fonte única dos valores visuais e aplica tipografia,
superfícies, controles, foco e estados à aplicação. `frontend/src/shared/ui/primitives.ts` publica
`Button`, `Field`, `Panel`, `DataTable` e `Badge`; `Feedback.ts` modela loading, vazio válido,
erro, indisponível, degradado, bloqueado, sucesso e ação crítica com regiões vivas e mensagens
seguras. A adoção representativa cobre o shell autenticado, login, dashboard e drill-down de jobs;
os demais owners continuam livres para adotar os mesmos primitives nos slices P10 seguintes.

`frontend/scripts/ui-contract.mjs` e `run-ui-contract.mjs` verificam tokens, contraste,
semântica/ARIA, foco, operação nativa de teclado, bloqueio, estados e ausência de efeitos
colaterais por renderização usando somente dados sintéticos. `npm --prefix frontend run test:ui-contract`
executa essa verificação sem dependência nova. O build e lint TypeScript/ESLint passam; não houve
migration, backend, chamada HTTP, mudança de papel, rota, âncora ou contrato fiscal.

DoD concluído em 2026-08-12 no issue 0034.
