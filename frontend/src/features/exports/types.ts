export type ExportState =
  | "pending"
  | "processing"
  | "complete"
  | "partial"
  | "failed"
  | "available"
  | "expired"
  | "excluded";

export type ExportItem = {
  document_id: string;
  state: string;
  archive_path: string | null;
  safe_error: string | null;
  size_bytes: number;
};

export type ExportItemSummary = {
  id: string;
  state: ExportState;
  expected_count: number;
  produced_count: number;
  expected_bytes: number;
  produced_bytes: number;
  created_at: string;
  expires_at: string;
  safe_error: string | null;
  download_url: string | null;
};

export type ExportDetail = ExportItemSummary & {
  requester_id: string;
  filter_snapshot: Record<string, unknown>;
  selection_snapshot: Record<string, unknown>;
  items: ExportItem[];
};
