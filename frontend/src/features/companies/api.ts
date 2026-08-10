import { get, patch, post } from "../../shared/http";
import { Company } from "./types";

export function listCompanies(): Promise<{ companies: Company[] }> {
  return get<{ companies: Company[] }>("/api/companies");
}

export function createCompany(company: { cnpj: string; legal_name: string }): Promise<unknown> {
  return post<unknown>("/api/companies/create", company);
}

export function updateCompany(
  companyId: string,
  company: { cnpj: string; legal_name: string; version: number },
): Promise<unknown> {
  return patch<unknown>(`/api/companies/${companyId}`, company);
}

export function changeCompanyState(
  companyId: string,
  action: "activate" | "deactivate",
  body: object,
): Promise<unknown> {
  return post<unknown>(`/api/companies/${companyId}/${action}`, body);
}

export function changeFlow(
  companyId: string,
  family: "nfe" | "nfse",
  state: "habilitado" | "pausado",
): Promise<unknown> {
  return post<unknown>(`/api/companies/${companyId}/flows/${family}`, { state });
}

export function enrichCompany(companyId: string): Promise<unknown> {
  return post<unknown>(`/api/companies/${companyId}/enrichment`);
}
