import { createRoot } from "react-dom/client";
import { useState } from "react";
import { DocumentsPresentation } from "../src/features/documents/DocumentsSection";
import type { DocumentDetail, DocumentResponse } from "../src/features/documents/types";
import "../src/shared/ui/tokens.css";

const params = new URLSearchParams(window.location.search);
const role = params.get("role") ?? "visualizador";
const session = params.get("session") ?? "authenticated";

const documentResponse: DocumentResponse = {
  status: "available",
  reason_code: "documents_available",
  documents: [{
    id: "document-synthetic-1",
    company_id: "company-synthetic-1",
    company_name: "Empresa sintética",
    family: "nfe",
    role: "entrada",
    category: "document",
    source: "simulator",
    flow: "distribution",
    identity: "doc-synthetic-1",
    identity_kind: "synthetic",
    emitted_at: "2026-08-12T10:00:00+00:00",
    authorized_at: "2026-08-12T10:01:00+00:00",
    competence: "2026-08-01",
    situation: "authorized",
    outcome: "persisted",
    evidence_available: true,
    xml_available: true,
    pdf_available: true,
    pdf_state: "available",
    pdf_error: null,
    detail_url: "/api/documents/document-synthetic-1",
    download_url: "/api/documents/document-synthetic-1/download",
    reason_code: null,
  }],
  collection_states: [{ company_id: "company-synthetic-1", family: "nfe", flow: "distribution", status: "available", reason_code: "documents_available" }],
  total: 3,
  limit: 1,
  truncated: true,
  filter: { from: "2026-08-01", to: "2026-09-01", family: "nfe", direction: "entrada" },
  boundary: "[from,to)",
  next_cursor: "opaque.synthetic.cursor",
};

const documentDetail: DocumentDetail = {
  id: "document-synthetic-1",
  company: { id: "company-synthetic-1", name: "Empresa sintética" },
  family: "nfe",
  role: "entrada",
  category: "document",
  source: "simulator",
  flow: "distribution",
  identity: { kind: "synthetic", value: "doc-synthetic-1" },
  dates: { emitted_at: "2026-08-12T10:00:00+00:00", authorized_at: "2026-08-12T10:01:00+00:00", competence: "2026-08-01" },
  situation: "authorized",
  state: "authorized",
  collection: { origin_execution_ref: "execution-synthetic-1" },
  parties: { issuer: null, recipient: null, provider: null },
  value_total: null,
  artifacts: [{ id: "artifact-synthetic-1", digest_prefix: "redacted", size_bytes: 12, content_type: "application/xml", availability: "available" }],
  events: [],
  availability: { xml: true, original: true, pdf: true },
  pdf: { id: "render-synthetic-1", state: "available", safe_error: null, renderer_id: "redacted", renderer_version: "redacted", representation: "danfe", pdf_type: "danfe", digest_prefix: "redacted", size_bytes: 20, content_type: "application/pdf", request_url: "/api/documents/document-synthetic-1/pdf/render", download_url: "/api/documents/document-synthetic-1/pdf" },
  download_url: "/api/documents/document-synthetic-1/download",
};

function DocumentsFixture() {
  const [notice, setNotice] = useState("");
  const [cursorUsed, setCursorUsed] = useState(false);
  const [detail, setDetail] = useState<DocumentDetail | null>(documentDetail);

  if (session !== "authenticated") {
    return (
      <main lang="pt-BR">
        <h1>Documentos sintéticos</h1>
        <p role="alert">Acesse sua conta.</p>
      </main>
    );
  }

  return (
    <main lang="pt-BR">
      <h1>Documentos sintéticos</h1>
      <p>Perfil sintético: {role}</p>
      {notice && <p role="status">{notice}</p>}
      <DocumentsPresentation
        documents={documentResponse}
        activeQuery={new URLSearchParams("from=2026-08-01&to=2026-09-01&family=nfe&direction=entrada")}
        detail={detail}
        loading={false}
        detailLoading={false}
        stale={false}
        error=""
        queryError=""
        detailError=""
        pdfActionError=""
        selectedDocumentId={detail?.id ?? null}
        pdfBusyId={null}
        onRetry={() => setNotice("Nova tentativa solicitada.")}
        onRetryDetail={() => setNotice("Nova tentativa do detalhe solicitada.")}
        onNextPage={(cursor) => {
          setCursorUsed(true);
          setNotice(cursor ? "Cursor opaco devolvido pelo servidor preservado." : "");
        }}
        onSelectDocument={(id) => setNotice(`Detalhe selecionado: ${id}`)}
        onDownload={(path) => setNotice(path.includes("/api/") ? "Download autorizado solicitado." : "Download indisponível.")}
        onRequestPdf={() => setNotice("Regeneração solicitada ao servidor.")}
        onCloseDetail={() => setDetail(null)}
      />
      {cursorUsed && <p data-testid="cursor-preserved">A próxima página mantém os filtros ativos.</p>}
    </main>
  );
}

window.fetch = async () => {
  throw new Error("Browser fixture does not permit network requests");
};

createRoot(document.getElementById("root")!).render(<DocumentsFixture />);
