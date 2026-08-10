export type DocumentItem = {
  id: string;
  company_id: string;
  company_name: string;
  family: string;
  role: string | null;
  category: string;
  source: string | null;
  flow: string;
  identity: string;
  identity_kind: string | null;
  emitted_at: string | null;
  authorized_at: string | null;
  competence: string | null;
  situation: string | null;
  outcome: "persisted" | "quarantine" | "conflict";
  evidence_available: boolean;
  reason_code: string | null;
};

export type DocumentResponse = {
  status:
    | "available"
    | "valid_empty"
    | "unavailable"
    | "no_coverage"
    | "unknown"
    | "partial"
    | "retry"
    | "blocked";
  reason_code: string;
  documents: DocumentItem[];
  collection_states: Array<{
    company_id: string | null;
    family: string | null;
    flow: string | null;
    status: string;
    reason_code: string;
  }>;
  next_cursor: string | null;
};
