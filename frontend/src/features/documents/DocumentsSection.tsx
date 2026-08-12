import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
import { downloadDocument, getDocument, listDocuments, requestPdf } from "./api";
import { DocumentDetail, DocumentItem, DocumentResponse, PdfState } from "./types";

function documentStatusLabel(status: DocumentResponse["status"]): string {
  return (
    {
      available: "Documentos disponíveis",
      valid_empty: "Consulta válida sem documentos",
      unavailable: "Documentos indisponíveis",
      no_coverage: "Sem cobertura",
      unknown: "Estado desconhecido",
      partial: "Resultado parcial",
      retry: "Retry pendente",
      blocked: "Coleta bloqueada",
    }[status] ?? "Estado desconhecido"
  );
}

function documentOutcomeLabel(outcome: DocumentItem["outcome"]): string {
  return { persisted: "Persistido", quarantine: "Quarentena", conflict: "Conflito" }[
    outcome
  ];
}

function pdfStatusLabel(state: PdfState): string {
  return {
    available: "Disponível",
    pending: "Pendente",
    failed: "Falhou",
    unsupported: "Não suportado",
    unavailable: "Indisponível",
  }[state];
}

type DocumentsSectionProps = { loadSignal: number; notify: (message: string) => void };

type DocumentLocationFilters = {
  search: string;
  family: string;
  direction: string;
  nfseCategory: string;
  from: string;
  to: string;
};

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

function hasDocumentDrilldownLocation(): boolean {
  const query = new URLSearchParams(window.location.search);
  return query.has("from") || query.has("to");
}

