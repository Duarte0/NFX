export type AuditEvent = {
  id: string;
  sequence: number;
  occurred_at: string;
  action: string;
  entity_type: string;
  entity_id: string;
  result: string;
  reason: string;
  actor_id: string | null;
  actor_role?: string;
  ip_address?: string | null;
  correlation_id?: string;
  context?: Record<string, unknown>;
  hash?: string;
};

export type AuditResponse = {
  events: AuditEvent[];
  next_cursor: number | null;
  integrity: boolean;
};

export type AuditFilters = {
  actor_id: string;
  action: string;
  entity_type: string;
  result: string;
  cursor: string;
};
