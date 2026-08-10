import { FormEvent, useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { getDashboard } from "./api";
import { DashboardCard, DashboardResponse } from "./types";

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

  return (
    <section id="dashboard">
      <h2>Dashboard</h2>
      <p>Somente leitura. Intervalos usam {"[início, fim)"} em datas civis de Brasília.</p>
      <form onSubmit={submit}>
        <label>
          De <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
        </label>
        <label>
          Até <input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
        </label>
        <button type="submit">Aplicar período</button>
      </form>
      <button onClick={() => void loadDashboard()}>Atualizar dashboard</button>
      {loading && <p role="status">Carregando dashboard…</p>}
      <Feedback message={error} error />
      {dashboard && (
        <>
          <p role="status">
            Atual: {dashboard.period.current.from} até {dashboard.period.current.to} · anterior: {dashboard.period.previous.from} até {dashboard.period.previous.to}
          </p>
          <div>
            {dashboard.cards.map((card) => (
              <article key={card.id} aria-label={card.label}>
                <h3>{card.label}</h3>
                <p>{valueLabel(card)}</p>
                <p role="status">{statusLabel(card.status)}</p>
                {card.previous && <p>Período anterior: {card.previous.value === null ? "—" : card.previous.value}</p>}
                {card.drilldown && <a href={card.drilldown.href}>Abrir lista correspondente</a>}
              </article>
            ))}
          </div>
          <h3>Capacidades</h3>
          <ul>
            {Object.entries(dashboard.capabilities).map(([name, capability]) => (
              <li key={name}>{name}: {capability.status}</li>
            ))}
          </ul>
          {dashboard.operational_health && (
            <aside aria-label="Saúde operacional">
              <h3>Saúde operacional</h3>
              <p>{dashboard.operational_health.status}</p>
              {dashboard.operational_health.backlog && <p>Backlog: {dashboard.operational_health.backlog.status}</p>}
            </aside>
          )}
        </>
      )}
    </section>
  );
}