export function DocumentsSection({ loadSignal, notify }: DocumentsSectionProps) {
  const [documents, setDocuments] = useState<DocumentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState(() => new URLSearchParams(window.location.search).get("search") ?? "");
  const [family, setFamily] = useState(() => new URLSearchParams(window.location.search).get("family") ?? "");
  const [direction, setDirection] = useState(() => new URLSearchParams(window.location.search).get("direction") ?? "");
  const [nfseCategory, setNfseCategory] = useState(() => new URLSearchParams(window.location.search).get("nfse_category") ?? "");
  const [from, setFrom] = useState(() => new URLSearchParams(window.location.search).get("from") ?? "");
  const [to, setTo] = useState(() => new URLSearchParams(window.location.search).get("to") ?? "");
  const [queryError, setQueryError] = useState<"unavailable" | "invalid" | "degraded" | "">("");
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const loadDocumentsRef = useRef<((locationFilters?: DocumentLocationFilters) => Promise<void>) | null>(null);

  const loadDocuments = useCallback(async (locationFilters?: DocumentLocationFilters) => {
    const active = locationFilters ?? { search, family, direction, nfseCategory, from, to };
    if (locationFilters) {
      setSearch(active.search);
      setFamily(active.family);
      setDirection(active.direction);
      setNfseCategory(active.nfseCategory);
      setFrom(active.from);
      setTo(active.to);
    }
    setLoading(true);
    setError("");
    setQueryError("");
    try {
      const query = new URLSearchParams(window.location.search);
      query.delete("cursor");
      query.delete("from");
      query.delete("to");
      query.delete("direction");
      query.delete("nfse_category");
      query.delete("search");
      query.delete("family");
      if (active.search) query.set("search", active.search);
      if (active.family) query.set("family", active.family);
      if (active.direction) query.set("direction", active.direction);
      if (active.nfseCategory) query.set("nfse_category", active.nfseCategory);
      if (active.from) query.set("from", active.from);
      if (active.to) query.set("to", active.to);
      window.history.replaceState(null, "", `?${query.toString()}`);
      setDocuments(await listDocuments(query));
    } catch (caught: unknown) {
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
      setError("Não foi possível consultar os documentos.");
      setDocuments(null);
      notify("Não foi possível consultar os documentos.");
    } finally {
      setLoading(false);
    }
  }, [direction, family, from, nfseCategory, notify, search, to]);

  useEffect(() => {
    loadDocumentsRef.current = loadDocuments;
  }, [loadDocuments]);

  useEffect(() => {
    if (loadSignal > 0) void loadDocuments();
  }, [loadDocuments, loadSignal]);

  useEffect(() => {
    const loadLocation = () => {
      if (hasDocumentDrilldownLocation()) {
        void loadDocumentsRef.current?.(filtersFromLocation());
      }
    };
    window.addEventListener("hashchange", loadLocation);
    loadLocation();
    return () => window.removeEventListener("hashchange", loadLocation);
  }, []);

  async function showDetail(id: string) {
    try {
      setDetail(await getDocument(id));
    } catch {
      notify("Não foi possível consultar o detalhe do documento.");
    }
  }

  async function generatePdf(id: string, regenerate = false) {
    try {
      await requestPdf(id, regenerate);
      notify(regenerate ? "Regeneração do PDF enfileirada." : "Geração do PDF enfileirada.");
      await loadDocuments();
      if (detail?.id === id) await showDetail(id);
    } catch {
      notify("Não foi possível solicitar o PDF.");
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    await loadDocuments();
  }

  return (
    <section id="documentos">
      <h2>Documentos</h2>
      <button onClick={() => void loadDocuments()}>Atualizar documentos</button>
      <form onSubmit={(event) => void submit(event)}>
        <label>
          De <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
        </label>
        <label>
          Até <input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
        </label>
        <label>
          Busca global <input value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <label>
          Família
          <select value={family} onChange={(event) => setFamily(event.target.value)}>
            <option value="">Todas</option>
            <option value="nfe">NF-e</option>
            <option value="nfse">NFS-e</option>
          </select>
        </label>
        <label>
          Direção NF-e
          <select value={direction} onChange={(event) => setDirection(event.target.value)}>
            <option value="">Todas</option>
            <option value="entrada">Entrada</option>
            <option value="saida">Saída</option>
          </select>
        </label>
        <label>
          Categoria NFS-e
          <select value={nfseCategory} onChange={(event) => setNfseCategory(event.target.value)}>
            <option value="">Todas</option>
            <option value="tomada">Tomada</option>
            <option value="prestada">Prestada</option>
          </select>
        </label>
        <button type="submit">Consultar</button>
      </form>
      {loading && <p role="status">Carregando documentos…</p>}
      <Feedback message={error} state="error" />
      {queryError === "invalid" && <p role="status">O filtro de documentos é inválido.</p>}
      {queryError === "unavailable" && <p role="status">Os documentos estão indisponíveis.</p>}
      {queryError === "degraded" && <p role="status">A consulta de documentos está degradada.</p>}
      {!loading && !error && documents && (
        <>
          <p role="status">
            Estado: {documentStatusLabel(documents.status)} · Motivo: {documents.reason_code}
          </p>
          {documents.filter && (
            <p>
              Período: {documents.filter.from} até {documents.filter.to} · limite {documents.boundary}
              {documents.filter.family ? ` · família ${documents.filter.family}` : ""}
              {documents.filter.direction ? ` · direção ${documents.filter.direction}` : ""}
              {documents.filter.nfse_category ? ` · categoria ${documents.filter.nfse_category}` : ""}
            </p>
          )}
          <p role="status">
            Total de documentos persistidos: {documents.total}
            {documents.truncated ? " (mostrando somente a primeira página limitada)" : ""}
          </p>
          {documents.documents.length === 0 ? (
            <p>
              {documents.status === "valid_empty"
                ? "Nenhum documento encontrado."
                : "Nenhum documento disponível para este estado."}
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Empresa</th><th>Identidade</th><th>Família</th>
                  <th>Competência</th><th>Resultado</th><th>Evidência</th><th>PDF</th><th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {documents.documents.map((document) => (
                  <tr key={document.id}>
                    <td>{document.company_name}</td>
                    <td>{document.identity}</td>
                    <td>{document.family}</td>
                    <td>{document.competence ?? "—"}</td>
                    <td>
                      {documentOutcomeLabel(document.outcome)}
                      {document.reason_code ? ` · ${document.reason_code}` : ""}
                    </td>
                    <td>{document.evidence_available ? "Disponível" : "Não disponível"}</td>
                    <td>
                      {pdfStatusLabel(document.pdf_state)}
                      {document.pdf_error ? ` · ${document.pdf_error}` : ""}
                    </td>
                    <td>
                      <button onClick={() => void showDetail(document.id)}>Detalhes</button>
                      {document.download_url && document.evidence_available && (
                        <button
                          onClick={() => void downloadDocument(document.download_url!).catch(() => notify("Download indisponível."))}
                        >
                          Baixar original
                        </button>
                      )}
                      {document.pdf_available && (
                        <button
                          onClick={() =>
                            void downloadDocument(`/api/documents/${document.id}/pdf`).catch(() =>
                              notify("Download de PDF indisponível."),
                            )
                          }
                        >
                          Baixar PDF
                        </button>
                      )}
                      {!document.pdf_available && document.pdf_state !== "unsupported" && (
                        <button onClick={() => void generatePdf(document.id)}>
                          {document.pdf_state === "failed" ? "Tentar PDF" : "Gerar PDF"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {detail && (
            <aside aria-label="Detalhe do documento">
              <h3>Detalhe do documento</h3>
              <p>{detail.identity.value} · {detail.family} · competência {detail.dates.competence}</p>
              <p>
                XML: {detail.availability.xml ? "Disponível" : "Não disponível"} · PDF: {pdfStatusLabel(detail.pdf.state)}
              </p>
              {detail.pdf.download_url && (
                <button
                  onClick={() =>
                    void downloadDocument(detail.pdf.download_url!).catch(() =>
                      notify("Download de PDF indisponível."),
                    )
                  }
                >
                  Baixar PDF
                </button>
              )}
              {detail.pdf.state !== "available" && detail.pdf.state !== "unsupported" && (
                <button onClick={() => void generatePdf(detail.id, detail.pdf.state === "failed")}>
                  {detail.pdf.state === "failed" ? "Regenerar PDF" : "Gerar PDF"}
                </button>
              )}
              <p>Eventos relacionados: {detail.events.length}</p>
              <button onClick={() => setDetail(null)}>Fechar detalhe</button>
            </aside>
          )}
        </>
      )}
    </section>
  );
}
