import { get, postForm } from "../../shared/http";
import { Certificate, CertificateInventoryResponse } from "./types";

export function getCertificate(companyId: string): Promise<{ certificate: Certificate | null }> {
  return get<{ certificate: Certificate | null }>(`/api/companies/${companyId}/certificate`);
}

export function uploadCertificate(
  companyId: string,
  file: File,
  password: string,
): Promise<unknown> {
  const form = new FormData();
  form.append("certificate", file);
  form.append("password", password);
  return postForm<unknown>(`/api/companies/${companyId}/certificate/upload`, form);
}

export function listCertificateInventory(
  filter: string,
  limit = 50,
  cursor?: string,
): Promise<CertificateInventoryResponse> {
  const query = new URLSearchParams({ filter, limit: String(limit) });
  if (cursor) query.set("cursor", cursor);
  return get<CertificateInventoryResponse>(`/api/certificates/inventory?${query.toString()}`);
}
