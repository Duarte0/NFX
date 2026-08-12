import { createRoot } from "react-dom/client";
import { useState, type FormEvent } from "react";
import { CompaniesPresentation } from "../src/features/companies/CompaniesSection";
import { CertificateInventoryPresentation } from "../src/features/certificates/CertificateInventoryPanel";
import { CollectionsPresentation } from "../src/features/collections/CollectionsSection";
import "../src/shared/ui/tokens.css";

const params = new URLSearchParams(window.location.search);
const role = params.get("role") ?? "visualizador";
const session = params.get("session") ?? "authenticated";

const company = {
  id: "company-browser-1",
  cnpj: "00000000000000",
  legal_name: "Empresa sintética",
  status: "ativa" as const,
  first_collection_at: null,
  deactivation_reason: null,
  version: 2,
  flows: {
    nfe: { id: "flow-browser-nfe", state: "habilitado" as const },
    nfse: { id: "flow-browser-nfse", state: "pausado" as const },
  },
  enrichment: { status: "sucesso", public_non_authoritative: true, payload: {}, error_code: "" },
};

const companyResult = {
  companies: [company],
  filter: { lifecycle: "active" as const },
  total: 2,
  limit: 1,
  truncated: true,
  next_cursor: "opaque.browser.company.cursor",
};

const inventoryResult = {
  certificates: [{
    id: "certificate-browser-1",
    company: { id: company.id, cnpj: company.cnpj, legal_name: company.legal_name },
    state: "current",
    status: "proximo_vencimento",
    not_before: "2026-01-01T00:00:00+00:00",
    not_after: "2026-08-20T00:00:00+00:00",
    days_until_expiry: 8,
  }],
  filter: { filter: "expiring" as const },
  evaluated_at: "2026-08-12T12:00:00+00:00",
  freshness: { status: "stale" as const, evaluated_at: "2026-08-12T11:00:00+00:00", age_seconds: 3600 },
  total: 3,
  limit: 1,
  truncated: true,
  next_cursor: "opaque.browser.certificate.cursor",
};

const flow = (family: "nfe" | "nfse", state: string, coverage: object | null) => ({
  family,
  flow_state: "habilitado",
  collection_state: state,
  last_attempt_at: "2026-08-12T10:00:00+00:00",
  last_success_at: null,
  next_scheduled_at: null,
  cooldown_until: null,
  blocked_reason: state === "blocked" ? "permanent_failure" : "",
  safe_error: state === "failed" ? "temporary_failure" : "",
  progress: { current: 2, total: 4 },
  coverage,
  active_execution: null,
  latest_execution: { id: `execution-browser-${family}-${state}`, state, safe_error: state === "partial" ? "partial_result" : "", origin: "manual" },
});

const collectionCompany = {
  company_id: company.id,
  legal_name: company.legal_name,
  status: company.status,
  flows: [
    flow("nfe", "running", null),
    flow("nfse", "blocked", { status: "none", source: "synthetic", verified_at: "2026-08-12T10:00:00+00:00", policy_version: "synthetic-policy" }),
    flow("nfse", "partial", { status: "unknown", source: "synthetic", verified_at: "2026-08-12T10:00:00+00:00", policy_version: "synthetic-policy" }),
    flow("nfse", "failed", { status: "error", source: "synthetic", verified_at: "2026-08-12T10:00:00+00:00", policy_version: "synthetic-policy" }),
  ],
};

const executionResult = {
  read_only: true as const,
  filter: { from: "2026-08-01", to: "2026-09-01", state: "partial" },
  boundary: "[from,to)" as const,
  total: 4,
  limit: 100,
  truncated: false,
  executions: [{
    id: "execution-browser-1",
    company_id: company.id,
    company_name: company.legal_name,
    family: "nfse",
    requested_scope: "nfse",
    state: "partial",
    outcome: "partial",
    recovery: "retry",
    safe_error: "partial_result",
    created_at: "2026-08-12T10:00:00+00:00",
    started_at: null,
    finished_at: null,
  }],
};

function noOpSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
}

function CompaniesFixture() {
  const [notice, setNotice] = useState("");
  const canManage = role !== "visualizador";
  if (session !== "authenticated") {
    return <main lang="pt-BR"><h1>Empresas sintéticas</h1><p role="alert">Acesse sua conta.</p></main>;
  }

  return (
    <main lang="pt-BR">
      <h1>Empresas, certificados e coletas sintéticas</h1>
      <p>Perfil sintético: {role}</p>
      {notice && <p role="status">{notice}</p>}
      {canManage && (
        <CompaniesPresentation
          companies={companyResult.companies}
          companyResult={companyResult}
          selectedCompany={company}
          loading={false}
          stale={false}
          error=""
          queryError=""
          actionBusy=""
          newCompany={{ cnpj: "", legal_name: "" }}
          editCompany={{ cnpj: company.cnpj, legal_name: company.legal_name }}
          onReload={() => setNotice("Atualização solicitada.")}
          onRetry={() => setNotice("Nova tentativa solicitada.")}
          onFilterChange={() => setNotice("Filtros preservados.")}
          onNextPage={() => setNotice("Cursor opaco preservado sem ser exibido.")}
          onCreate={noOpSubmit}
          onEdit={noOpSubmit}
          onSelect={() => setNotice("Empresa selecionada com teclado ou ponteiro.")}
          onCompanyAction={() => setNotice("Ação crítica aguardando confirmação do owner.")}
          onToggleFlow={() => setNotice("Alteração de fluxo enviada ao owner.")}
          onEnrich={() => setNotice("Enriquecimento público solicitado.")}
          onNewCompanyChange={() => undefined}
          onEditCompanyChange={() => undefined}
          onCertificateChanged={async () => undefined}
          onCertificateNotify={setNotice}
          children={(
            <section id="certificados" aria-labelledby="browser-certificates-title">
              <h2 id="browser-certificates-title">Certificados</h2>
              <CertificateInventoryPresentation
                filter="expiring"
                cursor="opaque.browser.certificate.cursor"
                result={inventoryResult}
                loading={false}
                stale
                error=""
                queryError=""
                onFilterChange={() => setNotice("Filtro de certificado preservado.")}
                onReload={() => setNotice("Inventário atualizado.")}
                onRetry={() => setNotice("Nova tentativa do inventário solicitada.")}
                onNextPage={() => setNotice("Cursor opaco preservado sem ser exibido.")}
              />
            </section>
          )}
        />
      )}
      <CollectionsPresentation
        companies={[collectionCompany]}
        executionResult={executionResult}
        executionFilter={executionResult.filter}
        executionLoading={false}
        executionStale
        collectionStale={false}
        error=""
        executionError=""
        canManage={canManage}
        actionBusy=""
        onReload={() => setNotice("Coletas atualizadas.")}
        onRetry={() => setNotice("Nova tentativa das coletas solicitada.")}
        onFilterChange={() => setNotice("Filtro de execução preservado.")}
        onRequest={() => setNotice("Solicitação de coleta enviada ao owner.")}
        onRetryCollection={() => setNotice("Retry de coleta enviado ao owner.")}
      />
    </main>
  );
}

window.fetch = async () => { throw new Error("Browser fixture does not permit network requests"); };
createRoot(document.getElementById("root")!).render(<CompaniesFixture />);
