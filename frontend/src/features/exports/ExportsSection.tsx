import { useCallback, useEffect, useRef, useState } from "react";
import { Feedback, type FeedbackState } from "../../shared/ui/Feedback";
import { Badge, Button, DataTable, Panel } from "../../shared/ui/primitives";
import { createExport, downloadExport, getExport, listExports } from "./api";
import type { ExportDetail, ExportItemSummary, ExportState } from "./types";

type ExportsSectionProps = { loadSignal: number; notify: (message: string) => void };

const exportStateLabels: Record<ExportState, string> = {
  pending: "Pendente",
  processing: "Processando",
  complete: "Concluída",
  partial: "Parcial",
  failed: "Falhou",
  available: "Disponível para download",
  expired: "Expirada",
  excluded: "Excluída",
};

const exportStateExplanations: Record<ExportState, string> = {
  pending: "A solicitação aguarda processamento pelo servidor.",
  processing: "O servidor está processando a seleção congelada.",
  complete: "A composição foi concluída; o download só aparece quando o servidor o autoriza.",
  partial: "Parte do escopo autorizado não foi produzida; esta exportação não é um ZIP completo.",
  failed: "A exportação não foi concluída.",
  available: "A exportação está disponível dentro do prazo informado pelo servidor.",
  expired: "A exportação expirou; os documentos de origem permanecem no acervo.",
  excluded: "Esta exportação não está disponível.",
};

const exportStateVariants: Record<ExportState, "brand" | "neutral" | "success" | "warning" | "danger" | "info"> = {
  pending: "info",
  processing: "info",
  complete: "success",
  partial: "warning",
  failed: "danger",
  available: "success",
  expired: "neutral",
  excluded: "danger",
};

const safeExportErrors: Record<string, string> = {
  partial_result: "O servidor produziu apenas parte do escopo autorizado.",
  all_items_failed: "Nenhum item do escopo autorizado foi produzido.",
  expired: "O prazo da exportação terminou.",
};

export function exportStateLabel(state: ExportState | string): string {
  return exportStateLabels[state as ExportState] ?? "Indisponível";
}

function exportStateExplanation(state: ExportState | string): string {
  return exportStateExplanations[state as ExportState] ?? "O estado da exportação não está disponível.";
}

function exportStateVariant(state: ExportState | string): "brand" | "neutral" | "success" | "warning" | "danger" | "info" {
  return exportStateVariants[state as ExportState] ?? "warning";
}

function safeExportError(error: string | null | undefined): string {
  return (error && safeExportErrors[error]) || "O servidor informou uma condição que requer atenção.";
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return null;
  return parsed.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

function dateValue(value: string | null | undefined) {
  const formatted = formatDate(value);
  return formatted && value
    ? <time dateTime={value}>{formatted}</time>
    : <span className="export-safe-note">Data não informada pelo servidor.</span>;
}

function formatBytes(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "Não informado";
  if (value < 1024) return `${value} bytes`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
}

function canDownload(item: Pick<ExportItemSummary, "state" | "download_url">): boolean {
  return item.state === "available" && typeof item.download_url === "string" && item.download_url.length > 0;
}

function scopeLabel(snapshot: Record<string, unknown>): string {
  const values: string[] = [];
  if (snapshot.family === "nfe") values.push("NF-e");
  if (snapshot.family === "nfse") values.push("NFS-e");
  if (snapshot.direction === "entrada") values.push("Entrada");
  if (snapshot.direction === "saida") values.push("Saída");
  if (snapshot.nfse_category === "tomada") values.push("Tomada");
  if (snapshot.nfse_category === "prestada") values.push("Prestada");
  return values.length ? `Escopo congelado pelo servidor: ${values.join(" · ")}` : "Escopo congelado pelo servidor.";
}

function stateBadge(state: ExportState | string) {
  return <Badge variant={exportStateVariant(state)}>{exportStateLabel(state)}</Badge>;
}

function stateContext(item: Pick<ExportItemSummary, "state" | "safe_error">) {
  return (
    <div className="export-state" role="status" aria-live="polite">
      {stateBadge(item.state)}
      <p>{exportStateExplanation(item.state)}</p>
      {item.safe_error && <p>{safeExportError(item.safe_error)}</p>}
    </div>
  );
}

function serverMetric(label: string, value: number | null | undefined, formatter: (value: number) => string) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return <span><strong>{label}:</strong> {formatter(value)}</span>;
}

