import { get, post } from "../../shared/http";
import { ExportDetail, ExportItemSummary } from "./types";

export function listExports(): Promise<{ exports: ExportItemSummary[] }> {
  return get<{ exports: ExportItemSummary[] }>("/api/exports");
}

export function createExport(filters: Record<string, unknown>, idempotencyKey: string): Promise<ExportItemSummary> {
  return post<ExportItemSummary>("/api/exports", { ...filters, idempotency_key: idempotencyKey });
}

export function getExport(id: string): Promise<ExportDetail> {
  return get<ExportDetail>(`/api/exports/${encodeURIComponent(id)}`);
}

export async function downloadExport(path: string): Promise<void> {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) throw new Error("export_download_failed");
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "exportacao-fiscal.zip";
  link.click();
  URL.revokeObjectURL(link.href);
}
