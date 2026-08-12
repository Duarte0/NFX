# Backup verificável e recuperação manual

## Metadados

- **Fase/status:** P9 — implementação e validação isolada de P9-02 concluídas; permanece uma lacuna de requisito de produção para cópia fisicamente separada e recuperação após perda do host.
- **Backlog:** P9-02. **Dependências:** P1-06, P2-03, P3-04.
- **PRD:** OPS-BKP-001, OPS-BKP-002, OPS-BKP-003, OPS-BKP-004, OPS-BKP-005, OPS-BKP-006; BR-BKP-001, SEC-009. **Aceite:** AC-015, AC-016.
- **Arquitetura:** ADR-008, ADR-012; seções 17, 25, 27, 35, 36, 37, 40 e 41.

## Propósito, baseline e exceção

Produzir backup diário verificável de PostgreSQL, objetos, PDFs, A1 cifrado, configuração necessária e material protegido da chave; validar a integridade do conjunto e documentar sua recuperação manual. A implementação atual em `/var/backups/nfx`, no mesmo host, cobre erro lógico/corrupção limitada, mas **não satisfaz** OPS-BKP-002 nem demonstra OPS-BKP-006 para perda física/ransomware do host. A arquitetura a registra como limitação do MVP; pelo PRD, mais prioritário, cópia fisicamente separada continua requisito de produção pendente.

## Estado e contratos Proposed

Operação é dona de backup e da validação do conjunto. **Proposed:** execução com tipo, início/fim, versão, estado, caminho seguro, tamanho, manifesto/hash, contagens e erro; validação com backup origem, destino isolado, verificações e resultado. Índices por data/estado. Formato/commands finais são locais, mas o manifesto deve ligar dump DB, conjunto de objetos e versão da chave/config.

Rotina diária cria snapshot consistente ou registra janela/ordem capaz de reconciliar. Retenção mantém 7 diários, 4 semanais e 12 mensais, sem que uma cópia ocupe silenciosamente vários slots incompatíveis; algoritmo de seleção deve ser testável. Expirar backup nunca exclui acervo. Material de recuperação fica com acesso restrito e sem senha em claro.

`restore_backup` é um exercício isolado de validação/integridade: confere o manifesto, dump, objetos, contagens, hashes, vínculos, auditoria, jobs/cursor e descriptografia de A1 sintético, e nunca altera volumes vivos. Ele não é restore operacional completo: não cria PostgreSQL/MinIO, não importa o dump nem repopula objetos. A recuperação aceita para o MVP é manual e documentada: operador autorizado prepara host novo e isolado, sobe PostgreSQL e MinIO, importa o dump, restaura os objetos do conjunto, fornece a chave mestre por mecanismo seguro externo, sobe a aplicação e valida o estado. Admin vê último backup, idade, tamanho, falha/atraso, retenção e última validação; outros papéis recebem 403.

## Segurança, observabilidade e falhas

Sem secrets em comando/log/manifests; a chave mestre é referenciada/protegida pelo mecanismo externo do operador. Métricas: sucesso/idade/duração/tamanho/falha/última validação. Backup parcial não é sucesso. Falha de objeto/chave/dump preserva cópias anteriores. A validação nunca aponta por engano para volumes vivos; guarda de ambiente falha fechado. A recuperação manual deve usar host, banco, bucket e volumes isolados dos ativos.

## Testes e evidência

Dataset totalmente sintético cobre DB, original, PDF, cursor, auditoria e A1. Testar sucesso, dump truncado, objeto/hash ausente, chave errada, retenção 7/4/12, espaço insuficiente, interrupção/retry, RBAC e validação isolada do conjunto. Evidência é relatório sem dados/segredos. A recuperação operacional completa é procedimento manual, não feature de runtime.

## Aceite e DoD

- [x] Backup diário inclui todos os componentes e manifesto verificável.
- [x] Retenção 7/4/12 é determinística e independente da retenção fiscal.
- [x] Validação isolada do conjunto comprova vínculos, hashes, cursor e decrypt, sem alterar volumes vivos.
- [x] Procedimento manual de recuperação de PostgreSQL, objetos e certificados cifrados é documentado; a chave mestre é externa ao backup.
- [x] Admin vê falha/atraso; demais papéis não veem detalhes.
- [x] Limitação de host único é explícita.

DoD: commands, schema operacional, runbook de recuperação manual, status administrativo e exercício sintético verde.
O arquivo `database.dump` é uma captura lógica determinística do PostgreSQL, sem credenciais em
argumentos; o formato físico de um dump externo permanece uma decisão operacional futura.
**Lacuna de requisito:** definir e comprovar destino fisicamente separado, controles de acesso e
recuperação após perda do host antes de declarar OPS-BKP-002/006 ou AC-016 concluídos em produção.
Isso não bloqueia P9-03, cuja saga deve continuar a preservar recovery sem falso sucesso.
