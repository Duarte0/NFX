import { FormEvent, MouseEvent, useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { Badge, Button, Field, Panel } from "../../shared/ui/primitives";
import { getDashboard } from "./api";
import { JobObservabilityPanel } from "./JobObservabilityPanel";
import { BackupHealth, DashboardCard, DashboardResponse } from "./types";

type DashboardSectionProps = { loadSignal: number; notify: (message: string) => void };

function statusLabel(status: DashboardCard["status"]): string {
  return {
    ready: "Disponível",
    zero: "Zero no período",
    stale: "Desatualizado",
    partial: "Parcial",
    degraded: "Degradado",
    unavailable: "Indisponível",
    unknown: "Desconhecido",
  }[status];
}

function valueLabel(card: DashboardCard): string {
  return card.current.value === null ? "—" : String(card.current.value);
}

function backupStatusLabel(status: BackupHealth["status"]): string {
  return {
    success: "Sucesso",
    failure: "Falha",
    unavailable: "Indisponível",
  }[status];
}

function backupCoverageLabel(backup: BackupHealth): string {
  if (backup.status === "success" && backup.latest_backup.state !== null && backup.latest_backup.state !== "complete") {
    return `Sucesso anterior; último conjunto ${backupStateLabel(backup.latest_backup.state).toLowerCase()}`;
  }
  return backupStatusLabel(backup.status);
}

function backupStateLabel(state: string | null): string {
  return {
    running: "Em execução",
    complete: "Concluído",
    partial: "Parcial",
    failed: "Falhou",
    expired: "Expirado",
    success: "Sucesso",
  }[state ?? ""] ?? "Desconhecido";
}

function safeErrorLabel(code: string): string {
  return {
    capture_failed: "Falha segura na captura.",
    database_dump_failed: "Falha segura no snapshot do banco.",
    object_missing: "Objeto necessário ausente.",
    object_divergent: "Objeto divergente.",
    key_unavailable: "Chave de recuperação indisponível.",
    key_invalid: "Chave de recuperação inválida.",
    manifest_invalid: "Manifesto inválido.",
    archive_corrupt: "Conjunto de backup corrompido.",
    insufficient_space: "Espaço insuficiente.",
    interrupted: "Operação interrompida.",
    live_target: "Destino ativo rejeitado.",
    target_invalid: "Destino isolado inválido.",
    source_unavailable: "Fonte de backup indisponível.",
  }[code] ?? "Falha operacional sem detalhes.";
}

function backupAgeLabel(ageSeconds: number | null): string {
  if (ageSeconds === null) return "Idade desconhecida";
  const total = Math.max(0, Math.floor(ageSeconds));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return `${days}d ${hours}h ${minutes}min`;
}

function cardBadgeVariant(status: DashboardCard["status"]): "success" | "warning" | "danger" | "neutral" {
  if (status === "ready") return "success";
  if (["stale", "partial", "degraded"].includes(status)) return "warning";
  if (["unavailable", "unknown"].includes(status)) return "danger";
  return "neutral";
}

export function DashboardSection({ loadSignal, notify }: DashboardSectionProps) {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDashboard(await getDashboard(from || undefined, to || undefined));
    } catch {
      setDashboard(null);
      setError("Não foi possível carregar o dashboard.");
      notify("Não foi possível carregar o dashboard.");
    } finally {
      setLoading(false);
    }
  }, [from, notify, to]);

  useEffect(() => {
    if (loadSignal > 0) void loadDashboard();
  }, [loadDashboard, loadSignal]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadDashboard();
  }

  function openJobDrilldown(event: MouseEvent<HTMLAnchorElement>, card: DashboardCard) {
    if (!card.id.startsWith("jobs.") || !card.drilldown) return;
    event.preventDefault();
    window.history.pushState(null, "", card.drilldown.href);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  return (
    <section id="dashboard">
      <h2>Dashboard</h2>
      <p>Somente leitura. Intervalos usam {"[início, fim)"} em datas civis de Brasília.</p>
      <form onSubmit={submit}>
        <Field id="dashboard-from" label="De">
          <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
        </Field>
        <Field id="dashboard-to" label="Até">
          <input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
        </Field>
        <Button type="submit">Aplicar período</Button>
      </form>
      <Button variant="secondary" onClick={() => void loadDashboard()}>Atualizar dashboard</Button>
      {loading && <Feedback state="loading" message="Carregando dashboard…" />}
      <Feedback message={error} state="error" />
      {dashboard && (
        <>
          <p role="status">
            Atual: {dashboard.period.current.from} até {dashboard.period.current.to} · anterior: {dashboard.period.previous.from} até {dashboard.period.previous.to}
          </p>
          <div>
            {dashboard.cards.map((card) => (
              <Panel as="article" key={card.id} aria-label={card.label} title={card.label}>
                <p>{valueLabel(card)}</p>
                <Badge variant={cardBadgeVariant(card.status)}>{statusLabel(card.status)}</Badge>
                {card.previous && <p>Período anterior: {card.previous.value === null ? "—" : card.previous.value}</p>}
                {card.drilldown && (
                  <a href={card.drilldown.href} onClick={(event) => openJobDrilldown(event, card)}>
                    Abrir lista correspondente
                  </a>
                )}
              </Panel>
            ))}
          </div>
          <JobObservabilityPanel loadSignal={loadSignal} notify={notify} />
          <h3>Capacidades</h3>
          <ul>
            {Object.entries(dashboard.capabilities).map(([name, capability]) => (
              <li key={name}>{name}: {capability.status}</li>
            ))}
          </ul>
          {dashboard.operational_health && (
            <Panel as="aside" aria-label="Saúde operacional" title="Saúde operacional">
              <p>{dashboard.operational_health.status}</p>
              {dashboard.operational_health.backlog && <p>Backlog: {dashboard.operational_health.backlog.status}</p>}
              {dashboard.operational_health.backup && (
                <Panel as="section" aria-label="Saúde do backup" title="Backup">
                  <p>Estado da cobertura: {backupCoverageLabel(dashboard.operational_health.backup)}</p>
                  <p>Último conjunto: {backupStateLabel(dashboard.operational_health.backup.latest_backup.state)}</p>
                  {dashboard.operational_health.backup.latest_backup.safe_error && (
                    <p role="status">{safeErrorLabel(dashboard.operational_health.backup.latest_backup.safe_error)}</p>
                  )}
                  <p>Idade do último sucesso: {backupAgeLabel(dashboard.operational_health.backup.latest_success_age_seconds)}</p>
                  <p>
                    Retenção concluída: diária {dashboard.operational_health.backup.retention.daily ?? "desconhecida"}, semanal {dashboard.operational_health.backup.retention.weekly ?? "desconhecida"}, mensal {dashboard.operational_health.backup.retention.monthly ?? "desconhecida"}
                  </p>
                  <p>Última validação: {backupStateLabel(dashboard.operational_health.backup.latest_restore.state)}</p>
                  {dashboard.operational_health.backup.latest_restore.state === "failed" && (
                    <p role="status">
                      Falha na última validação: {safeErrorLabel(dashboard.operational_health.backup.latest_restore.safe_error)}
                    </p>
                  )}
                </Panel>
              )}
            </Panel>
          )}
        </>
      )}
    </section>
  );
}
