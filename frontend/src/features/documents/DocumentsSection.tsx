import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../../shared/http";
import { Feedback, type FeedbackState } from "../../shared/ui/Feedback";
import { Badge, Button, DataTable, Field, Panel } from "../../shared/ui/primitives";
import { downloadDocument, getDocument, listDocuments, requestPdf } from "./api";
import { DocumentDetail, DocumentItem, DocumentResponse, PdfState } from "./types";

const documentStatusLabels: Record<DocumentResponse["status"], string> = {
  available: "Documentos disponíveis",
  valid_empty: "Consulta válida sem documentos",
  unavailable: "Documentos indisponíveis",
  no_coverage: "Sem cobertura",
  unknown: "Estado não reconhecido",
  partial: "Resultado parcial",
  retry: "Nova tentativa pendente",
  blocked: "Coleta bloqueada",
};

const documentStatusVariants: Record<DocumentResponse["status"], "success" | "warning" | "danger" | "neutral"> = {
  available: "success",
  valid_empty: "neutral",
  unavailable: "danger",
  no_coverage: "warning",
  unknown: "neutral",
  partial: "warning",
  retry: "warning",
  blocked: "danger",
};

const outcomeLabels: Record<DocumentItem["outcome"], string> = {
  persisted: "Persistido",
  quarantine: "Quarentena",
  conflict: "Conflito",
};

const pdfStateLabels: Record<PdfState, string> = {
  available: "Disponível",
  pending: "Em processamento",
  failed: "Falha na geração",
  unsupported: "Não suportado para este documento",
  unavailable: "Indisponível",
};

const reasonLabels: Record<string, string> = {
  documents_available: "A consulta retornou documentos persistidos.",
  query_valid_empty: "A consulta foi aceita, mas não encontrou documentos.",
  source_unavailable: "A fonte de documentos está indisponível.",
  collection_unavailable: "A coleta não está disponível neste momento.",
  coverage_none: "Não há cobertura para este escopo.",
  flow_not_configured: "Este fluxo ainda não possui cobertura configurada.",
  coverage_unknown: "A cobertura deste escopo ainda não foi determinada.",
  collection_unknown: "O estado da coleta não foi determinado.",
  collection_partial: "A consulta contém apenas parte do resultado disponível.",
  collection_retry: "A coleta requer uma nova tentativa.",
  collection_blocked: "A coleta está bloqueada por uma condição do servidor.",
  payload_quarantine: "Há conteúdo aguardando revisão segura.",
  quarantine_review: "Há conteúdo aguardando revisão segura.",
  conflict_review: "Há conteúdo em conflito que não foi tratado como íntegro.",
  content_hash_mismatch: "A evidência não passou na verificação de integridade.",
  not_yet_covered: "A cobertura deste escopo ainda não foi executada.",
};

const pdfErrorLabels: Record<string, string> = {
  renderer_unavailable: "A renderização de PDF está indisponível.",
  render_unavailable: "A renderização de PDF está indisponível.",
  source_xml_invalid: "O documento não pode ser renderizado com a fonte disponível.",
  pdf_size_limit: "O PDF excedeu o limite seguro de tamanho.",
  pdf_integrity_invalid: "O PDF não passou na verificação de integridade.",
  pdf_storage_integrity: "O PDF não passou na verificação de armazenamento.",
};

const documentStateLabels: Record<string, string> = {
  authorized: "Autorizado",
  cancelled: "Cancelado",
  canceled: "Cancelado",
  substituted: "Substituído",
  received: "Recebido",
  pending: "Pendente",
};

const relationshipLabels: Record<string, string> = {
  event: "Evento relacionado",
  substitution: "Substituição",
  cancellation: "Cancelamento",
};

const familyLabels: Record<string, string> = { nfe: "NF-e", nfse: "NFS-e" };
const directionLabels: Record<string, string> = { entrada: "Entrada", saida: "Saída" };
const categoryLabels: Record<string, string> = { tomada: "Tomada", prestada: "Prestada" };

type RequestErrorKind = "unavailable" | "invalid" | "degraded" | "";

