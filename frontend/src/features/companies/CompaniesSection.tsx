import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
import { CertificateInventoryPanel } from "../certificates/CertificateInventoryPanel";
import { CertificatePanel } from "../certificates/CertificatePanel";
import {
  changeCompanyState,
  changeFlow,
  createCompany as createCompanyApi,
  enrichCompany as enrichCompanyApi,
  listCompanies,
  updateCompany as updateCompanyApi,
} from "./api";
import { Company, CompanyListResponse } from "./types";

function statusLabel(status: Company["status"]): string {
  return { cadastrada: "Cadastrada", ativa: "Ativa", desativada: "Desativada" }[status];
}

type CompaniesSectionProps = {
  loadSignal: number;
  notify: (message: string) => void;
};

type CompanyLocationFilter = { lifecycle: string } | null;

function companyFilterFromLocation(): CompanyLocationFilter {
  const query = new URLSearchParams(window.location.search);
  if (!query.has("lifecycle")) return null;
  return { lifecycle: query.get("lifecycle") ?? "" };
}

function lifecycleFilterLabel(lifecycle: string): string {
  return { active: "Empresas ativas", inactive: "Empresas inativas" }[lifecycle] ?? lifecycle;
}

export function CompaniesSection({ loadSignal, notify }: CompaniesSectionProps) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyResult, setCompanyResult] = useState<CompanyListResponse | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [queryError, setQueryError] = useState<"unavailable" | "invalid" | "degraded" | "">("");
  const [newCompany, setNewCompany] = useState({ cnpj: "", legal_name: "" });
  const [editCompany, setEditCompany] = useState({ cnpj: "", legal_name: "" });

  const loadCompanies = useCallback(async (locationFilter?: CompanyLocationFilter) => {
    const filter = locationFilter === undefined ? companyFilterFromLocation() : locationFilter;
    setLoading(true);
    setError("");
    setQueryError("");
    try {
      const query = new URLSearchParams();
      if (filter !== null) query.set("lifecycle", filter.lifecycle);
      const payload = await listCompanies(query);
      const first = payload.companies[0] ?? null;
      setCompanyResult(payload);
      setCompanies(payload.companies);
      setSelectedCompany(first);
      setEditCompany(first ? { cnpj: first.cnpj, legal_name: first.legal_name } : { cnpj: "", legal_name: "" });
    } catch (caught: unknown) {
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
      setCompanyResult(null);
      setCompanies([]);
      setSelectedCompany(null);
      setError("Não foi possível carregar empresas. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (loadSignal > 0 || companyFilterFromLocation() !== null) void loadCompanies();
  }, [loadCompanies, loadSignal]);

  useEffect(() => {
    const loadLocation = () => {
      if (window.location.hash === "#empresas" && companyFilterFromLocation() !== null) {
        void loadCompanies();
      }
    };
    window.addEventListener("hashchange", loadLocation);
    return () => window.removeEventListener("hashchange", loadLocation);
  }, [loadCompanies]);

  async function companyAction(company: Company, action: "activate" | "deactivate") {
    let body: object = {};
    if (action === "deactivate") {
      if (!window.confirm("Deseja desativar esta empresa? O acervo será preservado.")) return;
      const reason = window.prompt("Informe o motivo da desativação:");
      if (!reason?.trim()) {
        notify("A desativação exige um motivo.");
        return;
      }
      body = { confirmed: true, reason };
    }
    try {
      await changeCompanyState(company.id, action, body);
      await loadCompanies();
    } catch {
      notify("Não foi possível alterar o estado da empresa.");
    }
  }

  async function toggleFlow(company: Company, family: "nfe" | "nfse") {
    const state = company.flows[family]?.state === "pausado" ? "habilitado" : "pausado";
    try {
      await changeFlow(company.id, family, state);
      await loadCompanies();
    } catch {
      notify("Só é possível alterar fluxos de empresa ativa.");
    }
  }

  async function enrichCompany(company: Company) {
    try {
      await enrichCompanyApi(company.id);
      notify("Consulta pública registrada; a fonte não é autoritativa.");
      await loadCompanies();
    } catch {
      notify("Não foi possível solicitar o enriquecimento público.");
    }
  }

  async function saveCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCompany) return;
    try {
      await updateCompanyApi(selectedCompany.id, { ...editCompany, version: selectedCompany.version });
      notify("Empresa atualizada.");
      await loadCompanies();
    } catch (error: unknown) {
      notify(error instanceof ApiError ? error.detail : "Não foi possível editar a empresa.");
    }
  }

  async function createCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createCompanyApi(newCompany);
      setNewCompany({ cnpj: "", legal_name: "" });
      notify("Empresa cadastrada.");
      await loadCompanies();
    } catch (error: unknown) {
      notify(error instanceof ApiError ? error.detail : "Não foi possível cadastrar a empresa.");
    }
  }

  return (
    <section id="empresas">
      <h2>Empresas</h2>
      <CertificateInventoryPanel loadSignal={loadSignal} />
      <button onClick={() => void loadCompanies()}>Atualizar empresas</button>
      {loading && <p role="status">Carregando empresas…</p>}
      <Feedback message={error} error />
      {queryError === "invalid" && <p role="status">O filtro de empresas é inválido.</p>}
      {queryError === "unavailable" && <p role="status">As empresas estão indisponíveis.</p>}
      {queryError === "degraded" && <p role="status">A consulta de empresas está degradada.</p>}
      {!loading && !error && companyResult && (
        <p role="status">
          {companyResult.filter.lifecycle
            ? `Filtro aplicado: ${lifecycleFilterLabel(companyResult.filter.lifecycle)}`
            : "Lista completa de empresas"}
          {" · "}Total reconciliado: {companyResult.total}
          {companyResult.truncated ? " (mostrando somente a primeira página limitada)" : ""}
        </p>
      )}
      {!loading && !error && companyResult && companies.length === 0 && (
        <p>
          {companyResult.filter.lifecycle
            ? "Nenhuma empresa encontrada para este filtro."
            : "Nenhuma empresa cadastrada."}
        </p>
      )}
      <form onSubmit={createCompany}>
        <h3>Cadastrar empresa</h3>
        <label>
          CNPJ
          <input value={newCompany.cnpj} onChange={(event) => setNewCompany({ ...newCompany, cnpj: event.target.value })} required />
        </label>
        <label>
          Razão social
          <input value={newCompany.legal_name} onChange={(event) => setNewCompany({ ...newCompany, legal_name: event.target.value })} required />
        </label>
        <button type="submit">Cadastrar</button>
      </form>
      <table>
        <thead><tr><th>Razão social</th><th>CNPJ</th><th>Estado</th><th>Fluxos</th></tr></thead>
        <tbody>
          {companies.map((company) => (
            <tr
              key={company.id}
              onClick={() => {
                setSelectedCompany(company);
                setEditCompany({ cnpj: company.cnpj, legal_name: company.legal_name });
              }}
            >
              <td>{company.legal_name}</td><td>{company.cnpj}</td><td>{statusLabel(company.status)}</td>
              <td>NF-e: {company.flows.nfe?.state} · NFS-e: {company.flows.nfse?.state}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selectedCompany && (
        <article>
          <h3>Detalhe: {selectedCompany.legal_name}</h3>
          <form onSubmit={saveCompany}>
            <label>
              CNPJ
              <input value={editCompany.cnpj} onChange={(event) => setEditCompany({ ...editCompany, cnpj: event.target.value })} required />
            </label>
            <label>
              Razão social
              <input value={editCompany.legal_name} onChange={(event) => setEditCompany({ ...editCompany, legal_name: event.target.value })} />
            </label>
            <button type="submit">Salvar empresa</button>
          </form>
          <p>CNPJ {selectedCompany.cnpj} · {statusLabel(selectedCompany.status)}</p>
          {selectedCompany.status === "ativa" && (
            <p>
              <button onClick={() => void toggleFlow(selectedCompany, "nfe")}>NF-e {selectedCompany.flows.nfe?.state === "pausado" ? "habilitar" : "pausar"}</button>{" "}
              <button onClick={() => void toggleFlow(selectedCompany, "nfse")}>NFS-e {selectedCompany.flows.nfse?.state === "pausado" ? "habilitar" : "pausar"}</button>
            </p>
          )}
          <button onClick={() => void companyAction(selectedCompany, selectedCompany.status === "ativa" ? "deactivate" : "activate")}>
            {selectedCompany.status === "ativa" ? "Desativar" : "Ativar"}
          </button>{" "}
          <button onClick={() => void enrichCompany(selectedCompany)}>Atualizar dados públicos</button>
          <CertificatePanel companyId={selectedCompany.id} onChanged={loadCompanies} notify={notify} />
        </article>
      )}
    </section>
  );
}
