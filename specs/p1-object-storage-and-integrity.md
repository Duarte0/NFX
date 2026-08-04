# Armazenamento de objetos e integridade

## Metadados

- **Fase/status:** P1 — concluída.
- **Backlog:** P1-06. **Dependências:** P0-03, P1-01.
- **PRD:** BR-INT-003, BR-INT-005; suporte futuro a NFR-004. **Aceite:** AC-006 e AC-007 serão completados em P4.
- **Arquitetura:** ADR-004 e ADR-007; seções 14–17, 28, 36, 37 e 40.

## Propósito e resultado

Criar uma porta de armazenamento S3/MinIO em que uma referência só seja finalizada após confirmação de bytes, tamanho e hash. Pendências, ausências, órfãos e divergências devem ser detectáveis e recuperáveis sem exclusão automática.

## Baseline, escopo e não escopo

MinIO e bucket de desenvolvimento existem no Compose; não há cliente, metadado relacional ou reconciliação. Esta spec implementa abstração e ciclo de objeto genérico. Não classifica conteúdo fiscal, não fornece download ao usuário, não gera PDF/ZIP e não avança cursor.

## Decisões de implementação

Artefatos/armazenamento são donos de bytes, hash e versão; PostgreSQL guarda referência. A decisão Proposed foi aceita como `Artifact`, com UUID interno, classe/chave lógica do chamador, chave física opaca gerada como `artifacts/<uuid>/v1`, SHA-256, tamanho, MIME declarado e retornado pelo armazenamento, estado, versão, timestamps e erro seguro. Os estados são `pending`, `finalized`, `missing` e `divergent`.

A constraint parcial permite somente uma referência `finalized` por chave lógica; retries com mesmo hash/tamanho retornam a referência finalizada existente e bytes divergentes recebem conflito explícito. Há índice de estado/idade e unicidade/índice da chave opaca. O limite inicial por artefato é 50 MiB; a classificação futura poderá fornecer políticas menores por classe. O adaptador usa arquivo temporário com spool de 1 MiB para calcular SHA-256 e limitar tamanho sem manter objetos grandes integralmente em memória.

## Interfaces e responsabilidades implementadas

`nfx.artifacts.storage.ArtifactStorageService` oferece `begin`, `transmit`, `open_verified`, `reconcile` e `metrics`; `ObjectStore` é a porta e `S3ObjectStore` é o adaptador MinIO/S3. A sequência é criar pendência → transmitir bytes → conferir `head` (hash/tamanho) → finalizar o metadado em transação. O chamador recebe ID/metadados; credenciais só são usadas no adaptador construído na borda de infraestrutura. Não foi exposto endpoint HTTP nem alterada a autorização de negócio.

## Segurança, observabilidade e falhas

O serviço valida metadados e limite de tamanho; logs contêm ID, operação, duração, tamanho quando concluído e resultado, nunca bytes, XML, PFX ou credencial. `ArtifactMetrics` expõe pendências, pendências por idade, ausentes, divergentes e órfãos; a latência/erro fica no evento estruturado da transmissão. MinIO indisponível ou falha de banco após upload mantém a referência pendente e não a finaliza; a reconciliação detecta a pendência e quaisquer objetos sem referência, sem exclusão automática. Hash/tamanho divergentes marcam `divergent` e bloqueiam leitura.

## Migração, testes e evidência

`nfx.0002_artifact` cria a tabela, constraint de tamanho, constraint parcial de chave lógica e índices. `tests/integration/test_artifact_storage.py` usa bytes sintéticos e `MemoryObjectStore` isolado para a matriz abaixo, além de exercitar `S3ObjectStore` no bucket exclusivo do Compose.

| Corte/cenário | Estado/evidência esperada |
|---|---|
| zero bytes e leitura parcial | `finalized`; SHA-256/tamanho confirmados e leitura retorna os bytes |
| limite, stream interrompido, MinIO indisponível | `pending`; retry posterior finaliza |
| falha de DB depois do upload | `pending`; objeto/referência seguem detectáveis |
| objeto removido ou alterado | `missing`/`divergent`; `open_verified` recusa servir |
| retry e duas finalizações concorrentes | uma única referência `finalized`; mesmo conteúdo é idempotente, conteúdo distinto conflita |
| órfão | contador aumenta; reconciliador não remove nem corrige hash |

Validação executada: `TEST_RUN_ID=p1-artifacts-… ./scripts/test-integration.sh` — 14 testes de integração verdes, incluindo instalação limpa/reexecução da migração e MinIO real em Compose.

## Aceite e DoD

- [x] `finalizado` só ocorre após hash/tamanho confirmados.
- [x] Falha em qualquer corte é reexecutável ou reconciliável.
- [x] Objeto ausente/divergente não é servido.
- [x] Reconciliação não exclui silenciosamente objeto/referência.
- [x] Nenhuma chave física deriva de texto não confiável.

DoD satisfeito: migração, porta, implementação MinIO, reconciliador, métricas e testes de integração verdes. A decisão Proposed de algoritmo foi aceita como SHA-256, registrado no metadado por objeto para compatibilidade de leitura futura.
