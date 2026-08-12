import { get, post } from "../../shared/http";
import { DocumentDetail, DocumentResponse } from "./types";

export function listDocuments(query: URLSearchParams): Promise<DocumentResponse> {
  query.set("limit", query.get("limit") ?? "50");
  return get<DocumentResponse>(`/api/documents?${query.toString()}`);
}

export function getDocument(id: string): Promise<DocumentDetail> {
  return get<DocumentDetail>(`/api/documents/${encodeURIComponent(id)}`);
}

export function requestPdf(
  requestUrl: string,
  regenerate = false,
): Promise<{ pdf: DocumentDetail["pdf"] }> {
  return post<{ pdf: DocumentDetail["pdf"] }>(
    requestUrl,
    { regenerate },
  );
}

export async function downloadDocument(path: string): Promise<void> {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error("download_failed");
  }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "documento-fiscal";
  link.click();
  URL.revokeObjectURL(link.href);
}
