import { get } from "../../shared/http";
import { AuditResponse } from "./types";

export function listAuditEvents(query = new URLSearchParams()): Promise<AuditResponse> {
  const params = new URLSearchParams(query);
  if (!params.has("limit")) params.set("limit", "50");
  return get<AuditResponse>(`/api/audit/events?${params.toString()}`);
}
