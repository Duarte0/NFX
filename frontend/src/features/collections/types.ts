export type CollectionFlow = {
  family: "nfe" | "nfse";
  flow_state: string;
  collection_state: string;
  last_attempt_at: string | null;
  last_success_at: string | null;
  next_scheduled_at: string | null;
  cooldown_until: string | null;
  blocked_reason: string;
  safe_error: string;
  progress: { current: number; total: number };
  coverage: {
    status: string;
    source: string;
    verified_at: string;
    policy_version: string;
  } | null;
  active_execution: {
    id: string;
    state: string;
    safe_error: string;
    safe_summary: Record<string, unknown>;
  } | null;
  latest_execution: {
    id: string;
    state: string;
    safe_error: string;
    origin: string;
  } | null;
};

export type CollectionCompany = {
  company_id: string;
  legal_name: string;
  status: string;
  flows: CollectionFlow[];
};

export type CollectionExecutionFilter = {
  from: string;
  to: string;
  state: string;
};

export type CollectionExecutionSummary = {
  id: string;
  company_id: string;
  company_name: string;
  family: string;
  requested_scope: string;
  state: string;
  outcome: string;
  recovery: string;
  safe_error: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type CollectionExecutionResponse = {
  read_only: true;
  filter: CollectionExecutionFilter;
  boundary: "[from,to)";
  total: number;
  limit: number;
  truncated: boolean;
  executions: CollectionExecutionSummary[];
};
