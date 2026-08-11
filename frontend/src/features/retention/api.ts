import { get, post } from "../../shared/http";
import { DeletionOperation, RetentionDetail, RetentionPreview, RetentionResponse } from "./types";

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

export function requestDeletion(
  id: string,
  body: { scope_hash: string; scope_version: string; confirmation: string; reason: string },
): Promise<DeletionOperation> {
  return post<DeletionOperation>(`/api/retention/documents/${encodeURIComponent(id)}/deletion`, body);
}

export function getDeletionStatus(id: string): Promise<DeletionOperation> {
  return get<DeletionOperation>(`/api/retention/deletions/${encodeURIComponent(id)}`);
}

export function resumeDeletion(id: string): Promise<DeletionOperation> {
  return post<DeletionOperation>(`/api/retention/deletions/${encodeURIComponent(id)}/resume`);
}
