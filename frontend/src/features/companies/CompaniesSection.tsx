import { FormEvent, ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback, FeedbackState } from "../../shared/ui/Feedback";
import { Badge, Button, DataTable, Field, Panel } from "../../shared/ui/primitives";
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

type CompanyAction = "activate" | "deactivate";
type FlowFamily = "nfe" | "nfse";

export type CompanyLocationFilter = URLSearchParams;

export type CompaniesPresentationProps = {
  companies: Company[];
  companyResult: CompanyListResponse | null;
  selectedCompany: Company | null;
  loading: boolean;
  stale: boolean;
  error: string;
  queryError: "unavailable" | "invalid" | "degraded" | "";
  actionBusy: string;
  newCompany: { cnpj: string; legal_name: string };
  editCompany: { cnpj: string; legal_name: string };
  onReload: () => void;
  onRetry: () => void;
  onFilterChange: (query: URLSearchParams) => void;
  onNextPage: () => void;
  onCreate: (event: FormEvent<HTMLFormElement>) => void;
  onEdit: (event: FormEvent<HTMLFormElement>) => void;
  onSelect: (company: Company) => void;
  onCompanyAction: (company: Company, action: CompanyAction) => void;
  onToggleFlow: (company: Company, family: FlowFamily) => void;
  onEnrich: (company: Company) => void;
  onNewCompanyChange: (value: { cnpj: string; legal_name: string }) => void;
  onEditCompanyChange: (value: { cnpj: string; legal_name: string }) => void;
  onCertificateChanged?: () => Promise<void>;
  onCertificateNotify?: (message: string) => void;
  children?: ReactNode;
};

export function companyFilterFromLocation(): CompanyLocationFilter {
  const current = new URLSearchParams(window.location.search);
  const selected = new URLSearchParams();
  for (const key of ["lifecycle", "status", "search", "limit", "cursor"]) {
    for (const value of current.getAll(key)) selected.append(key, value);
  }
  return selected;
}

function lifecycleFilterLabel(lifecycle: string | undefined): string {
  return {
    active: "Empresas ativas",
    inactive: "Empresas inativas",
  }[lifecycle ?? ""] ?? "Filtro de empresas informado pelo servidor";
}

export function companyStatusLabel(status: string): string {
  return {
    cadastrada: "Empresa cadastrada",
    ativa: "Empresa ativa",
    desativada: "Empresa desativada",
  }[status] ?? "Estado da empresa informado pelo servidor";
}

export function flowStateLabel(state: string): string {
  return {
    habilitado: "Fluxo habilitado",
    pausado: "Fluxo pausado",
  }[state] ?? "Estado do fluxo informado pelo servidor";
}

function enrichmentLabel(status: string): string {
  return {
    sucesso: "Consulta pública concluída",
    vazio: "Consulta pública sem dados",
    nao_encontrado: "Empresa não encontrada na fonte pública",
    timeout: "Consulta pública demorou além do limite",
    indisponivel: "Fonte pública indisponível",
    malformado: "Resposta pública não utilizável",
  }[status] ?? "Estado do enriquecimento público informado pelo servidor";
}

function statusVariant(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "ativa") return "success";
  if (status === "desativada") return "danger";
  return "neutral";
}

function flowVariant(state: string): "success" | "warning" | "neutral" {
  return state === "habilitado" ? "success" : state === "pausado" ? "warning" : "neutral";
}

function queryErrorState(error: CompaniesPresentationProps["queryError"]): FeedbackState {
  if (error === "invalid") return "error";
  if (error === "degraded") return "degraded";
  return "unavailable";
}

function StaleNotice({ stale }: { stale: boolean }) {
  return stale ? (
    <div className="feature-stale" role="status">
      <Badge variant="warning">Leitura desatualizada</Badge>
      <span>A última leitura segura permanece visível enquanto a atualização termina.</span>
    </div>
  ) : null;
}

