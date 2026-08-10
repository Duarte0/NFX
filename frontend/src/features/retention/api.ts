import { get } from "../../shared/http";
import { RetentionDetail, RetentionPreview, RetentionResponse } from "./types";

export function listRetention(query = new URLSearchParams()): Promise<RetentionResponse> {
  query.set("limit", query.get("limit") ?? "50");
  return get<RetentionResponse>(`/api/retention/documents?${query.toString()}`);
}

export function getRetentionDetail(id: string): Promise<RetentionDetail> {
  return get<RetentionDetail>(`/api/retention/documents/${encodeURIComponent(id)}`);
}

export function getRetentionPreview(id: string, scopeHash?: string): Promise<RetentionPreview> {
  const query = scopeHash ? `?scope_hash=${encodeURIComponent(scopeHash)}` : "";
  return get<RetentionPreview>(`/api/retention/documents/${encodeURIComponent(id)}/preview${query}`);
}
