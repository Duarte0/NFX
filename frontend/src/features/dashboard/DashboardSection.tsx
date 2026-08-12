import { FormEvent, MouseEvent, useCallback, useEffect, useRef, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { Badge, Button, Field, Panel } from "../../shared/ui/primitives";
import { getDashboard } from "./api";
import { JobObservabilityPanel } from "./JobObservabilityPanel";
import { BackupHealth, DashboardCard, DashboardResponse, DashboardSignal } from "./types";

type DashboardStatus = DashboardSignal["status"];
type DashboardGroupKey = "fiscal" | "processing" | "certificates" | "other";

const dashboardGroups: ReadonlyArray<{
  key: DashboardGroupKey;
  title: string;
  description: string;
}> = [
  {
    key: "fiscal",
    title: "Indicadores fiscais e operacionais",
    description: "Empresas e documentos preservados pelo período selecionado.",
  },
  {
    key: "processing",
    title: "Coletas e processamento",
    description: "Execuções de coleta e jobs reconciliados com seus owners.",
  },
  {
    key: "certificates",
    title: "Certificados e capacidades",
    description: "Inventário protegido e capacidades declaradas pelo servidor.",
  },
  {
    key: "other",
    title: "Outros indicadores",
    description: "Indicadores adicionais fornecidos pelo servidor.",
  },
];

const capabilityLabels: Record<string, string> = {
  fiscal_sources: "Fontes fiscais",
  documents: "Documentos",
  rendering: "Renderização de PDF",
  disk: "Armazenamento em disco",
  backup: "Backup",
  certificates: "Certificados",
  operational_health: "Saúde operacional",
};

const capabilityStatusLabels: Record<string, string> = {
  available: "Disponível",
  unavailable: "Indisponível",
  admin_only: "Somente Administrador",
  proposed: "Proposto",
  pending: "Pendente",
};

const healthStatusLabels: Record<string, string> = {
  ready: "Pronta",
  available: "Disponível",
  degraded: "Degradada",
  unavailable: "Indisponível",
  stale: "Desatualizada",
  missing: "Ausente",
  stopped: "Parada",
  delayed: "Atrasada",
  success: "Sucesso",
  failure: "Falha",
  complete: "Concluído",
  partial: "Parcial",
  failed: "Falhou",
  expired: "Expirado",
  running: "Em execução",
};

const dependencyLabels: Record<string, string> = {
  postgres: "Banco de dados",
  schema: "Esquema do banco",
  minio: "Armazenamento de objetos",
};

const processLabels: Record<string, string> = {
  worker: "Worker de processamento",
  scheduler: "Agendador",
};

const queueLabels: Record<string, string> = {
  queued: "Na fila",
  running: "Em execução",
  blocked: "Bloqueados",
  completed: "Concluídos",
};

function statusLabel(status: DashboardStatus): string {
  return {
    ready: "Disponível",
    zero: "Zero real no período",
    stale: "Desatualizado",
    partial: "Parcial",
    degraded: "Degradado",
    unavailable: "Indisponível",
    unknown: "Desconhecido",
  }[status];
}

function valueLabel(signal: DashboardSignal): string {
  return signal.value === null ? "Não disponível" : String(signal.value);
}

function capabilityStatusLabel(status: string): string {
  return capabilityStatusLabels[status] ?? "Estado da capacidade não reconhecido";
}

function healthStatusLabel(status: string): string {
  return healthStatusLabels[status] ?? "Estado operacional não reconhecido";
}

function badgeVariant(status: string): "success" | "warning" | "danger" | "neutral" {
  if (["ready", "available", "success", "complete"].includes(status)) return "success";
  if (["stale", "partial", "degraded", "delayed", "missing", "stopped", "running"].includes(status)) {
    return "warning";
  }
  if (["unavailable", "failure", "failed", "expired"].includes(status)) return "danger";
  return "neutral";
}

function formatAge(ageSeconds: number | null): string {
  if (ageSeconds === null) return "Idade não informada";
  const total = Math.max(0, Math.floor(ageSeconds));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}min`;
  if (minutes > 0) return `${minutes}min ${seconds}s`;
  return `${seconds}s`;
}

function freshnessLabel(freshness: DashboardSignal["freshness"]): string {
  const state = {
    fresh: "Atualizada",
    stale: "Desatualizada",
    unknown: "Frescura não informada",
  }[freshness.status];
  const evaluated = freshness.evaluated_at ? ` · avaliada em ${freshness.evaluated_at}` : "";
  const age = freshness.age_seconds === null ? "" : ` · idade ${formatAge(freshness.age_seconds)}`;
  return `${state}${evaluated}${age}`;
}

function backupStatusLabel(status: BackupHealth["status"]): string {
  return {
    success: "Sucesso",
    failure: "Falha",
    unavailable: "Indisponível",
  }[status];
}

function backupStateLabel(state: string | null): string {
  return healthStatusLabel(state ?? "unknown");
}

function backupCoverageLabel(backup: BackupHealth): string {
  if (backup.status === "success" && backup.latest_backup.state !== null && backup.latest_backup.state !== "complete") {
    return `Sucesso anterior; último conjunto ${backupStateLabel(backup.latest_backup.state).toLowerCase()}`;
  }
  return backupStatusLabel(backup.status);
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

function dashboardGroupForCardId(cardId: string): DashboardGroupKey {
  const prefix = cardId.split(".", 1)[0];
  if (prefix === "companies" || prefix === "documents") return "fiscal";
  if (prefix === "collections" || prefix === "jobs") return "processing";
  if (prefix === "certificates") return "certificates";
  return "other";
}

function cardsForGroup(cards: DashboardCard[], key: DashboardGroupKey): DashboardCard[] {
  return cards.filter((card) => dashboardGroupForCardId(card.id) === key);
}

function SignalSummary({ label, signal }: { label: string; signal: DashboardSignal }) {
  return (
    <div className="dashboard-card__signal">
      <span className="dashboard-card__signal-label">{label}</span>
      <strong className="dashboard-card__value">{valueLabel(signal)}</strong>
      <Badge variant={badgeVariant(signal.status)}>{statusLabel(signal.status)}</Badge>
    </div>
  );
}

function DashboardCardView({
  card,
  onOpenJobDrilldown,
}: {
  card: DashboardCard;
  onOpenJobDrilldown: (event: MouseEvent<HTMLAnchorElement>, card: DashboardCard) => void;
}) {
  return (
    <Panel as="article" id={`dashboard-card-${card.id.replaceAll(".", "-")}`} title={card.label} className="dashboard-card">
      <div className="dashboard-card__status" aria-label={`Estado geral: ${statusLabel(card.status)}`}>
        <Badge variant={badgeVariant(card.status)}>{statusLabel(card.status)}</Badge>
        <span className="dashboard-card__freshness">{freshnessLabel(card.freshness)}</span>
      </div>
      <div className="dashboard-card__signals">
        <SignalSummary label={card.kind === "period" ? "Período atual" : "Valor atual"} signal={card.current} />
        {card.previous && <SignalSummary label="Período anterior" signal={card.previous} />}
      </div>
      {card.drilldown && (
        <a
          className="dashboard-card__link"
          href={card.drilldown.href}
          aria-label={`Abrir lista correspondente a ${card.label}`}
          onClick={(event) => onOpenJobDrilldown(event, card)}
        >
          Abrir lista correspondente
        </a>
      )}
    </Panel>
  );
}

function DashboardCards({
  cards,
  onOpenJobDrilldown,
}: {
  cards: DashboardCard[];
  onOpenJobDrilldown: (event: MouseEvent<HTMLAnchorElement>, card: DashboardCard) => void;
}) {
  if (cards.length === 0) {
    return <Feedback state="empty" message="Nenhum indicador foi fornecido para este período." />;
  }

  return (
    <div className="dashboard-groups">
      {dashboardGroups.map((group) => {
        const groupCards = cardsForGroup(cards, group.key);
        if (groupCards.length === 0) return null;
        return (
          <Panel
            as="section"
            id={`dashboard-group-${group.key}`}
            key={group.key}
            title={group.title}
            className="dashboard-group"
          >
            <p className="dashboard-group__description">{group.description}</p>
            <div className="dashboard-card-grid">
              {groupCards.map((card) => (
                <DashboardCardView key={card.id} card={card} onOpenJobDrilldown={onOpenJobDrilldown} />
              ))}
            </div>
          </Panel>
        );
      })}
    </div>
  );
}

function CapabilitySummary({ dashboard }: { dashboard: DashboardResponse }) {
  return (
    <Panel as="section" id="dashboard-capabilities" title="Capacidades" className="dashboard-capabilities">
      <p>Estados declarados pelo servidor, sem cálculo ou autorização no navegador.</p>
      <ul className="dashboard-status-list">
        {Object.entries(dashboard.capabilities).map(([name, capability], index) => {
          const label = capabilityLabels[name] ?? `Capacidade adicional ${index + 1}`;
          return (
            <li key={name}>
              <span>{label}</span>
              <Badge variant={badgeVariant(capability.status)}>{capabilityStatusLabel(capability.status)}</Badge>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

function OperationalHealth({ dashboard }: { dashboard: DashboardResponse }) {
  const health = dashboard.operational_health;
  if (!health) return null;

  return (
    <Panel as="aside" id="dashboard-operational-health" title="Saúde operacional" className="dashboard-health">
      <div className="dashboard-card__status">
        <Badge variant={badgeVariant(health.status)}>{healthStatusLabel(health.status)}</Badge>
        <span>Somente leitura e visível quando o servidor fornece esta seção autorizada.</span>
      </div>
      {health.dependencies && (
        <div className="dashboard-health__block">
          <h4>Dependências</h4>
          <ul className="dashboard-status-list">
            {Object.entries(health.dependencies).map(([name, status], index) => (
              <li key={name}>
                <span>{dependencyLabels[name] ?? `Dependência adicional ${index + 1}`}</span>
                <Badge variant={badgeVariant(status)}>{healthStatusLabel(status)}</Badge>
              </li>
            ))}
          </ul>
        </div>
      )}
      {health.processes && (
        <div className="dashboard-health__block">
          <h4>Processos</h4>
          <ul className="dashboard-status-list">
            {Object.entries(health.processes).map(([name, process], index) => (
              <li key={name}>
                <span>{processLabels[name] ?? `Processo adicional ${index + 1}`}</span>
                <span>
                  <Badge variant={badgeVariant(process.status)}>{healthStatusLabel(process.status)}</Badge>
                  <small> · idade {formatAge(process.age_seconds)}</small>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {health.jobs && (
        <div className="dashboard-health__block">
          <h4>Jobs</h4>
          <p><Badge variant={badgeVariant(health.jobs.status)}>{healthStatusLabel(health.jobs.status)}</Badge></p>
          {health.jobs.queue_counts && (
            <ul className="dashboard-status-list">
              {Object.entries(health.jobs.queue_counts).map(([name, count], index) => (
                <li key={name}>
                  <span>{queueLabels[name] ?? `Fila adicional ${index + 1}`}</span>
                  <strong>{count}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {health.backlog && (
        <div className="dashboard-health__block">
          <h4>Backlog</h4>
          <p>
            <Badge variant={badgeVariant(health.backlog.status)}>{healthStatusLabel(health.backlog.status)}</Badge>
            {` · item mais antigo: ${formatAge(health.backlog.oldest_due_age_seconds)}`}
          </p>
        </div>
      )}
      {health.backup && (
        <Panel as="section" id="dashboard-backup-health" title="Backup">
          <p>
            <strong>Estado da cobertura:</strong> {backupCoverageLabel(health.backup)}
          </p>
          <p>
            <strong>Último conjunto:</strong> {backupStateLabel(health.backup.latest_backup.state)}
          </p>
          {health.backup.latest_backup.safe_error && (
            <p role="status">{safeErrorLabel(health.backup.latest_backup.safe_error)}</p>
          )}
          <p><strong>Idade do último sucesso:</strong> {formatAge(health.backup.latest_success_age_seconds)}</p>
          <p>
            <strong>Retenção concluída:</strong> diária {health.backup.retention.daily ?? "não informada"}, semanal {health.backup.retention.weekly ?? "não informada"}, mensal {health.backup.retention.monthly ?? "não informada"}
          </p>
          <p><strong>Última validação:</strong> {backupStateLabel(health.backup.latest_restore.state)}</p>
          {health.backup.latest_restore.state === "failed" && (
            <p role="status">Falha na última validação: {safeErrorLabel(health.backup.latest_restore.safe_error)}</p>
          )}
        </Panel>
      )}
    </Panel>
  );
}

export type DashboardPresentationProps = {
  dashboard: DashboardResponse | null;
  loading: boolean;
  error: string;
  onRetry: () => void;
  onOpenJobDrilldown: (event: MouseEvent<HTMLAnchorElement>, card: DashboardCard) => void;
};

export function DashboardPresentation({
  dashboard,
  loading,
  error,
  onRetry,
  onOpenJobDrilldown,
}: DashboardPresentationProps) {
  const hasStaleRead = dashboard !== null && (loading || Boolean(error));

  return (
    <>
      {loading && <Feedback state="loading" message="Carregando dashboard…" />}
      {hasStaleRead && (
        <div className="dashboard-state dashboard-state--stale" role="status" aria-live="polite">
          <Badge variant="warning">Desatualizado</Badge>
          <p>A última leitura segura permanece visível enquanto esta seleção é atualizada ou revalidada.</p>
        </div>
      )}
      {error && (
        <div className="dashboard-request-error">
          <Feedback message={error} state="error" />
          <Button variant="secondary" onClick={onRetry}>Tentar novamente</Button>
        </div>
      )}
      {dashboard && (
        <>
          <div className="dashboard-period" role="status">
            <div>
              <strong>Período atual</strong>
              <span>{dashboard.period.current.from} até {dashboard.period.current.to}</span>
            </div>
            <div>
              <strong>Comparativo anterior</strong>
              <span>{dashboard.period.previous.from} até {dashboard.period.previous.to}</span>
            </div>
            <span className="dashboard-period__boundary">Fronteira: {dashboard.period.boundary}</span>
            <span className="dashboard-period__evaluated">Avaliado em: {dashboard.evaluated_at}</span>
          </div>
          <DashboardCards cards={dashboard.cards} onOpenJobDrilldown={onOpenJobDrilldown} />
          <CapabilitySummary dashboard={dashboard} />
          <OperationalHealth dashboard={dashboard} />
        </>
      )}
    </>
  );
}

function periodFromLocation(): { from: string; to: string } {
  if (typeof window === "undefined") return { from: "", to: "" };
  if (window.location.hash && window.location.hash !== "#dashboard") return { from: "", to: "" };
  const query = new URLSearchParams(window.location.search);
  return { from: query.get("from") ?? "", to: query.get("to") ?? "" };
}

type DashboardSectionProps = { loadSignal: number; notify: (message: string) => void };

export function DashboardSection({ loadSignal, notify }: DashboardSectionProps) {
  const initialPeriod = periodFromLocation();
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [from, setFrom] = useState(initialPeriod.from);
  const [to, setTo] = useState(initialPeriod.to);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestSequence = useRef(0);

  const loadDashboard = useCallback(async () => {
    const sequence = requestSequence.current + 1;
    requestSequence.current = sequence;
    setLoading(true);
    setError("");
    try {
      const nextDashboard = await getDashboard(from || undefined, to || undefined);
      if (sequence !== requestSequence.current) return;
      setDashboard(nextDashboard);
    } catch {
      if (sequence !== requestSequence.current) return;
      setError("Não foi possível carregar o dashboard.");
      notify("Não foi possível carregar o dashboard.");
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
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
    <section id="dashboard" aria-labelledby="dashboard-title">
      <h2 id="dashboard-title">Dashboard</h2>
      <p>Somente leitura. Intervalos usam [início, fim) em datas civis de Brasília.</p>
      <div className="dashboard-toolbar">
        <form className="dashboard-period-form" onSubmit={submit}>
          <Field id="dashboard-from" label="De">
            <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
          </Field>
          <Field id="dashboard-to" label="Até">
            <input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
          </Field>
          <Button type="submit">Aplicar período</Button>
        </form>
        <Button variant="secondary" onClick={() => void loadDashboard()}>Atualizar dashboard</Button>
      </div>
      <DashboardPresentation
        dashboard={dashboard}
        loading={loading}
        error={error}
        onRetry={() => void loadDashboard()}
        onOpenJobDrilldown={openJobDrilldown}
      />
      {dashboard && <JobObservabilityPanel loadSignal={loadSignal} notify={notify} />}
    </section>
  );
}