export function CompaniesPresentation({
  companies,
  companyResult,
  selectedCompany,
  loading,
  stale,
  error,
  queryError,
  actionBusy,
  newCompany,
  editCompany,
  onReload,
  onRetry,
  onFilterChange,
  onNextPage,
  onCreate,
  onEdit,
  onSelect,
  onCompanyAction,
  onToggleFlow,
  onEnrich,
  onNewCompanyChange,
  onEditCompanyChange,
  onCertificateChanged,
  onCertificateNotify,
  children,
}: CompaniesPresentationProps) {
  function submitFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const query = new URLSearchParams();
    const lifecycle = values.get("lifecycle");
    const status = values.get("status");
    const search = values.get("search");
    if (typeof lifecycle === "string" && lifecycle) query.set("lifecycle", lifecycle);
    else if (typeof status === "string" && status) query.set("status", status);
    if (typeof search === "string" && search) query.set("search", search);
    onFilterChange(query);
  }

  return (
    <section id="empresas" aria-labelledby="empresas-title" className="feature-section">
      <div className="feature-heading">
        <div>
          <p className="feature-eyebrow">Cadastro e ciclo de vida</p>
          <h2 id="empresas-title">Empresas</h2>
          <p className="feature-intro">Identidade, fluxos e enriquecimento público em contextos separados.</p>
        </div>
        <Button variant="secondary" onClick={onReload} disabled={loading}>Atualizar empresas</Button>
      </div>
      <form key={`${companyResult?.filter.lifecycle ?? ""}-${companyResult?.filter.status ?? ""}-${companyResult?.filter.search ?? ""}`} className="feature-filter-form" onSubmit={submitFilter}>
        <Field id="company-lifecycle" label="Ciclo de vida">
          <select name="lifecycle" defaultValue={companyResult?.filter.lifecycle ?? ""}>
            <option value="">Todas as empresas</option>
            <option value="active">Empresas ativas</option>
            <option value="inactive">Empresas inativas</option>
          </select>
        </Field>
        <Field id="company-status" label="Estado cadastral">
          <select name="status" defaultValue={companyResult?.filter.status ?? ""}>
            <option value="">Qualquer estado</option>
            <option value="cadastrada">Empresa cadastrada</option>
            <option value="ativa">Empresa ativa</option>
            <option value="desativada">Empresa desativada</option>
          </select>
        </Field>
        <Field id="company-search" label="Busca" hint="A validação do limite permanece no servidor.">
          <input name="search" defaultValue={companyResult?.filter.search ?? ""} />
        </Field>
        <Button type="submit" variant="secondary">Aplicar filtros</Button>
      </form>
      {loading && <Feedback state="loading" message="Carregando empresas…" />}
      <StaleNotice stale={stale} />
      {error && <Feedback state={queryErrorState(queryError)} message={error} />}
      {queryError === "invalid" && <Feedback state="error" message="Os filtros de empresas são inválidos." />}
      {queryError === "unavailable" && <Feedback state="unavailable" message="As empresas estão indisponíveis." />}
      {queryError === "degraded" && <Feedback state="degraded" message="A consulta de empresas está degradada." />}
      {(error || queryError) && <Button variant="secondary" onClick={onRetry} disabled={loading}>Tentar novamente</Button>}
      {!loading && !error && !queryError && companyResult && (
        <div className="feature-summary" role="status">
          <span>{companyResult.filter.lifecycle ? lifecycleFilterLabel(companyResult.filter.lifecycle) : "Lista de empresas"}</span>
          <span>Total reconciliado: {companyResult.total}</span>
          <span>Limite: {companyResult.limit}</span>
          <span>{companyResult.truncated ? "Há mais resultados" : "Todos os resultados desta consulta foram apresentados"}</span>
        </div>
      )}
      <Panel as="section" title="Cadastrar empresa" className="feature-panel">
        <form className="feature-form" onSubmit={onCreate}>
          <Field id="new-company-cnpj" label="CNPJ" required><input value={newCompany.cnpj} onChange={(event) => onNewCompanyChange({ ...newCompany, cnpj: event.target.value })} required /></Field>
          <Field id="new-company-name" label="Razão social" required><input value={newCompany.legal_name} onChange={(event) => onNewCompanyChange({ ...newCompany, legal_name: event.target.value })} required /></Field>
          <Button type="submit" disabled={actionBusy === "create-company"}>{actionBusy === "create-company" ? "Cadastrando…" : "Cadastrar empresa"}</Button>
        </form>
      </Panel>
      {!loading && !error && companyResult && companies.length === 0 && (
        <Feedback state="empty" message={companyResult.filter.lifecycle ? "Nenhuma empresa encontrada para este filtro." : "Nenhuma empresa cadastrada."} />
      )}
      {companies.length > 0 && (
        <DataTable caption="Empresas consultadas" className="company-table">
          <thead><tr><th>Empresa</th><th>Estado</th><th>Fluxos</th><th>Ação</th></tr></thead>
          <tbody>
            {companies.map((company) => (
              <tr key={company.id} className={selectedCompany?.id === company.id ? "is-selected" : undefined}>
                <td><strong>{company.legal_name}</strong><br /><small>{company.cnpj}</small></td>
                <td><Badge variant={statusVariant(company.status)}>{companyStatusLabel(company.status)}</Badge></td>
                <td className="feature-badge-list">
                  {(["nfe", "nfse"] as const).map((family) => {
                    const flow = company.flows[family];
                    return flow ? <Badge key={family} variant={flowVariant(flow.state)}>{family === "nfe" ? "NF-e" : "NFS-e"}: {flowStateLabel(flow.state)}</Badge> : <Badge key={family} variant="neutral">{family === "nfe" ? "NF-e" : "NFS-e"}: Fluxo não informado</Badge>;
                  })}
                </td>
                <td><Button variant="secondary" onClick={() => onSelect(company)} aria-label={`Abrir empresa ${company.legal_name}`}>Abrir detalhe</Button></td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      {companyResult?.next_cursor && <div className="feature-pagination"><Button variant="secondary" onClick={onNextPage} disabled={loading}>Próxima página</Button><span>Os filtros permanecem ativos na próxima página.</span></div>}
      {selectedCompany && (
        <Panel as="article" title={`Detalhe: ${selectedCompany.legal_name}`} className="feature-panel company-detail">
          <div className="feature-summary">
            <Badge variant={statusVariant(selectedCompany.status)}>{companyStatusLabel(selectedCompany.status)}</Badge>
            <span>Identificador da empresa: {selectedCompany.cnpj}</span>
          </div>
          <form className="feature-form" onSubmit={onEdit}>
            <Field id="edit-company-cnpj" label="CNPJ" hint={selectedCompany.first_collection_at ? "O CNPJ fica imutável após a primeira coleta." : undefined}><input value={editCompany.cnpj} onChange={(event) => onEditCompanyChange({ ...editCompany, cnpj: event.target.value })} required disabled={Boolean(selectedCompany.first_collection_at)} /></Field>
            <Field id="edit-company-name" label="Razão social"><input value={editCompany.legal_name} onChange={(event) => onEditCompanyChange({ ...editCompany, legal_name: event.target.value })} required /></Field>
            <Button type="submit" disabled={actionBusy === "edit-company"}>{actionBusy === "edit-company" ? "Salvando…" : "Salvar empresa"}</Button>
          </form>
          <div className="feature-detail-grid">
            {(["nfe", "nfse"] as const).map((family) => {
              const flow = selectedCompany.flows[family];
              return flow ? (
                <Panel as="section" key={family} title={family === "nfe" ? "NF-e" : "NFS-e"} className="feature-subpanel">
                  <Badge variant={flowVariant(flow.state)}>{family === "nfe" ? "NF-e" : "NFS-e"}: {flowStateLabel(flow.state)}</Badge>
                  {selectedCompany.status === "ativa" && <Button variant="secondary" onClick={() => onToggleFlow(selectedCompany, family)} disabled={Boolean(actionBusy)}>{flow.state === "pausado" ? "Habilitar fluxo" : "Pausar fluxo"}</Button>}
                </Panel>
              ) : null;
            })}
          </div>
          {selectedCompany.enrichment ? (
            <div className="feature-enrichment" role="status">
              <Badge variant={selectedCompany.enrichment.status === "sucesso" ? "success" : "warning"}>{enrichmentLabel(selectedCompany.enrichment.status)}</Badge>
              <span>Enriquecimento público não autoritativo; não altera a identidade fiscal cadastrada.</span>
            </div>
          ) : <Feedback state="empty" message="Enriquecimento público ainda não consultado; a ausência não impede o cadastro ou a coleta." />}
          <div className="feature-actions">
            <Button variant={selectedCompany.status === "ativa" ? "danger" : "secondary"} onClick={() => onCompanyAction(selectedCompany, selectedCompany.status === "ativa" ? "deactivate" : "activate")} disabled={Boolean(actionBusy)}>{selectedCompany.status === "ativa" ? "Desativar empresa" : "Ativar empresa"}</Button>
            <Button variant="secondary" onClick={() => onEnrich(selectedCompany)} disabled={Boolean(actionBusy)}>Consultar dados públicos</Button>
          </div>
          <CertificatePanel companyId={selectedCompany.id} onChanged={onCertificateChanged ?? (async () => undefined)} notify={onCertificateNotify ?? (() => undefined)} />
        </Panel>
      )}
      {children}
    </section>
  );
}

export function CompaniesSection({ loadSignal, notify }: { loadSignal: number; notify: (message: string) => void }) {
  const [companyResult, setCompanyResult] = useState<CompanyListResponse | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [queryError, setQueryError] = useState<CompaniesPresentationProps["queryError"]>("");
  const [actionBusy, setActionBusy] = useState("");
  const [newCompany, setNewCompany] = useState({ cnpj: "", legal_name: "" });
  const [editCompany, setEditCompany] = useState({ cnpj: "", legal_name: "" });
  const companyRequestSequence = useRef(0);
  const resultRef = useRef<CompanyListResponse | null>(null);

  const loadCompanies = useCallback(async (requestedQuery: CompanyLocationFilter = companyFilterFromLocation()) => {
    const requestId = ++companyRequestSequence.current;
    setLoading(true);
    setError("");
    setQueryError("");
    setStale(resultRef.current !== null);
    try {
      const payload = await listCompanies(new URLSearchParams(requestedQuery));
      if (requestId !== companyRequestSequence.current) return;
      resultRef.current = payload;
      setCompanyResult(payload);
      setStale(false);
      setSelectedCompany((current) => {
        const next = payload.companies.find((company) => company.id === current?.id) ?? payload.companies[0] ?? null;
        if (next) setEditCompany({ cnpj: next.cnpj, legal_name: next.legal_name });
        return next;
      });
    } catch (caught: unknown) {
      if (requestId !== companyRequestSequence.current) return;
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
      setStale(resultRef.current !== null);
      setError("Não foi possível carregar empresas. A última leitura segura continua disponível.");
    } finally {
      if (requestId === companyRequestSequence.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (loadSignal > 0 || companyFilterFromLocation().toString()) void loadCompanies();
  }, [loadCompanies, loadSignal]);

  useEffect(() => {
    const loadLocation = () => {
      if (window.location.hash === "#empresas" || companyFilterFromLocation().toString()) void loadCompanies();
    };
    window.addEventListener("hashchange", loadLocation);
    window.addEventListener("popstate", loadLocation);
    return () => {
      window.removeEventListener("hashchange", loadLocation);
      window.removeEventListener("popstate", loadLocation);
    };
  }, [loadCompanies]);

  async function runMutation(key: string, operation: () => Promise<void>) {
    if (actionBusy) return;
    setActionBusy(key);
    try {
      await operation();
    } finally {
      setActionBusy("");
    }
  }

  function changeFilter(query: URLSearchParams) {
    const url = new URL(window.location.href);
    url.search = query.toString();
    window.history.pushState(null, "", `${url.pathname}${url.search}${url.hash || "#empresas"}`);
    void loadCompanies(query);
  }

  function nextPage() {
    if (!companyResult?.next_cursor) return;
    const query = companyFilterFromLocation();
    query.set("cursor", companyResult.next_cursor);
    changeFilter(query);
  }

  async function companyAction(company: Company, action: CompanyAction) {
    if (action === "deactivate") {
      if (!window.confirm("Deseja desativar esta empresa? O acervo será preservado.")) return;
      const reason = window.prompt("Informe o motivo da desativação:");
      if (!reason?.trim()) {
        notify("A desativação exige um motivo.");
        return;
      }
      await runMutation(`company-${action}`, async () => {
        try {
          await changeCompanyState(company.id, action, { confirmed: true, reason });
          await loadCompanies();
        } catch {
          notify("Não foi possível alterar o estado da empresa.");
        }
      });
      return;
    }
    await runMutation(`company-${action}`, async () => {
      try {
        await changeCompanyState(company.id, action, {});
        await loadCompanies();
      } catch {
        notify("Não foi possível alterar o estado da empresa.");
      }
    });
  }

  async function toggleFlow(company: Company, family: FlowFamily) {
    const state = company.flows[family]?.state === "pausado" ? "habilitado" : "pausado";
    await runMutation(`flow-${family}`, async () => {
      try {
        await changeFlow(company.id, family, state);
        await loadCompanies();
      } catch {
        notify("Só é possível alterar fluxos de empresa ativa.");
      }
    });
  }

  async function enrichCompany(company: Company) {
    await runMutation("enrichment", async () => {
      try {
        await enrichCompanyApi(company.id);
        notify("Consulta pública registrada; a fonte não é autoritativa.");
        await loadCompanies();
      } catch {
        notify("Não foi possível solicitar o enriquecimento público.");
      }
    });
  }

  async function saveCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCompany) return;
    await runMutation("edit-company", async () => {
      try {
        await updateCompanyApi(selectedCompany.id, { ...editCompany, version: selectedCompany.version });
        notify("Empresa atualizada.");
        await loadCompanies();
      } catch (caught: unknown) {
        notify(caught instanceof ApiError ? caught.detail : "Não foi possível editar a empresa.");
      }
    });
  }

  async function createCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runMutation("create-company", async () => {
      try {
        await createCompanyApi(newCompany);
        setNewCompany({ cnpj: "", legal_name: "" });
        notify("Empresa cadastrada.");
        await loadCompanies();
      } catch (caught: unknown) {
        notify(caught instanceof ApiError ? caught.detail : "Não foi possível cadastrar a empresa.");
      }
    });
  }

  return (
    <CompaniesPresentation
      companies={companyResult?.companies ?? []}
      companyResult={companyResult}
      selectedCompany={selectedCompany}
      loading={loading}
      stale={stale}
      error={error}
      queryError={queryError}
      actionBusy={actionBusy}
      newCompany={newCompany}
      editCompany={editCompany}
      onReload={() => void loadCompanies()}
      onRetry={() => void loadCompanies()}
      onFilterChange={changeFilter}
      onNextPage={nextPage}
      onCreate={createCompany}
      onEdit={saveCompany}
      onSelect={(company) => { setSelectedCompany(company); setEditCompany({ cnpj: company.cnpj, legal_name: company.legal_name }); }}
      onCompanyAction={(company, action) => void companyAction(company, action)}
      onToggleFlow={(company, family) => void toggleFlow(company, family)}
      onEnrich={(company) => void enrichCompany(company)}
      onNewCompanyChange={setNewCompany}
      onEditCompanyChange={setEditCompany}
      onCertificateChanged={() => loadCompanies()}
      onCertificateNotify={notify}
      children={(
        <section id="certificados" aria-labelledby="certificados-heading" className="feature-section__child">
          <h3 id="certificados-heading">Certificados</h3>
          <CertificateInventoryPanel loadSignal={loadSignal} />
        </section>
      )}
    />
  );
}
