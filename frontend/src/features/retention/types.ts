export type RetentionState = "retained" | "eligible" | "non_executable";

export type RetentionItem = {
  id: string;
  company_id: string;
  family: string;
  category: string;
  flow: string;
  state: RetentionState;
  reason_code: string;
  rule_version: string;
  basis_date: string | null;
  eligibility_date: string | null;
  calculated_on: string;
  scope_hash: string;
  detail_url: string;
  preview_url: string;
};

export type RetentionResponse = {
  documents: RetentionItem[];
  next_cursor: string | null;
  as_of: string;
  rule_version: string;
};

export type RetentionDetail = {
  document: RetentionItem;
  decision: {
    state: RetentionState;
    reason_code: string;
    rule_version: string;
    basis_date: string | null;
    eligibility_date: string | null;
    calculated_on: string;
  };
  preview_url: string;
};

export type RetentionPreview = {
  document: {
    id: string;
    company_id: string;
    family: string;
    category: string;
    flow: string;
    emitted_at: string;
    authorized_at: string | null;
  };
  decision: RetentionDetail["decision"];
  scope: { hash: string; version: string };
  evidence: Array<{
    id: string;
    artifact_id: string;
    digest_prefix: string;
    size_bytes: number;
    content_type: string;
    availability: "available" | "unavailable";
  }>;
  events: Array<{ id: string; category: string; evidence: RetentionPreview["evidence"] }>;
  deletion: { authorized: false; message: string };
};
