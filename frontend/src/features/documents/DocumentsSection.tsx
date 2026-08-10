import { useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { listDocuments } from "./api";
import { DocumentItem, DocumentResponse } from "./types";

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

type DocumentsSectionProps = { loadSignal: number; notify: (message: string) => void };

export function DocumentsSection({ loadSignal, notify }: DocumentsSectionProps) {
  const [documents, setDocuments] = useState<DocumentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDocuments(await listDocuments());
    } catch {
      setError("Não foi possível consultar os documentos.");
      setDocuments(null);
      notify("Não foi possível consultar os documentos.");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0) void loadDocuments();
  }, [loadDocuments, loadSignal]);

  return (
    <section id="documentos">
      <h2>Documentos</h2>
      <button onClick={() => void loadDocuments()}>Atualizar documentos</button>
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
                  <th>Competência</th><th>Resultado</th><th>Evidência</th>
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
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}
