import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
import { CertificatePanel } from "../certificates/CertificatePanel";
import {
  changeCompanyState,
  changeFlow,
  createCompany as createCompanyApi,
  enrichCompany as enrichCompanyApi,
  listCompanies,
  updateCompany as updateCompanyApi,
} from "./api";
import { Company } from "./types";

function statusLabel(status: Company["status"]): string {
  return { cadastrada: "Cadastrada", ativa: "Ativa", desativada: "Desativada" }[status];
}

type CompaniesSectionProps = {
  loadSignal: number;
  notify: (message: string) => void;
};

export function CompaniesSection({ loadSignal, notify }: CompaniesSectionProps) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [newCompany, setNewCompany] = useState({ cnpj: "", legal_name: "" });
  const [editCompany, setEditCompany] = useState({ cnpj: "", legal_name: "" });

  const loadCompanies = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await listCompanies();
      const first = payload.companies[0] ?? null;
      setCompanies(payload.companies);
      setSelectedCompany(first);
      setEditCompany(first ? { cnpj: first.cnpj, legal_name: first.legal_name } : { cnpj: "", legal_name: "" });
    } catch {
      setError("Não foi possível carregar empresas. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (loadSignal > 0) void loadCompanies();
  }, [loadCompanies, loadSignal]);

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
      <button onClick={() => void loadCompanies()}>Atualizar empresas</button>
      {loading && <p role="status">Carregando empresas…</p>}
      <Feedback message={error} error />
      {!loading && !error && companies.length === 0 && <p>Nenhuma empresa cadastrada.</p>}
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
