import { FormEvent, useCallback, useEffect, useState } from "react";
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

export function DocumentsSection({ loadSignal, notify }: DocumentsSectionProps) {
  const [documents, setDocuments] = useState<DocumentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState(() => new URLSearchParams(window.location.search).get("search") ?? "");
  const [family, setFamily] = useState(() => new URLSearchParams(window.location.search).get("family") ?? "");
  const [detail, setDetail] = useState<DocumentDetail | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const query = new URLSearchParams(window.location.search);
      query.delete("cursor");
      if (search) query.set("search", search); else query.delete("search");
      if (family) query.set("family", family); else query.delete("family");
      window.history.replaceState(null, "", `?${query.toString()}`);
      setDocuments(await listDocuments(query));
    } catch {
      setError("Não foi possível consultar os documentos.");
      setDocuments(null);
      notify("Não foi possível consultar os documentos.");
    } finally {
      setLoading(false);
    }
  }, [family, notify, search]);

  useEffect(() => {
    if (loadSignal > 0) void loadDocuments();
  }, [loadDocuments, loadSignal]);

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
        <button type="submit">Consultar</button>
      </form>
      {loading && <p role="status">Carregando documentos…</p>}
      <Feedback message={error} error />
      {!loading && !error && documents && (
        <>
          <p role="status">
            Estado: {documentStatusLabel(documents.status)} · Motivo: {documents.reason_code}
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