function exportMetrics(item: Pick<ExportItemSummary, "expected_count" | "produced_count" | "expected_bytes" | "produced_bytes">) {
  return (
    <div className="export-summary" aria-label="Metadados retornados pelo servidor">
      {serverMetric("Itens produzidos pelo servidor", item.produced_count, (value) => String(value))}
      {serverMetric("Itens esperados pelo servidor", item.expected_count, (value) => String(value))}
      {serverMetric("Bytes produzidos pelo servidor", item.produced_bytes, formatBytes)}
      {serverMetric("Bytes esperados pelo servidor", item.expected_bytes, formatBytes)}
    </div>
  );
}

function downloadAction(
  item: ExportItemSummary,
  actionBusy: string | null,
  onDownload: (item: ExportItemSummary) => void,
) {
  if (!canDownload(item)) {
    return <span className="export-safe-note">Download não autorizado pelo servidor para este estado.</span>;
  }
  return (
    <Button
      variant="secondary"
      disabled={actionBusy === item.id}
      aria-busy={actionBusy === item.id}
      onClick={() => onDownload(item)}
    >
      {actionBusy === item.id ? "Baixando…" : "Baixar ZIP"}
    </Button>
  );
}

export type ExportsPresentationProps = {
  exports: ExportItemSummary[];
  listReady: boolean;
  detail: ExportDetail | null;
  loading: boolean;
  stale: boolean;
  error: string;
  detailLoading: boolean;
  detailStale: boolean;
  detailError: string;
  requestBusy: boolean;
  actionBusy: string | null;
  selectedExportId: string | null;
  onRequest: () => void;
  onReload: () => void;
  onRetry: () => void;
  onSelectExport: (id: string) => void;
  onRetryDetail: () => void;
  onDownload: (item: ExportItemSummary) => void;
  onCloseDetail: () => void;
};

