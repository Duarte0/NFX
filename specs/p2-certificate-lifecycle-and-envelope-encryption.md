# Certificados A1 e criptografia por envelope

## Metadados

- **Fase/status:** P2 — pronta após empresa/objetos/auditoria.
- **Backlog:** P2-03 e parte de UI de P2-04.
- **Dependências:** P1-05, P1-06, P2-01.
- **PRD:** FR-CERT-001, FR-CERT-002; BR-CERT-001, BR-CERT-002, BR-CERT-003, BR-CERT-004, BR-CERT-005, BR-CERT-006, BR-CERT-007; FR-COLL-001, BR-COLL-001, SEC-007, AUD-004. **Aceite:** AC-002, AC-014, AC-021.
- **Arquitetura:** ADR-008; seções 8, 14, 17, 25, 33, 35, 36 e 37.

## Propósito e resultado

Validar, cifrar e associar exatamente um A1 `.pfx` corrente por empresa. Certificado inválido nunca habilita coleta; certificado válido cria solicitação de coleta inicial, sem fazê-la inline. Substituição preserva acervo e estado fiscal.

## Baseline, escopo e não escopo

Usa empresa, objetos e chave externa configurada; não há parser/modelo atual. Inclui upload, validação, envelope, status/vencimento, substituição e UI segura. Não inclui integração fiscal, armazenamento em claro, compartilhamento entre empresas, PKI própria ou renovação automática.

## Estado e schema Proposed

Certificados é dona do corrente/estado; objetos guarda bytes cifrados. **Proposed:** registro com ID, empresa, objeto cifrado, senha cifrada ou segredo encapsulado, fingerprint público seguro, CNPJ extraído, validade, estado, versão da chave e timestamps; histórico permanece, mas constraint parcial garante um corrente por empresa e fingerprint não corrente em outra empresa. A chave de dados por registro é envolvida por chave mestre externa; versão é persistida. O desenho exato senha+PFX pode variar, mas ambos permanecem cifrados e recuperáveis por backup.

## Regras, interfaces e UI

Pipeline antes da ativação: validar extensão/MIME/tamanho; parse seguro; senha; legibilidade; validade; CNPJ extraído e igualdade com empresa; cifrar; armazenar; tornar corrente transacionalmente; auditar; solicitar job inicial. Estado funcional: ausente, válido, próximo do vencimento (<=30 dias), expirado, inválido, ilegível, senha incorreta, incompatível. Erros explicam a classe sem revelar material. Substituição não reinicia cursor.

Contrato interno fornece material descriptografado somente a worker autorizado e por escopo temporal mínimo; nunca retorna via HTTP. UI de Admin/Operador recebe multipart e senha, limpa campo após envio e mostra somente metadados/status; Visualizador não acessa.

## Segurança, auditoria e observabilidade

Limitar tamanho, validar conteúdo e zeroizar buffers quando a biblioteca permitir. Redigir senha, PFX, chave, token e stack de parser. Auditar inclusão/substituição/resultado sem segredo. Métricas: estados, dias até expirar, validação falha por classe e decrypt falho, sem fingerprint/CNPJ como label.

## Falhas, testes e recovery

Qualquer falha antes de ativar preserva corrente anterior. Falha permanente bloqueia fluxos e retries; correção/substituição os libera. Testar PFX sintético válido, senha errada, CNPJ divergente, expirado, limite 30/31 dias, corrida de substituição, falha objeto/DB, redaction, decrypt com chave errada e criação única do job inicial.

## Aceite e DoD

- [ ] Associação inválida não altera o certificado corrente.
- [ ] Um A1 corrente por empresa e nenhum compartilhamento.
- [ ] Bytes/senha estão cifrados e nunca aparecem em saídas.
- [ ] <=30 dias e expirado são estados distintos.
- [ ] Substituição preserva cursores/acervo e coleta inicial é assíncrona/idempotente.

DoD: migrações, parser, envelope, UI, auditoria, bloqueio e testes verdes. **Proposed:** biblioteca criptográfica, algoritmo e política de rotação; devem ser registrados sem inventar decisão Accepted.
