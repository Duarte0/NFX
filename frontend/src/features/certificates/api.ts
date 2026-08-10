import { get, postForm } from "../../shared/http";
import { Certificate } from "./types";

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
