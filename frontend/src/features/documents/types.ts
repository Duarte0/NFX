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
  xml_available: boolean;
  pdf_available: boolean;
  detail_url: string;
  download_url: string | null;
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

export type DocumentDetail = {
  id: string;
  company: { id: string; name: string };
  family: string;
  role: string;
  category: string;
  source: string;
  flow: string;
  identity: { kind: string; value: string };
  dates: { emitted_at: string; authorized_at: string | null; competence: string };
  situation: string;
  state: string;
  collection: { origin_execution_ref: string };
  parties: { issuer: string | null; recipient: string | null; provider: string | null };
  value_total: number | null;
  artifacts: Array<{
    id: string;
    digest_prefix: string;
    size_bytes: number;
    content_type: string;
    availability: "available" | "unavailable";
  }>;
  events: Array<{
    id: string;
    family: string;
    category: string;
    source: string;
    flow: string;
    identity: string;
    occurred_at: string;
    situation: string;
    relationship_type: string;
    state: string;
    artifacts: DocumentDetail["artifacts"];
  }>;
  availability: { xml: boolean; original: boolean; pdf: boolean };
  download_url: string;
};
