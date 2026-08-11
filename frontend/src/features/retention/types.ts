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
  renders: Array<{
    id: string;
    renderer_id: string;
    renderer_version: string;
    state: string;
    source_digest: string;
    source_artifact: {
      id: string;
      digest_prefix: string;
      size_bytes: number | null;
      version: number;
      availability: "available" | "unavailable";
    };
    artifact: {
      id: string;
      digest_prefix: string;
      size_bytes: number | null;
      version: number;
      availability: "available" | "unavailable";
    } | null;
  }>;
  deletion: { authorized: false; message: string };
};

export type DeletionOperationState =
  | "pending"
  | "executing"
  | "recovery_required"
  | "failed"
  | "completed";

export type DeletionOperation = {
  id: string;
  target_document_id: string;
  state: DeletionOperationState;
  scope: { hash: string; version: string };
  reason: string;
  current_step: string | null;
  safe_error: string | null;
  result_code: string | null;
  requested_at: string;
  started_at: string | null;
  completed_at: string | null;
  checkpoint: Record<string, unknown>;
  items: Array<{
    id: string;
    kind: string;
    target_id: string;
    artifact_id: string | null;
    digest_prefix: string | null;
    size_bytes: number | null;
    version: number | null;
    state: string;
    attempts: number;
    safe_error: string | null;
  }>;
};
