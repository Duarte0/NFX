# Runtime interno e HTTPS

O perfil `docker-compose.runtime.yml` é a implantação local de produção do MVP. Ele mantém
web, worker, scheduler, PostgreSQL e MinIO como serviços reiniciáveis, e publica somente o
reverse proxy. As redes `app` e `data` são privadas; volumes `postgres_runtime_data` e
`minio_runtime_data` são persistentes e não devem ser removidos durante reinícios, upgrade ou
rollback.

## Provisionamento

Construa uma única imagem versionada para os três processos, construa o proxy com sua
configuração versionada e gere o certificado fora do repositório:

```sh
docker build --target app -t nfx-inov:2026-08-10 .
docker compose -f docker-compose.runtime.yml build proxy
scripts/generate-runtime-certificate.sh /var/lib/nfx/tls
```

Forneça, por ambiente seguro, `NFX_APP_IMAGE`, `NFX_TLS_DIR`, `NFX_SECRET_DIR`, `NFX_BACKUP_DIR`, `DATABASE_URL`,
`POSTGRES_PASSWORD`, `MINIO_ROOT_USER` e `MINIO_ROOT_PASSWORD`. `NFX_SECRET_DIR` deve conter
somente os arquivos `nfx_secret_key` e `nfx_certificate_master_key`, montados como
`/run/secrets` somente leitura. O Compose falha fechado quando qualquer valor obrigatório está
ausente; o loader também rejeita segredos ausentes, placeholders ou fontes duplicadas. Os
arquivos de segredo e TLS devem ser legíveis somente pelo runtime autorizado.

## Inicialização, saúde e reinício

```sh
docker compose -f docker-compose.runtime.yml config
docker compose -f docker-compose.runtime.yml up -d postgres minio
docker compose -f docker-compose.runtime.yml run --rm web python backend/manage.py nfx_migrate
docker compose -f docker-compose.runtime.yml up -d
docker compose -f docker-compose.runtime.yml ps
```

Use `https://nfx.internal:8443` (ou o hostname local configurado). A porta HTTP 8080 do proxy
responde somente com redirect 308 para HTTPS; PostgreSQL, MinIO, console, worker e scheduler
não têm portas publicadas. Liveness da aplicação é independente; readiness depende de schema,
PostgreSQL e MinIO. A saúde operacional administrativa continua em `/health/operational`, com
freshness durável de worker/scheduler e sem dados fiscais ou segredos.

Um serviço pode ser reiniciado individualmente:

```sh
docker compose -f docker-compose.runtime.yml restart web
docker compose -f docker-compose.runtime.yml restart worker
docker compose -f docker-compose.runtime.yml restart scheduler
```

O worker deixa leases recuperáveis e o scheduler recupera trabalho vencido. Não use `down
--volumes` no runtime: isso destruiria o estado persistente.

## Upgrade, rollback e limitações

Antes do upgrade, faça backup conforme o runbook P9-02, verifique a compatibilidade das
migrations e confirme a saúde do banco/MinIO. Suba a nova imagem, aplique migrations compatíveis,
aguarde readiness e reinicie proxy/web/worker/scheduler conforme necessário. Rollback deve usar
a imagem e configuração anteriores somente enquanto o schema permanecer compatível; volumes não
são apagados nem recriados. Renove o certificado gerando um novo par no diretório externo e
reiniciando somente o proxy após validar os arquivos.

O certificado autoassinado cifra o tráfego, mas gera aviso de confiança no navegador. CA interna,
alta disponibilidade, acesso externo e backup fisicamente separado são decisões futuras; o
backup local no mesmo host é uma limitação aceita do MVP.

`NFX_BACKUP_DIR` é montado somente como a área protegida `/var/backups/nfx` dos processos da
aplicação. O diretório deve existir fora do repositório, ter permissões restritas e ser incluído
no procedimento administrativo de cópia/proteção. Não monte volumes de runtime como destino de
restore: use um destino isolado separado e os guards do comando `restore_backup`.

Os limites escolhidos são verificados com `docker compose ps`/health e `docker stats
--no-stream` durante o smoke operacional; uma carga sintética de health e uma reinicialização de
cada processo devem manter o proxy pronto e os volumes intactos. O resultado e a imagem usada
devem ser anexados ao registro operacional, sem incluir configuração ou dados sensíveis.
