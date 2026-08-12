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

export type CertificateInventoryFilter = "current" | "expired" | "expiring";

export type CertificateInventoryRow = {
  id: string;
  company: { id: string; cnpj: string; legal_name: string };
  state: string;
  status: string;
  not_before: string;
  not_after: string;
  days_until_expiry: number | null;
};

export type CertificateInventoryResponse = {
  certificates: CertificateInventoryRow[];
  filter: { filter: CertificateInventoryFilter };
  evaluated_at: string;
  freshness: {
    status: "fresh" | "stale" | "unknown";
    evaluated_at: string | null;
    age_seconds: number | null;
  };
  total: number;
  limit: number;
  truncated: boolean;
  next_cursor: string | null;
};
