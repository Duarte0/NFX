import { get } from "../../shared/http";
import { AuditEvent } from "./types";

export function listAuditEvents(): Promise<{ events: AuditEvent[] }> {
  return get<{ events: AuditEvent[] }>("/api/audit/events");
}
