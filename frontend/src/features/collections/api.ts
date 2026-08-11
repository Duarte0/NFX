import { get, post } from "../../shared/http";
import {
  CollectionCompany,
  CollectionExecutionFilter,
  CollectionExecutionResponse,
} from "./types";

export function listCollections(): Promise<{ collections: CollectionCompany[] }> {
  return get<{ collections: CollectionCompany[] }>("/api/collections");
}

export function listCollectionExecutions(
  filter: CollectionExecutionFilter,
): Promise<CollectionExecutionResponse> {
  const query = new URLSearchParams();
  if (filter.from) query.set("from", filter.from);
  if (filter.to) query.set("to", filter.to);
  if (filter.state) query.set("state", filter.state);
  return get<CollectionExecutionResponse>(`/api/collections/executions?${query.toString()}`);
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
