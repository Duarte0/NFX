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
};
