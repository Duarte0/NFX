# Backup e restauração comprovada

## Metadados

- **Fase/status:** P9 — pronta; restore comprovado é pré-requisito apenas da exclusão.
- **Backlog:** P9-02. **Dependências:** P1-06, P2-03, P3-04.
- **PRD:** OPS-BKP-001, OPS-BKP-002, OPS-BKP-003, OPS-BKP-004, OPS-BKP-005, OPS-BKP-006; BR-BKP-001, SEC-009. **Aceite:** AC-015, AC-016.
- **Arquitetura:** ADR-008, ADR-012; seções 17, 25, 27, 35, 36, 37, 40 e 41.

## Propósito, baseline e exceção

Produzir backup diário verificável e restauração isolada de PostgreSQL, objetos, PDFs, A1 cifrado, configuração necessária e material protegido da chave. `/var/backups/nfx` no mesmo host é exceção **Accepted**: cobre erro lógico/corrupção limitada, não falha física/ransomware nem conformidade plena com OPS-BKP-002/006.

## Estado e contratos Proposed

Operação é dona de backup/restore. **Proposed:** execução com tipo, início/fim, versão, estado, caminho seguro, tamanho, manifesto/hash, contagens, erro; restore com backup origem, ambiente isolado, validações e resultado. Índices por data/estado. Formato/commands finais são locais, mas o manifesto deve ligar dump DB, conjunto de objetos e versão da chave/config.

Rotina diária cria snapshot consistente ou registra janela/ordem capaz de reconciliar. Retenção mantém 7 diários, 4 semanais e 12 mensais, sem que uma cópia ocupe silenciosamente vários slots incompatíveis; algoritmo de seleção deve ser testável. Expirar backup nunca exclui acervo. Material de recuperação fica com acesso restrito e sem senha em claro.

Restore ocorre em serviços/volumes isolados e valida migrações/versão, contagens, hashes, vínculos, auditoria, jobs/cursor, leitura de objetos e descriptografia de A1 sintético. Teste e resultado registrados no máximo a cada três meses. Admin vê último backup, idade, tamanho, falha/atraso, retenção e último restore; outros papéis recebem 403.

## Segurança, observabilidade e falhas

Sem secrets em comando/log/manifests; chave é referenciada/protegida conforme runbook. Métricas: sucesso/idade/duração/tamanho/falha/último restore. Backup parcial não é sucesso. Falha de objeto/chave/dump preserva cópias anteriores. Restore nunca aponta por engano para volumes vivos; guarda de ambiente falha fechado.

## Testes e evidência

Dataset totalmente sintético cobre DB, original, PDF, cursor, auditoria e A1. Testar sucesso, dump truncado, objeto/hash ausente, chave errada, retenção 7/4/12, espaço insuficiente, interrupção/retry, RBAC e restauração trimestral simulada. Evidência é relatório sem dados/segredos.

## Aceite e DoD

- [ ] Backup diário inclui todos os componentes e manifesto verificável.
- [ ] Retenção 7/4/12 é determinística e independente da retenção fiscal.
- [ ] Restore isolado comprova vínculos, hashes, cursor e decrypt.
- [ ] Admin vê falha/atraso; demais papéis não veem detalhes.
- [ ] Limitação de host único é explícita.

DoD: jobs/commands, schema operacional, runbook, dashboard hooks e exercício completo verde. **Deferred:** destino fisicamente separado.
