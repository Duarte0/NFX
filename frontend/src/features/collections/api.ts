import { get, post } from "../../shared/http";
import { CollectionCompany } from "./types";

export function listCollections(): Promise<{ collections: CollectionCompany[] }> {
  return get<{ collections: CollectionCompany[] }>("/api/collections");
}

export function requestCollection(
  companyId: string,
  scope: "completa" | "nfe" | "nfse",
): Promise<unknown> {
  return post<unknown>(`/api/companies/${companyId}/collection/request`, { scope });
}

export function retryCollection(companyId: string, executionId: string): Promise<unknown> {
  return post<unknown>(`/api/companies/${companyId}/collection/retry/${executionId}`);
}
