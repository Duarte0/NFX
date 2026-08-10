import { get } from "../../shared/http";
import { DocumentResponse } from "./types";

export function listDocuments(): Promise<DocumentResponse> {
  return get<DocumentResponse>("/api/documents?limit=50");
}
