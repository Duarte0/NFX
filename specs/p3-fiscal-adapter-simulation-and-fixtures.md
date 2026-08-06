# Simuladores fiscais e fixtures seguras

## Metadados

- **Fase/status:** P3 — pronta após P0-04 e engine P3.
- **Backlog:** P3-03. **Dependências:** P0-04, P3-01.
- **PRD:** SEC-007, NFR-007, NFR-008; suporta testes de BR-COLL-006, BR-INT-002, BR-INT-005. **Aceite futuro:** AC-006, AC-007, AC-008, AC-009.
- **Arquitetura:** ADR-006; seções 10.2, 23, 24, 33, 37 e 38.

## Propósito e resultado

Definir portas substituíveis e simuladores determinísticos de NF-e/ADN para que P4–P6 sejam implementadas sem endpoint, credencial, certificado, CNPJ ou XML real e sem possibilidade de atingir produção.

## Baseline, escopo e não escopo

P0 fornece guarda de rede e P3 jobs. Criar contratos semânticos, formato de cenário e fixtures sintéticas. Não implementar SOAP/HTTP oficial, schemas finais, parsing fiscal definitivo ou persistência de documento.

## Contratos Proposed e cenários

**Proposed:** porta recebe fonte/família/ator/fluxo, cursor opaco, política efetiva, certificado handle abstrato e correlação; retorna resultado tipado, página/unidades brutas sintéticas, próximo cursor/NSU, cobertura/cooldown e metadados seguros. Erros são valores/classificações, não exceções não tipadas. Contratos NF-e e ADN são independentes mesmo quando compartilham tipos genéricos.

Simuladores devem reproduzir: paginação; sucesso com itens; vazio válido; duplicata mesmo hash; identidade igual/conteúdo divergente; timeout; indisponibilidade; cooldown; bloqueio permanente; payload malformado/desconhecido; evento sem pai; cursor repetido; morte/restart. Cenário define seed e sequência para replay determinístico.

## Segurança e fixtures

Fixtures são geradas/sintéticas, claramente marcadas, com domínios reservados, CNPJs fictícios válidos apenas para algoritmo e certificados gerados localmente quando indispensáveis. Nunca copiar XML/credencial/token/URL produtiva. Scanner/teste deve detectar canários e destinos proibidos. Transporte fake registra chamadas para provar ordem e ausência de rede.

## Observabilidade, falha e testes

Logs do simulador incluem cenário/passo/correlação, não conteúdo integral. Testar contrato contra fakes NF-e/ADN, determinismo, paginação, todos os erros, cancelamento/restart e guarda antes de DNS/conexão. Falha de fixture inválida encerra cenário com erro claro, sem interpretá-la como vazio.

## Aceite e DoD

- [ ] Cada cenário obrigatório possui fixture e expectativa documentadas.
- [ ] Trocar fake por adapter futuro não altera casos de uso.
- [ ] Teste não abre rede fiscal nem contém dado real.
- [ ] Vazio, indisponível, sem cobertura, parcial e bloqueado são distinguíveis.
- [ ] Replay é determinístico e adequado a testes de idempotência.

DoD: portas, biblioteca de cenários, fixtures, scanner/guarda e suite verdes. **Open:** endpoints/leiautes oficiais; não bloqueiam simuladores.
