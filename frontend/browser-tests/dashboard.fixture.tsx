import { createRoot } from "react-dom/client";
import { DashboardPresentation } from "../src/features/dashboard/DashboardSection";
import { DashboardResponse } from "../src/features/dashboard/types";
import "../src/shared/ui/tokens.css";

const role = new URLSearchParams(window.location.search).get("role") ?? "visualizador";
const dashboard: DashboardResponse = {
  read_only: true,
  evaluated_at: "2026-08-12T12:00:00+00:00",
  period: {
    current: { from: "2026-08-01", to: "2026-09-01" },
    previous: { from: "2026-07-01", to: "2026-08-01" },
    boundary: "[from,to)",
  },
  cards: [
    {
      id: "companies.active",
      label: "Empresas ativas",
      kind: "snapshot",
      current: { value: 2, status: "ready", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: null,
      status: "ready",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?lifecycle=active#empresas", filters: { lifecycle: "active" } },
    },
    {
      id: "documents.total",
      label: "Documentos no período",
      kind: "period",
      current: { value: 5, status: "ready", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: { value: 0, status: "zero", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      status: "ready",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?from=2026-08-01&to=2026-09-01#documentos", filters: { from: "2026-08-01", to: "2026-09-01" } },
    },
    {
      id: "collections.partial",
      label: "Coletas parciais",
      kind: "period",
      current: { value: 1, status: "partial", freshness: { status: "stale", evaluated_at: "2026-08-12T11:00:00+00:00", age_seconds: 3600 } },
      previous: { value: null, status: "unavailable", freshness: { status: "unknown", evaluated_at: null, age_seconds: null } },
      status: "degraded",
      freshness: { status: "stale", evaluated_at: "2026-08-12T11:00:00+00:00", age_seconds: 3600 },
      drilldown: { href: "?from=2026-08-01&to=2026-09-01&state=partial#coletas", filters: { from: "2026-08-01", to: "2026-09-01", state: "partial" } },
    },
    {
      id: "jobs.pending",
      label: "Processamento pendente",
      kind: "period",
      current: { value: 1, status: "ready", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: { value: 0, status: "zero", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      status: "ready",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?from=2026-08-01&to=2026-09-01&filter=pending#dashboard", filters: { from: "2026-08-01", to: "2026-09-01", filter: "pending" } },
    },
    {
      id: "certificates.expired",
      label: "Certificados vencidos",
      kind: "snapshot",
      current: { value: 0, status: "zero", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: null,
      status: "zero",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?filter=expired#empresas", filters: { filter: "expired" } },
    },
  ],
  capabilities: {
    documents: { status: "available" },
    backup: { status: role === "administrador" ? "available" : "admin_only" },
  },
  operational_health: role === "administrador" ? {
    status: "degraded",
    dependencies: { postgres: "ready", minio: "unavailable" },
    processes: { worker: { status: "stale", age_seconds: 60 } },
    jobs: { status: "ready", queue_counts: { queued: 2 } },
    backlog: { status: "delayed", oldest_due_age_seconds: 600 },
    backup: {
      status: "success",
      latest_backup: { state: "complete", safe_error: "" },
      latest_success_age_seconds: 60,
      retention: { daily: 2, weekly: 1, monthly: 1 },
      latest_restore: { state: "success", safe_error: "" },
    },
  } : undefined,
};

window.fetch = async () => {
  throw new Error("Browser fixture does not permit network requests");
};

createRoot(document.getElementById("root")!).render(
  <main lang="pt-BR">
    <h1>Dashboard sintético</h1>
    <DashboardPresentation
      dashboard={dashboard}
      loading={false}
      error=""
      onRetry={() => undefined}
      onOpenJobDrilldown={() => undefined}
    />
  </main>,
);
