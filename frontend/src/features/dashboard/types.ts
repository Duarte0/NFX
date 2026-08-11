export type DashboardSignal = {
  value: number | null;
  status: "ready" | "zero" | "unavailable" | "stale" | "partial" | "degraded" | "unknown";
  freshness: {
    status: "fresh" | "stale" | "unknown";
    evaluated_at: string | null;
    age_seconds: number | null;
  };
};

export type DashboardCard = {
  id: string;
  label: string;
  kind: "period" | "snapshot";
  current: DashboardSignal;
  previous: DashboardSignal | null;
  status: DashboardSignal["status"];
  freshness: DashboardSignal["freshness"];
  drilldown: { href: string; filters: Record<string, string> } | null;
};

export type BackupHealth = {
  status: "success" | "failure" | "unavailable";
  latest_backup: { state: string | null; safe_error: string };
  latest_success_age_seconds: number | null;
  retention: { daily: number | null; weekly: number | null; monthly: number | null };
  latest_restore: { state: string | null; safe_error: string };
};

export type DashboardResponse = {
  read_only: true;
  evaluated_at: string;
  period: {
    current: { from: string; to: string };
    previous: { from: string; to: string };
    boundary: "[from,to)";
  };
  cards: DashboardCard[];
  capabilities: Record<string, { status: string; reason?: string }>;
  operational_health?: {
    status: string;
    dependencies?: Record<string, string>;
    processes?: Record<string, { status: string; age_seconds: number | null }>;
    jobs?: { status: string; queue_counts?: Record<string, number> };
    backlog?: { status: string; oldest_due_age_seconds: number | null };
    backup?: BackupHealth;
  };
};