export function ExportsPresentation({
  exports,
  listReady,
  detail,
  loading,
  stale,
  error,
  detailLoading,
  detailStale,
  detailError,
  requestBusy,
  actionBusy,
  selectedExportId,
  onRequest,
  onReload,
  onRetry,
  onSelectExport,
  onRetryDetail,
  onDownload,
  onCloseDetail,
}: ExportsPresentationProps) {
  const listErrorState: FeedbackState = stale ? "degraded" : "unavailable";
  return (
    <section id="exportacoes" aria-labelledby="exportacoes-title" className="feature-section export-section">
      <div className="feature-heading">
        <div>
          <p className="feature-eyebrow">ZIP assíncrono</p>
          <h2 id="exportacoes-title">Exportações</h2>
          <p className="feature-intro">Solicite e acompanhe somente os estados duráveis retornados pelo servidor.</p>
        </div>
        <div className="feature-actions">
          <Button onClick={onRequest} disabled={requestBusy} aria-busy={requestBusy}>
            {requestBusy ? "Solicitando…" : "Solicitar exportação"}
          </Button>
          <Button variant="secondary" onClick={onReload} disabled={loading} aria-busy={loading}>
            {loading ? "Atualizando…" : "Atualizar exportações"}
          </Button>
        </div>
      </div>
      {loading && <Feedback state="loading" message="Carregando exportações…" />}
      {stale && (
        <div className="feature-stale" role="status" aria-live="polite">
          <Badge variant="warning">Leitura desatualizada</Badge>
          <span>A última leitura segura permanece visível enquanto a atualização é revalidada.</span>
        </div>
      )}
      {error && (
        <div className="export-request-error">
          <Feedback state={listErrorState} message={error} />
          <Button variant="secondary" onClick={onRetry} disabled={loading}>Tentar novamente</Button>
        </div>
      )}
      {listReady && exports.length === 0 && !loading && !error && <Feedback state="empty" message="Nenhuma exportação solicitada." />}
      {exports.length > 0 && (
        <DataTable caption="Exportações solicitadas" className="export-table">
          <thead>
            <tr><th>Solicitada</th><th>Estado</th><th>Metadados</th><th>Expira</th><th>Ações</th></tr>
          </thead>
          <tbody>
            {exports.map((item) => (
              <tr key={item.id} className={selectedExportId === item.id ? "is-selected" : undefined}>
                <td>{dateValue(item.created_at)}</td>
                <td>{stateContext(item)}</td>
                <td>{exportMetrics(item)}</td>
                <td>{dateValue(item.expires_at)}</td>
                <td>
                  <div className="export-actions">
                    <Button
                      variant="secondary"
                      onClick={() => onSelectExport(item.id)}
                      disabled={detailLoading && selectedExportId === item.id}
                      aria-busy={detailLoading && selectedExportId === item.id}
                    >
                      {detailLoading && selectedExportId === item.id ? "Consultando…" : "Detalhes"}
                    </Button>
                    {downloadAction(item, actionBusy, onDownload)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      {selectedExportId && (
        <Panel as="aside" id="export-detail" title="Detalhe da exportação" className="export-detail" aria-live="polite">
          {detailLoading && <Feedback state="loading" message="Consultando o estado durável da exportação…" />}
          {detailStale && (
            <div className="feature-stale" role="status">
              <Badge variant="warning">Detalhe desatualizado</Badge>
              <span>A última leitura segura do detalhe permanece visível.</span>
            </div>
          )}
          {detailError && (
            <div className="export-request-error">
              <Feedback state={detailStale ? "degraded" : "unavailable"} message={detailError} />
              <Button variant="secondary" onClick={onRetryDetail} disabled={detailLoading}>Tentar novamente</Button>
            </div>
          )}
          {detail && (
            <>
              {stateContext(detail)}
              {exportMetrics(detail)}
              <div className="export-detail__context">
                <span><strong>Solicitada:</strong> {dateValue(detail.created_at)}</span>
                <span><strong>Expira:</strong> {dateValue(detail.expires_at)}</span>
                <span>{scopeLabel(detail.filter_snapshot)}</span>
              </div>
              {detail.state === "partial" && <Feedback state="degraded" message="A exportação parcial conserva apenas os itens autorizados e produzidos pelo servidor." />}
              {detail.state === "expired" && <Feedback state="empty" message="O prazo terminou; isso não remove os documentos de origem do acervo." />}
              {downloadAction(detail, actionBusy, onDownload)}
              <Button variant="secondary" onClick={onCloseDetail}>Fechar detalhe</Button>
            </>
          )}
        </Panel>
      )}
    </section>
  );
}

export function ExportsSection({ loadSignal, notify }: ExportsSectionProps) {
  const [exports, setExports] = useState<ExportItemSummary[]>([]);
  const [listReady, setListReady] = useState(false);
  const [detail, setDetail] = useState<ExportDetail | null>(null);
  const [selectedExportId, setSelectedExportId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailStale, setDetailStale] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [requestBusy, setRequestBusy] = useState(false);
  const [detailBusyId, setDetailBusyId] = useState<string | null>(null);
  const [downloadBusyId, setDownloadBusyId] = useState<string | null>(null);
  const listRequestSequence = useRef(0);
  const listPromiseRef = useRef<Promise<boolean> | null>(null);
  const detailRequestSequence = useRef(0);
  const requestBusyRef = useRef(false);
  const detailBusyRef = useRef<string | null>(null);
  const downloadBusyRef = useRef<string | null>(null);
  const hasListResponseRef = useRef(false);
  const detailRef = useRef<ExportDetail | null>(null);
  const idempotencySequence = useRef(0);

  const loadExports = useCallback((force = false): Promise<boolean> => {
    if (!force && listPromiseRef.current) return listPromiseRef.current;
    const sequence = ++listRequestSequence.current;
    const hadResponse = hasListResponseRef.current;
    const request = (async () => {
      setLoading(true);
      setError("");
      if (hadResponse) setStale(true);
      try {
        const result = await listExports();
        if (sequence !== listRequestSequence.current) return false;
        setExports(result.exports);
        hasListResponseRef.current = true;
        setListReady(true);
        setStale(false);
        setError("");
        return true;
      } catch {
        if (sequence !== listRequestSequence.current) return false;
        setListReady(hadResponse);
        setStale(hadResponse);
        setError(hadResponse ? "A atualização das exportações está indisponível." : "As exportações estão indisponíveis.");
        return false;
      } finally {
        if (sequence === listRequestSequence.current) setLoading(false);
      }
    })();
    listPromiseRef.current = request;
    void request.finally(() => {
      if (listPromiseRef.current === request) listPromiseRef.current = null;
    });
    return request;
  }, []);

  useEffect(() => {
    if (loadSignal > 0) void loadExports();
  }, [loadExports, loadSignal]);

  const requestExport = useCallback(async () => {
    if (requestBusyRef.current) return;
    requestBusyRef.current = true;
    setRequestBusy(true);
    const idempotencyKey = `ui-${Date.now()}-${idempotencySequence.current++}`;
    try {
      await createExport({}, idempotencyKey);
      notify("Exportação enfileirada; o estado será confirmado pelo servidor.");
      await loadExports(true);
    } catch {
      notify("Não foi possível solicitar a exportação.");
    } finally {
      requestBusyRef.current = false;
      setRequestBusy(false);
    }
  }, [loadExports, notify]);

  const selectExport = useCallback(async (id: string) => {
    if (detailBusyRef.current === id) return;
    detailBusyRef.current = id;
    const sequence = ++detailRequestSequence.current;
    const retainingDetail = detailRef.current?.id === id;
    setSelectedExportId(id);
    setDetailError("");
    setDetailStale(retainingDetail);
    if (!retainingDetail) {
      detailRef.current = null;
      setDetail(null);
    }
    setDetailBusyId(id);
    setDetailLoading(true);
    try {
      const result = await getExport(id);
      if (sequence !== detailRequestSequence.current) return;
      detailRef.current = result;
      setDetail(result);
      setDetailStale(false);
      setDetailError("");
    } catch {
      if (sequence !== detailRequestSequence.current) return;
      setDetailStale(retainingDetail);
      setDetailError("O detalhe da exportação está indisponível.");
    } finally {
      if (sequence === detailRequestSequence.current) {
        setDetailLoading(false);
        setDetailBusyId(null);
      }
      if (detailBusyRef.current === id) detailBusyRef.current = null;
    }
  }, []);

  const retryDetail = useCallback(() => {
    if (selectedExportId) void selectExport(selectedExportId);
  }, [selectExport, selectedExportId]);

  const handleDownload = useCallback(async (item: ExportItemSummary) => {
    if (!canDownload(item) || !item.download_url || downloadBusyRef.current === item.id) return;
    downloadBusyRef.current = item.id;
    setDownloadBusyId(item.id);
    try {
      await downloadExport(item.download_url);
      notify("Download autorizado solicitado.");
    } catch {
      notify("A exportação não está disponível para download.");
    } finally {
      downloadBusyRef.current = null;
      setDownloadBusyId(null);
    }
  }, [notify]);

  const closeDetail = useCallback(() => {
    ++detailRequestSequence.current;
    detailBusyRef.current = null;
    detailRef.current = null;
    setSelectedExportId(null);
    setDetail(null);
    setDetailError("");
    setDetailStale(false);
    setDetailLoading(false);
    setDetailBusyId(null);
  }, []);

  return (
    <ExportsPresentation
      exports={listReady ? exports : []}
      listReady={listReady}
      detail={detail}
      loading={loading}
      stale={stale}
      error={error}
      detailLoading={detailLoading}
      detailStale={detailStale}
      detailError={detailError}
      requestBusy={requestBusy}
      actionBusy={downloadBusyId ?? detailBusyId}
      selectedExportId={selectedExportId}
      onRequest={() => void requestExport()}
      onReload={() => void loadExports()}
      onRetry={() => void loadExports()}
      onSelectExport={(id) => void selectExport(id)}
      onRetryDetail={retryDetail}
      onDownload={(item) => void handleDownload(item)}
      onCloseDetail={closeDetail}
    />
  );
}
