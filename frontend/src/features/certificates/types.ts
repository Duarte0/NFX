export type Certificate = {
  id: string;
  state: string;
  status: string;
  fingerprint_sha256: string;
  certificate_cnpj: string;
  not_before: string;
  not_after: string;
  days_until_expiry: number | null;
  key_version: number;
};
