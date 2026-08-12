import { createRoot } from "react-dom/client";
import { useRef, useState } from "react";
import { ExportsPresentation } from "../src/features/exports/ExportsSection";
import type { ExportDetail, ExportItemSummary, ExportState } from "../src/features/exports/types";
import "../src/shared/ui/tokens.css";

const params = new URLSearchParams(window.location.search);
const role = params.get("role") ?? "visualizador";
const session = params.get("session") ?? "authenticated";

const stateFixtures: Array<{ state: ExportState; safeError: string | null; produced: number; bytes: number; url: string | null }> = [
  { state: "pending", safeError: null, produced: 0, bytes: 0, url: null },
  { state: "processing", safeError: null, produced: 2, bytes: 2048, url: null },
  { state: "complete", safeError: null, produced: 4, bytes: 4096, url: null },
  { state: "available", safeError: null, produced: 4, bytes: 4096, url: "/api/exports/export-available/download" },
  { state: "partial", safeError: "partial_result", produced: 3, bytes: 3072, url: "/api/exports/export-partial/download" },
  { state: "failed", safeError: "all_items_failed", produced: 0, bytes: 0, url: null },
  { state: "expired", safeError: "expired", produced: 4, bytes: 4096, url: null },
  { state: "excluded", safeError: null, produced: 0, bytes: 0, url: null },
];

const exportSummaries: ExportItemSummary[] = stateFixtures.map(({ state, safeError, produced, bytes, url }, index) => ({
  id: `export-${state}`,
  state,
  expected_count: 4,
  produced_count: produced,
  expected_bytes: 4096,
  produced_bytes: bytes,
  created_at: "2026-08-12T10:00:00+00:00",
  expires_at: "2026-08-13T10:00:00+00:00",
  safe_error: safeError,
  download_url: url,
  ...(index === 0 ? { expected_count: 4 } : {}),
}));

function detailFor(item: ExportItemSummary): ExportDetail {
  return {
    ...item,
    requester_id: "requester-synthetic",
    filter_snapshot: { family: "nfe", direction: "entrada", company_ids: ["company-not-rendered"] },
    selection_snapshot: { document_ids: ["document-not-rendered"] },
    items: [{
      document_id: "document-not-rendered",
      state: item.state === "partial" ? "missing" : "included",
      archive_path: "/archive/path-not-rendered",
      safe_error: item.state === "partial" ? "source_missing" : null,
      size_bytes: item.produced_bytes,
    }],
  };
}

function ExportsFixture() {
  const [notice, setNotice] = useState("");
  const [exports, setExports] = useState(exportSummaries);
  const [detail, setDetail] = useState<ExportDetail | null>(null);
  const [selectedExportId, setSelectedExportId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailStale, setDetailStale] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [requestBusy, setRequestBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [requestCount, setRequestCount] = useState(0);
  const refreshAttempt = useRef(0);
  const requestBusyRef = useRef(false);
  const detailSequence = useRef(0);

  if (session !== "authenticated") {
    return (
      <main lang="pt-BR">
        <h1>Exportações sintéticas</h1>
        <p role="alert">Acesse sua conta.</p>
      </main>
    );
  }

  function refresh() {
    setLoading(true);
    setStale(true);
    setError("");
    const attempt = ++refreshAttempt.current;
    window.setTimeout(() => {
      setLoading(false);
      if (attempt === 1) {
        setError("A atualização das exportações está indisponível.");
        setStale(true);
        return;
      }
      setStale(false);
      setError("");
      setExports(exportSummaries);
    }, 120);
  }

  function request() {
    if (requestBusyRef.current) return;
    requestBusyRef.current = true;
    setRequestBusy(true);
    setRequestCount((current) => current + 1);
    setNotice("Solicitação enviada uma vez; o estado será confirmado pelo servidor.");
    window.setTimeout(() => {
      requestBusyRef.current = false;
      setRequestBusy(false);
    }, 120);
  }

  function selectExport(id: string) {
    const sequence = ++detailSequence.current;
    const item = exports.find((candidate) => candidate.id === id);
    if (!item) return;
    setSelectedExportId(id);
    setDetail(null);
    setDetailError("");
    setDetailStale(false);
    setDetailLoading(true);
    window.setTimeout(() => {
      if (sequence !== detailSequence.current) return;
      setDetail(detailFor(item));
      setDetailLoading(false);
    }, id === "export-pending" ? 220 : 40);
  }

  function closeDetail() {
    ++detailSequence.current;
    setSelectedExportId(null);
    setDetail(null);
    setDetailLoading(false);
    setDetailError("");
  }

  return (
    <main lang="pt-BR">
      <h1>Exportações sintéticas</h1>
      <p>Perfil sintético: {role}</p>
      <p data-testid="request-count">Solicitações sintéticas: {requestCount}</p>
      {notice && <p role="status">{notice}</p>}
      <ExportsPresentation
        exports={exports}
        listReady
        detail={detail}
        loading={loading}
        stale={stale}
        error={error}
        detailLoading={detailLoading}
        detailStale={detailStale}
        detailError={detailError}
        requestBusy={requestBusy}
        actionBusy={actionBusy}
        selectedExportId={selectedExportId}
        onRequest={request}
        onReload={refresh}
        onRetry={refresh}
        onSelectExport={selectExport}
        onRetryDetail={() => selectedExportId && selectExport(selectedExportId)}
        onDownload={(item) => {
          setActionBusy(item.id);
          setNotice("Download autorizado solicitado.");
          window.setTimeout(() => setActionBusy(null), 80);
        }}
        onCloseDetail={closeDetail}
      />
    </main>
  );
}

window.fetch = async () => {
  throw new Error("Browser fixture does not permit network requests");
};

createRoot(document.getElementById("root")!).render(<ExportsFixture />);