export type DocumentLocationFilters = {
  search: string;
  family: string;
  direction: string;
  nfseCategory: string;
  from: string;
  to: string;
};

type DocumentsSectionProps = { loadSignal: number; notify: (message: string) => void };

const controlledFilterKeys = ["search", "family", "direction", "nfse_category", "from", "to"] as const;

function lookupLabel(labels: Record<string, string>, value: string | null | undefined, fallback: string): string {
  if (!value) return fallback;
  return labels[value] ?? fallback;
}

function documentStatusLabel(status: DocumentResponse["status"]): string {
  return documentStatusLabels[status] ?? "Estado não reconhecido";
}

function documentStatusVariant(status: DocumentResponse["status"]): "success" | "warning" | "danger" | "neutral" {
  return documentStatusVariants[status] ?? "neutral";
}

function documentReasonLabel(reasonCode: string | null | undefined): string {
  return (reasonCode && reasonLabels[reasonCode]) || "O servidor informou uma condição que requer atenção.";
}

function documentOutcomeLabel(outcome: DocumentItem["outcome"]): string {
  return outcomeLabels[outcome] ?? "Resultado não reconhecido";
}

function pdfStatusLabel(state: PdfState): string {
  return pdfStateLabels[state] ?? "Estado de PDF não reconhecido";
}

function pdfErrorLabel(error: string | null | undefined): string {
  return (error && pdfErrorLabels[error]) || "A geração do PDF não foi concluída.";
}

function documentStateLabel(state: string): string {
  return documentStateLabels[state] ?? "Estado fiscal não informado";
}

function relationshipLabel(relationship: string): string {
  return relationshipLabels[relationship] ?? "Relação informada pelo servidor";
}

function filtersFromLocation(): DocumentLocationFilters {
  const query = new URLSearchParams(window.location.search);
  return {
    search: query.get("search") ?? "",
    family: query.get("family") ?? "",
    direction: query.get("direction") ?? "",
    nfseCategory: query.get("nfse_category") ?? "",
    from: query.get("from") ?? "",
    to: query.get("to") ?? "",
  };
}

function queryForFilters(filters: DocumentLocationFilters, resetCursor: boolean): URLSearchParams {
  const query = new URLSearchParams(window.location.search);
  for (const key of controlledFilterKeys) query.delete(key);
  if (filters.search) query.set("search", filters.search);
  if (filters.family) query.set("family", filters.family);
  if (filters.direction) query.set("direction", filters.direction);
  if (filters.nfseCategory) query.set("nfse_category", filters.nfseCategory);
  if (filters.from) query.set("from", filters.from);
  if (filters.to) query.set("to", filters.to);
  if (resetCursor) query.delete("cursor");
  return query;
}

