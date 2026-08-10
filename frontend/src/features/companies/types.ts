export type CompanyFlow = { id: string; state: "habilitado" | "pausado" };

export type Company = {
  id: string;
  cnpj: string;
  legal_name: string;
  status: "cadastrada" | "ativa" | "desativada";
  first_collection_at: string | null;
  deactivation_reason: string | null;
  version: number;
  flows: Record<string, CompanyFlow>;
  enrichment: {
    status: string;
    public_non_authoritative: boolean;
    payload: unknown;
    error_code: string;
  } | null;
};
