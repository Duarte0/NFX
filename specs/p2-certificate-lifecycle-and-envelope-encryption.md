# Certificados A1 e criptografia por envelope

## Metadados

- **Fase/status:** P2 — concluída.
- **Backlog:** P2-03 e parte de UI de P2-04.
- **Dependências:** P1-05, P1-06, P2-01.
- **PRD:** FR-CERT-001, FR-CERT-002; BR-CERT-001, BR-CERT-002, BR-CERT-003, BR-CERT-004, BR-CERT-005, BR-CERT-006, BR-CERT-007; FR-COLL-001, BR-COLL-001, SEC-007, AUD-004. **Aceite:** AC-002, AC-014, AC-021.
- **Arquitetura:** ADR-008; seções 8, 14, 17, 25, 33, 35, 36 e 37.

## Propósito e resultado

Validar, cifrar e associar exatamente um A1 `.pfx` corrente por empresa. Certificado inválido nunca habilita coleta; certificado válido cria solicitação de coleta inicial, sem fazê-la inline. Substituição preserva acervo e estado fiscal.

## Baseline, escopo e não escopo

Usa empresa, objetos e chave externa configurada; a baseline não tinha parser/modelo e esta spec os implementa. Inclui upload, validação, envelope, status/vencimento, substituição e UI segura. Não inclui integração fiscal, armazenamento em claro, compartilhamento entre empresas, PKI própria ou renovação automática.

## Estado e schema Proposed

Certificados é dona do corrente/estado; objetos guarda bytes cifrados. **Proposed:** registro com ID, empresa, objeto cifrado, senha cifrada ou segredo encapsulado, fingerprint público seguro, CNPJ extraído, validade, estado, versão da chave e timestamps; histórico permanece, mas constraint parcial garante um corrente por empresa e fingerprint não corrente em outra empresa. A chave de dados por registro é envolvida por chave mestre externa; versão é persistida. O desenho exato senha+PFX pode variar, mas ambos permanecem cifrados e recuperáveis por backup.

## Regras, interfaces e UI

Pipeline antes da ativação: validar extensão/MIME/tamanho; parse seguro; senha; legibilidade; validade; CNPJ extraído e igualdade com empresa; cifrar; armazenar; tornar corrente transacionalmente; auditar; solicitar job inicial. Estado funcional: ausente, válido, próximo do vencimento (<=30 dias), expirado, inválido, ilegível, senha incorreta, incompatível. Erros explicam a classe sem revelar material. Substituição não reinicia cursor.

Contrato interno fornece material descriptografado somente a worker autorizado e por escopo temporal mínimo; nunca retorna via HTTP. UI de Admin/Operador recebe multipart e senha, limpa campo após envio e mostra somente metadados/status; Visualizador não acessa.

## Segurança, auditoria e observabilidade

Limitar tamanho, validar conteúdo e zeroizar buffers quando a biblioteca permitir. Redigir senha, PFX, chave, token e stack de parser. Auditar inclusão/substituição/resultado sem segredo. Métricas: estados, dias até expirar, validação falha por classe e decrypt falho, sem fingerprint/CNPJ como label.

## Falhas, testes e recovery

Qualquer falha antes de ativar preserva corrente anterior. Falha permanente bloqueia fluxos e retries; correção/substituição os libera. Testar PFX sintético válido, senha errada, CNPJ divergente, expirado, limite 30/31 dias, corrida de substituição, falha objeto/DB, redaction, decrypt com chave errada e criação única do job inicial.

## Decisões Proposed adotadas nesta implementação

- `cryptography==44.0.2` fornece PKCS#12 e AES-256-GCM. Cada certificado recebe uma chave de dados aleatória de 256 bits; a chave é encapsulada pela chave mestre externa `NFX_CERTIFICATE_MASTER_KEY` (base64url de 32 bytes), com versão `1`. O PFX cifrado fica no `Artifact` e a senha cifrada fica no registro do certificado; ambos usam nonce e AAD vinculada ao UUID do certificado.
- O registro físico é `nfx_certificate`; estados persistidos são `pending`, `current`, `replaced` e `storage_failed`. Constraints parciais garantem um corrente por empresa e impedem o mesmo fingerprint em dois correntes. O fingerprint SHA-256 é o único identificador público do certificado usado pela aplicação.
- O limite de upload é 5 MiB; a validação aceita `.pfx`, exige chave privada/certificado, extrai CNPJ de atributos do subject e extensões reconhecíveis, valida datas e usa `normalize_cnpj`. Falhas de validação acontecem antes da associação corrente.
- A coleta inicial é representada por `nfx_initial_collection_request`, com estado `queued` e chave idempotente `initial:<company_id>`. A criação é transacional e não executa transporte fiscal nem worker inline; o consumo pelo worker permanece contrato para P3.
- A autorização usa a ação já aceita `ADMINISTER_CERTIFICATES`; somente o endpoint multipart recebe material e as respostas retornam apenas metadados. `certificate_material()` é o contrato interno de curta duração para worker autorizado e zera buffers mutáveis no encerramento quando possível.

## Implementação e evidência

- Código: `backend/nfx/certificates/{models,services,views}.py`, `backend/nfx/collection/models.py`, `backend/nfx/models.py` e `backend/nfx/urls.py`.
- Persistência: `backend/nfx/migrations/0007_certificate_lifecycle.py`, incluindo certificado, constraints/indexes e solicitação inicial. A migração foi aplicada em instalação limpa e `schema_status` reportou `0007_certificate_lifecycle` compatível.
- Configuração: `requirements.txt`, `backend/nfx/infrastructure/configuration.py`, `.env.example`, `docker-compose.app.yml`, `docker-compose.test.yml`, `Makefile` e `docs/DEVELOPMENT.md` documentam a chave mestre externa; nenhum valor real ou segredo foi versionado.
- UI: `frontend/src/main.tsx` adiciona upload multipart, limpeza do campo de senha, status/validade e mensagens sem material sensível; Visualizador não recebe a ação nem o endpoint.
- Testes: `tests/unit/test_certificate_lifecycle.py` cobre PFX sintético válido, senha/CNPJ inválidos, cifragem, decrypt com chave errada, limite de 30/31 dias, substituição, falha de storage, corrida concorrente, coleta inicial única e preservação da corrente; `tests/unit/test_safe_configuration.py` cobre a chave externa; `tests/integration/test_migrations.py` cobre a migração 0007.

## Aceite e DoD

- [x] Associação inválida não altera o certificado corrente — testes de senha incorreta, CNPJ divergente, expirado, ilegível e limite.
- [x] Um A1 corrente por empresa e nenhum compartilhamento — constraints, serviço transacional e teste de corrida.
- [x] Bytes/senha estão cifrados e nunca aparecem em saídas — AES-256-GCM, Artifact cifrado, payload metadata-only e redaction/auditoria.
- [x] <=30 dias e expirado são estados distintos — `certificate_status()` e teste dos limites 30/31 dias.
- [x] Substituição preserva cursores/acervo e coleta inicial é assíncrona/idempotente — histórico `replaced`, estado da empresa intocado e `InitialCollectionRequest` único.

DoD satisfeito: migrações, parser, envelope, UI, auditoria, bloqueio e testes verdes. A rotação de chave continua preparada pelo campo `key_version`, mas a execução operacional de rotação fica fora do escopo desta spec.