function locationUrl(query: URLSearchParams): string {
  const search = query.toString();
  return `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
}

function safeRequestError(kind: RequestErrorKind): { state: FeedbackState; message: string } | null {
  if (kind === "invalid") return { state: "error", message: "O filtro de documentos foi rejeitado pelo servidor." };
  if (kind === "degraded") return { state: "degraded", message: "A consulta de documentos está degradada." };
  if (kind === "unavailable") return { state: "unavailable", message: "Os documentos estão indisponíveis." };
  return null;
}

function filterValueLabel(key: string, value: string): string {
  if (key === "family") return lookupLabel(familyLabels, value, "Família informada");
  if (key === "direction") return lookupLabel(directionLabels, value, "Direção informada");
  if (key === "nfse_category") return lookupLabel(categoryLabels, value, "Categoria informada");
  if (key === "from") return `De ${value}`;
  if (key === "to") return `Até ${value}`;
  if (key === "search") return `Busca: ${value}`;
  if (key === "company_id") return "Empresas selecionadas pelo servidor";
  if (key === "competence_from") return `Competência a partir de ${value}`;
  if (key === "competence_to") return `Competência até ${value}`;
  if (key === "emitted_from") return `Emissão a partir de ${value}`;
  if (key === "emitted_to") return `Emissão até ${value}`;
  if (key === "event_type") return "Tipo de evento informado";
  if (key === "flow") return "Fluxo informado";
  return "Filtro informado";
}

function activeFilterSummary(documents: DocumentResponse, activeQuery: URLSearchParams) {
  const values = new Map<string, string[]>();
  for (const [key, value] of activeQuery.entries()) {
    if (key === "cursor" || key === "limit") continue;
    const current = values.get(key) ?? [];
    current.push(value);
    values.set(key, current);
  }
  if (documents.filter) {
    for (const [key, value] of Object.entries(documents.filter)) {
      if (key === "from" || key === "to" || (value && !values.has(key))) values.set(key, [String(value)]);
    }
  }
  const entries = [...values.entries()].flatMap(([key, entries]) => entries.map((value) => ({ key, value })));
  if (!entries.length) return <p className="document-filters__empty">Nenhum filtro adicional informado.</p>;
  return (
    <ul className="document-filters__summary" aria-label="Filtros ativos">
      {entries.map(({ key, value }, index) => <li key={`${key}-${value}-${index}`}>{filterValueLabel(key, value)}</li>)}
    </ul>
  );
}

function emptyMessage(status: DocumentResponse["status"]): { state: FeedbackState; message: string } {
  if (status === "valid_empty") return { state: "empty", message: "Nenhum documento foi encontrado para os filtros informados." };
  if (status === "no_coverage") return { state: "unavailable", message: "Não há cobertura para este escopo; isso não representa uma consulta vazia." };
  if (status === "partial") return { state: "degraded", message: "O servidor retornou uma leitura parcial sem documentos nesta página." };
  if (status === "retry") return { state: "degraded", message: "A consulta depende de uma nova tentativa da coleta." };
  if (status === "blocked") return { state: "blocked", message: "A coleta está bloqueada; nenhum sucesso foi inferido." };
  if (status === "unavailable") return { state: "unavailable", message: "Os documentos não estão disponíveis para esta consulta." };
  return { state: "error", message: "Nenhum documento pode ser apresentado para o estado informado." };
}

function availabilityLabel(available: boolean, availableLabel: string): string {
  return available ? availableLabel : "Não disponível";
}

export type DocumentPresentationProps = {
  documents: DocumentResponse | null;
  activeQuery: URLSearchParams;
  detail: DocumentDetail | null;
  loading: boolean;
  detailLoading: boolean;
  stale: boolean;
  error: string;
  queryError: RequestErrorKind;
  detailError: string;
  pdfActionError: string;
  selectedDocumentId: string | null;
  pdfBusyId: string | null;
  onRetry: () => void;
  onRetryDetail: () => void;
  onNextPage: (cursor: string) => void;
  onSelectDocument: (id: string) => void;
  onDownload: (path: string, message: string) => void;
  onRequestPdf: (document: DocumentDetail, regenerate: boolean) => void;
  onCloseDetail: () => void;
};

export function DocumentsPresentation({
  documents,
  activeQuery,
  detail,
  loading,
  detailLoading,
  stale,
  error,
  queryError,
  detailError,
  pdfActionError,
  selectedDocumentId,
  pdfBusyId,
  onRetry,
  onRetryDetail,
  onNextPage,
  onSelectDocument,
  onDownload,
  onRequestPdf,
  onCloseDetail,
}: DocumentPresentationProps) {
  const requestError = safeRequestError(queryError);
  const hasError = Boolean(error || requestError);
  return (
    <div className="documents-presentation">
      {loading && <Feedback state="loading" message="Carregando documentos…" />}
      {stale && (
        <div className="document-state document-state--stale" role="status" aria-live="polite">
          <Badge variant="warning">Leitura desatualizada</Badge>
          <p>A última leitura segura permanece visível enquanto esta consulta é atualizada ou revalidada.</p>
        </div>
      )}
      {hasError && (
        <div className="document-request-error">
          <Feedback message={requestError?.message ?? error} state={requestError?.state ?? "error"} />
          <Button variant="secondary" onClick={onRetry}>Tentar novamente</Button>
        </div>
      )}
      {documents && (
        <Panel id="document-results" title="Resultados dos documentos" className="document-results">
          <div className="document-status" role="status" aria-live="polite">
            <Badge variant={documentStatusVariant(documents.status)}>{documentStatusLabel(documents.status)}</Badge>
            <p>{documentReasonLabel(documents.reason_code)}</p>
          </div>
          {activeFilterSummary(documents, activeQuery)}
          {documents.filter && documents.boundary && <p className="document-period">Período retornado pelo servidor: {documents.filter.from} até {documents.filter.to} · fronteira {documents.boundary}</p>}
          <div className="document-pagination" role="status">
            <span>{documents.documents.length} registro(s) nesta página · total informado pelo servidor: {documents.total} · limite: {documents.limit}</span>
            {documents.truncated && <span>Há mais resultados além desta página limitada.</span>}
            {documents.next_cursor && <Button variant="secondary" onClick={() => onNextPage(documents.next_cursor!)}>Próxima página</Button>}
          </div>
          {documents.documents.length === 0 ? (
            <Feedback {...emptyMessage(documents.status)} />
          ) : (
            <DataTable caption="Documentos consultados" className="document-table">
              <thead>
                <tr>
                  <th>Empresa</th><th>Identidade</th><th>Família</th><th>Competência</th>
                  <th>Resultado</th><th>Original/XML</th><th>PDF</th><th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {documents.documents.map((document) => (
                  <tr key={document.id}>
                    <td>{document.company_name}</td>
                    <td>{document.identity}</td>
                    <td>{lookupLabel(familyLabels, document.family, "Família não reconhecida")}</td>
                    <td>{document.competence ?? "Não informado"}</td>
                    <td>
                      <Badge variant={document.outcome === "persisted" ? "success" : document.outcome === "conflict" ? "danger" : "warning"}>{documentOutcomeLabel(document.outcome)}</Badge>
                      {document.reason_code && <small className="document-safe-note">{documentReasonLabel(document.reason_code)}</small>}
                    </td>
                    <td>{availabilityLabel(document.evidence_available, document.xml_available ? "XML disponível" : "Original disponível")}</td>
                    <td>
                      <Badge variant={document.pdf_state === "available" ? "success" : document.pdf_state === "failed" ? "danger" : "warning"}>{pdfStatusLabel(document.pdf_state)}</Badge>
                      {document.pdf_error && <small className="document-safe-note">{pdfErrorLabel(document.pdf_error)}</small>}
                    </td>
                    <td>
                      <div className="document-actions">
                        <Button onClick={() => onSelectDocument(document.id)} aria-label={`Ver detalhe de ${document.identity}`}>Ver detalhe</Button>
                        {document.download_url && document.evidence_available && (
                          <Button variant="secondary" onClick={() => onDownload(document.download_url!, "Download do original indisponível.")}>
                            {document.xml_available ? "Baixar XML" : "Baixar original"}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </Panel>
      )}
      {detailLoading && <Feedback state="loading" message="Carregando detalhe do documento…" />}
      {detailError && (
        <div className="document-request-error">
          <Feedback message={detailError} state="error" />
          <Button variant="secondary" onClick={onRetryDetail}>Tentar detalhe</Button>
        </div>
      )}
      {detail && (
        <Panel as="aside" id="document-detail" title={`Detalhe do documento ${detail.identity.value}`} className="document-detail">
          <p><strong>Identidade:</strong> {detail.identity.value}</p>
          <p><strong>Família:</strong> {lookupLabel(familyLabels, detail.family, "Família não reconhecida")} · <strong>Categoria:</strong> {lookupLabel(categoryLabels, detail.category, "Categoria informada")}</p>
          <p><strong>Estado fiscal:</strong> <Badge variant="neutral">{documentStateLabel(detail.state)}</Badge></p>
          <p><strong>Competência:</strong> {detail.dates.competence} · <strong>Emissão:</strong> {detail.dates.emitted_at}</p>
          <Panel id="document-original" title="XML e original">
            <p><Badge variant={detail.availability.xml ? "success" : "warning"}>{detail.availability.xml ? "XML disponível" : "XML não disponível"}</Badge></p>
            {detail.download_url && detail.availability.original && (
              <Button variant="secondary" onClick={() => onDownload(detail.download_url, "Download do original indisponível.")}>
                {detail.availability.xml ? "Baixar XML" : "Baixar original"}
              </Button>
            )}
          </Panel>
          <Panel id="document-pdf" title="PDF derivado">
            <p><Badge variant={detail.pdf.state === "available" ? "success" : detail.pdf.state === "failed" ? "danger" : "warning"}>{pdfStatusLabel(detail.pdf.state)}</Badge></p>
            {detail.pdf.safe_error && <p className="document-safe-note">{pdfErrorLabel(detail.pdf.safe_error)}</p>}
            {pdfActionError && <Feedback message={pdfActionError} state="error" />}
            {detail.pdf.state === "available" && detail.pdf.download_url && (
              <Button variant="secondary" onClick={() => onDownload(detail.pdf.download_url!, "Download do PDF indisponível.")}>Baixar PDF</Button>
            )}
            {detail.pdf.state === "available" && (
              <Button variant="secondary" blocked={pdfBusyId === detail.id} onClick={() => onRequestPdf(detail, true)}>
                {pdfBusyId === detail.id ? "Regeneração em andamento…" : "Regenerar PDF"}
              </Button>
            )}
            {detail.pdf.state === "pending" && <p>O PDF está em processamento; atualize para observar o estado durável.</p>}
            {detail.pdf.state === "failed" && (
              <Button blocked={pdfBusyId === detail.id} onClick={() => onRequestPdf(detail, true)}>
                {pdfBusyId === detail.id ? "Regeneração em andamento…" : "Regenerar PDF"}
              </Button>
            )}
            {detail.pdf.state === "unavailable" && (
              <Button blocked={pdfBusyId === detail.id} onClick={() => onRequestPdf(detail, false)}>
                {pdfBusyId === detail.id ? "Solicitação em andamento…" : "Solicitar PDF"}
              </Button>
            )}
            {detail.pdf.state === "unsupported" && <p>Não há ação de renderização para este documento.</p>}
          </Panel>
          <Panel id="document-events" title="Eventos e substituições">
            {detail.events.length === 0 ? <p>Nenhum evento relacionado foi retornado.</p> : (
              <ul className="document-events">
                {detail.events.map((event) => (
                  <li key={event.id}>
                    <Badge variant="neutral">{relationshipLabel(event.relationship_type)}</Badge>
                    <span>{event.identity} · {event.occurred_at} · {documentStateLabel(event.state)}</span>
                  </li>
                ))}
              </ul>
            )}
            <p>Artefatos retornados: {detail.artifacts.length} · eventos relacionados: {detail.events.length}</p>
          </Panel>
          <Button variant="secondary" onClick={onCloseDetail}>Fechar detalhe</Button>
        </Panel>
      )}
      {selectedDocumentId && !detail && !detailLoading && !detailError && <p role="status">Selecione um documento para consultar o detalhe.</p>}
    </div>
  );
}

function initialFilters(): DocumentLocationFilters {
  return filtersFromLocation();
}

export function DocumentsSection({ loadSignal, notify }: DocumentsSectionProps) {
  const initial = initialFilters();
  const [filters, setFilters] = useState(initial);
  const filtersRef = useRef(initial);
  const [activeQuery, setActiveQuery] = useState(() => new URLSearchParams(window.location.search));
  const [documents, setDocuments] = useState<DocumentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [queryError, setQueryError] = useState<RequestErrorKind>("");
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [pdfActionError, setPdfActionError] = useState("");
  const [pdfBusyId, setPdfBusyId] = useState<string | null>(null);
  const selectedDocumentRef = useRef<string | null>(null);
  const pdfOperation = useRef(0);
  const listSequence = useRef(0);
  const listInFlight = useRef<string | null>(null);
  const detailSequence = useRef(0);
  const detailInFlight = useRef<string | null>(null);

  const syncFilters = useCallback((next: DocumentLocationFilters) => {
    filtersRef.current = next;
    setFilters(next);
  }, []);

  const loadDocuments = useCallback(async (query: URLSearchParams) => {
    const requestKey = query.toString();
    if (listInFlight.current === requestKey) return;
    listInFlight.current = requestKey;
    const sequence = listSequence.current + 1;
    listSequence.current = sequence;
    setActiveQuery(new URLSearchParams(query));
    setLoading(true);
    setError("");
    setQueryError("");
    try {
      const response = await listDocuments(new URLSearchParams(query));
      if (sequence !== listSequence.current) return;
      setDocuments(response);
    } catch (caught: unknown) {
      if (sequence !== listSequence.current) return;
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
      setError("Não foi possível consultar os documentos.");
      notify("Não foi possível consultar os documentos.");
    } finally {
      if (sequence === listSequence.current) setLoading(false);
      if (listInFlight.current === requestKey) listInFlight.current = null;
    }
  }, [notify]);

  const loadCurrentLocation = useCallback(() => {
    const next = filtersFromLocation();
    syncFilters(next);
    void loadDocuments(queryForFilters(next, false));
  }, [loadDocuments, syncFilters]);

  useEffect(() => {
    if (loadSignal > 0 || window.location.hash === "#documentos") loadCurrentLocation();
  }, [loadCurrentLocation, loadSignal]);

  useEffect(() => {
    const loadLocation = () => {
      if (window.location.hash !== "#documentos") return;
      setDetail(null);
      setSelectedDocumentId(null);
      selectedDocumentRef.current = null;
      setDetailError("");
      loadCurrentLocation();
    };
    window.addEventListener("hashchange", loadLocation);
    window.addEventListener("popstate", loadLocation);
    return () => {
      window.removeEventListener("hashchange", loadLocation);
      window.removeEventListener("popstate", loadLocation);
    };
  }, [loadCurrentLocation]);

  const retry = useCallback(() => {
    void loadDocuments(new URLSearchParams(window.location.search));
  }, [loadDocuments]);

  const submit = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = queryForFilters(filtersRef.current, true);
    window.history.replaceState(null, "", locationUrl(query));
    setDetail(null);
    setSelectedDocumentId(null);
    selectedDocumentRef.current = null;
    setDetailError("");
    await loadDocuments(query);
  }, [loadDocuments]);

  const nextPage = useCallback((cursor: string) => {
    const query = new URLSearchParams(window.location.search);
    query.set("cursor", cursor);
    window.history.pushState(null, "", locationUrl(query));
    setDetail(null);
    setSelectedDocumentId(null);
    selectedDocumentRef.current = null;
    setDetailError("");
    void loadDocuments(query);
  }, [loadDocuments]);

  const showDetail = useCallback(async (id: string) => {
    if (detailInFlight.current === id) return;
    detailInFlight.current = id;
    const sequence = detailSequence.current + 1;
    detailSequence.current = sequence;
    setSelectedDocumentId(id);
    selectedDocumentRef.current = id;
    setDetail(null);
    setDetailError("");
    setPdfActionError("");
    setDetailLoading(true);
    try {
      const response = await getDocument(id);
      if (sequence !== detailSequence.current) return;
      setDetail(response);
    } catch {
      if (sequence !== detailSequence.current) return;
      setDetailError("Não foi possível consultar o detalhe do documento.");
      notify("Não foi possível consultar o detalhe do documento.");
    } finally {
      if (sequence === detailSequence.current) setDetailLoading(false);
      if (detailInFlight.current === id) detailInFlight.current = null;
    }
  }, [notify]);

  const retryDetail = useCallback(() => {
    if (selectedDocumentRef.current) void showDetail(selectedDocumentRef.current);
  }, [showDetail]);

  const generatePdf = useCallback(async (document: DocumentDetail, regenerate: boolean) => {
    if (pdfBusyId === document.id) return;
    const operation = pdfOperation.current + 1;
    pdfOperation.current = operation;
    setPdfBusyId(document.id);
    setPdfActionError("");
    try {
      await requestPdf(document.pdf.request_url, regenerate);
      notify(regenerate ? "Regeneração do PDF enfileirada." : "Geração do PDF enfileirada.");
      await loadDocuments(new URLSearchParams(window.location.search));
      const refreshed = await getDocument(document.id);
      if (operation === pdfOperation.current && selectedDocumentRef.current === document.id) setDetail(refreshed);
    } catch {
      setPdfActionError("Não foi possível solicitar o PDF. O XML/original permanece independente desta falha.");
      notify("Não foi possível solicitar o PDF.");
    } finally {
      if (operation === pdfOperation.current) setPdfBusyId(null);
    }
  }, [loadDocuments, notify, pdfBusyId]);

  const download = useCallback(async (path: string, message: string) => {
    try {
      await downloadDocument(path);
    } catch {
      notify(message);
    }
  }, [notify]);

  const updateFilter = useCallback((key: keyof DocumentLocationFilters, value: string) => {
    const next = { ...filtersRef.current, [key]: value };
    filtersRef.current = next;
    setFilters(next);
  }, []);

  const isKnownFamily = familyLabels[filters.family] !== undefined;
  const isKnownDirection = directionLabels[filters.direction] !== undefined;
  const isKnownCategory = categoryLabels[filters.nfseCategory] !== undefined;

  return (
    <section id="documentos" aria-labelledby="documentos-title">
      <h2 id="documentos-title">Documentos</h2>
      <p>Consulta somente leitura. Datas do dashboard usam a fronteira civil [from,to); a autorização e os dados permanecem no servidor.</p>
      <div className="document-toolbar">
        <form className="document-filter-form" onSubmit={(event) => void submit(event)}>
          <Field id="documents-from" label="De"><input type="date" value={filters.from} onChange={(event) => updateFilter("from", event.target.value)} /></Field>
          <Field id="documents-to" label="Até"><input type="date" value={filters.to} onChange={(event) => updateFilter("to", event.target.value)} /></Field>
          <Field id="documents-search" label="Busca global"><input value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} /></Field>
          <Field id="documents-family" label="Família">
            <select value={filters.family} onChange={(event) => updateFilter("family", event.target.value)}>
              <option value="">Todas</option><option value="nfe">NF-e</option><option value="nfse">NFS-e</option>
              {filters.family && !isKnownFamily && <option value={filters.family}>Valor informado; validação no servidor</option>}
            </select>
          </Field>
          <Field id="documents-direction" label="Direção NF-e">
            <select value={filters.direction} onChange={(event) => updateFilter("direction", event.target.value)}>
              <option value="">Todas</option><option value="entrada">Entrada</option><option value="saida">Saída</option>
              {filters.direction && !isKnownDirection && <option value={filters.direction}>Valor informado; validação no servidor</option>}
            </select>
          </Field>
          <Field id="documents-nfse-category" label="Categoria NFS-e">
            <select value={filters.nfseCategory} onChange={(event) => updateFilter("nfseCategory", event.target.value)}>
              <option value="">Todas</option><option value="tomada">Tomada</option><option value="prestada">Prestada</option>
              {filters.nfseCategory && !isKnownCategory && <option value={filters.nfseCategory}>Valor informado; validação no servidor</option>}
            </select>
          </Field>
          <Button type="submit">Consultar</Button>
        </form>
        <Button variant="secondary" onClick={() => void loadDocuments(new URLSearchParams(window.location.search))}>Atualizar documentos</Button>
      </div>
      <DocumentsPresentation
        documents={documents}
        activeQuery={activeQuery}
        detail={detail}
        loading={loading}
        detailLoading={detailLoading}
        stale={documents !== null && (loading || Boolean(error))}
        error={error}
        queryError={queryError}
        detailError={detailError}
        pdfActionError={pdfActionError}
        selectedDocumentId={selectedDocumentId}
        pdfBusyId={pdfBusyId}
        onRetry={retry}
        onRetryDetail={retryDetail}
        onNextPage={nextPage}
        onSelectDocument={(id) => void showDetail(id)}
        onDownload={(path, message) => void download(path, message)}
        onRequestPdf={(document, regenerate) => void generatePdf(document, regenerate)}
        onCloseDetail={() => { setDetail(null); setSelectedDocumentId(null); selectedDocumentRef.current = null; setPdfActionError(""); }}
      />
    </section>
  );
}
