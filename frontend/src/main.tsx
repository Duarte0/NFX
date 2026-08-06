import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type User = { id: string; name: string; role: "administrador" | "operador" | "visualizador" };
type AuditEvent = { id: string; sequence: number; occurred_at: string; action: string; entity_type: string; entity_id: string; result: string; reason: string; actor_id: string | null };
type ManagedUser = User & { email: string; active: boolean; version: number };
type CompanyFlow = { id: string; state: "habilitado" | "pausado" };
type Company = { id: string; cnpj: string; legal_name: string; status: "cadastrada" | "ativa" | "desativada"; first_collection_at: string | null; deactivation_reason: string | null; version: number; flows: Record<string, CompanyFlow>; enrichment: { status: string; public_non_authoritative: boolean; payload: unknown; error_code: string } | null };

function cookie(name: string): string {
  return document.cookie.split("; ").find((part) => part.startsWith(`${name}=`))?.split("=")[1] ?? "";
}

function statusLabel(status: Company["status"]): string {
  return { cadastrada: "Cadastrada", ativa: "Ativa", desativada: "Desativada" }[status];
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [newUser, setNewUser] = useState({ name: "", email: "", role: "visualizador", password: "" });
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [companiesLoading, setCompaniesLoading] = useState(false);
  const [companiesError, setCompaniesError] = useState("");
  const [newCompany, setNewCompany] = useState({ cnpj: "", legal_name: "" });
  const [editCompany, setEditCompany] = useState({ cnpj: "", legal_name: "" });

  useEffect(() => {
    void fetch("/api/auth/csrf", { credentials: "same-origin" })
      .then(() => fetch("/api/auth/session", { credentials: "same-origin" }))
      .then(async (response) => (response.ok ? (response.json() as Promise<{ user: User }>) : null))
      .then((payload) => setUser(payload?.user ?? null));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/auth/login", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") }, body: JSON.stringify({ email, password }) });
    if (!response.ok) { setMessage("Não foi possível iniciar a sessão. Verifique suas credenciais."); return; }
    const payload = (await response.json()) as { user: User };
    setPassword(""); setMessage(""); setUser(payload.user);
  }

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": cookie("csrftoken") } });
    setUser(null); setMessage("Sessão encerrada.");
  }

  async function loadAudit() {
    const response = await fetch("/api/audit/events", { credentials: "same-origin" });
    if (!response.ok) { setMessage("Não foi possível consultar a auditoria."); return; }
    const payload = (await response.json()) as { events: AuditEvent[] }; setAuditEvents(payload.events);
  }

  async function loadUsers() {
    const response = await fetch("/api/users", { credentials: "same-origin" });
    if (!response.ok) { setMessage("Não foi possível consultar usuários."); return; }
    const payload = (await response.json()) as { users: ManagedUser[] }; setManagedUsers(payload.users);
  }

  async function createManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/users/create", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") }, body: JSON.stringify(newUser) });
    if (!response.ok) { setMessage("Não foi possível criar o usuário."); return; }
    setNewUser({ name: "", email: "", role: "visualizador", password: "" }); await loadUsers();
  }

  async function loadCompanies() {
    setCompaniesLoading(true); setCompaniesError("");
    try {
      const response = await fetch("/api/companies", { credentials: "same-origin" });
      if (!response.ok) throw new Error("companies");
      const payload = (await response.json()) as { companies: Company[] };
      setCompanies(payload.companies); setSelectedCompany(payload.companies[0] ?? null); setEditCompany(payload.companies[0] ? { cnpj: payload.companies[0].cnpj, legal_name: payload.companies[0].legal_name } : { cnpj: "", legal_name: "" });
    } catch { setCompaniesError("Não foi possível carregar empresas. Tente novamente."); }
    finally { setCompaniesLoading(false); }
  }

  async function createCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/companies/create", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") }, body: JSON.stringify(newCompany) });
    if (!response.ok) { setMessage((await response.json() as { detail?: string }).detail ?? "Não foi possível cadastrar a empresa."); return; }
    setNewCompany({ cnpj: "", legal_name: "" }); setMessage("Empresa cadastrada."); await loadCompanies();
  }

  async function companyAction(company: Company, action: "activate" | "deactivate") {
    let body: object = {};
    if (action === "deactivate") {
      if (!window.confirm("Deseja desativar esta empresa? O acervo será preservado.")) return;
      const reason = window.prompt("Informe o motivo da desativação:");
      if (!reason?.trim()) { setMessage("A desativação exige um motivo."); return; }
      body = { confirmed: true, reason };
    }
    const response = await fetch(`/api/companies/${company.id}/${action}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") }, body: JSON.stringify(body) });
    if (!response.ok) { setMessage("Não foi possível alterar o estado da empresa."); return; }
    await loadCompanies();
  }

  async function toggleFlow(company: Company, family: "nfe" | "nfse") {
    const current = company.flows[family]?.state;
    const state = current === "pausado" ? "habilitado" : "pausado";
    const response = await fetch(`/api/companies/${company.id}/flows/${family}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") }, body: JSON.stringify({ state }) });
    if (!response.ok) { setMessage("Só é possível alterar fluxos de empresa ativa."); return; }
    await loadCompanies();
  }

  async function enrichCompany(company: Company) {
    const response = await fetch(`/api/companies/${company.id}/enrichment`, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": cookie("csrftoken") } });
    if (!response.ok) { setMessage("Não foi possível solicitar o enriquecimento público."); return; }
    setMessage("Consulta pública registrada; a fonte não é autoritativa."); await loadCompanies();
  }

  async function updateCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCompany) return;
    const response = await fetch(`/api/companies/${selectedCompany.id}`, { method: "PATCH", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") }, body: JSON.stringify({ ...editCompany, version: selectedCompany.version }) });
    if (!response.ok) { setMessage((await response.json() as { detail?: string }).detail ?? "Não foi possível editar a empresa."); return; }
    setMessage("Empresa atualizada."); await loadCompanies();
  }

  if (!user) return <main lang="pt-BR"><h1>NFX INOV</h1><p>{message || "Acesse sua conta."}</p><form onSubmit={submit}><label>E-mail<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Senha<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label><button type="submit">Entrar</button></form></main>;
  const canManage = user.role !== "visualizador";
  const isAdmin = user.role === "administrador";
  return <main lang="pt-BR"><header><h1>NFX INOV</h1><p>{user.name} · {user.role}</p><button onClick={() => void signOut()}>Sair</button></header><nav aria-label="Navegação principal"><a href="#documentos">Documentos</a><a href="#exportacoes">Exportações</a>{canManage && <><a href="#empresas" onClick={() => void loadCompanies()}>Empresas</a><a href="#certificados">Certificados</a><a href="#coletas">Coletas</a></>}{isAdmin && <><a href="#usuarios" onClick={() => void loadUsers()}>Usuários</a><a href="#auditoria" onClick={() => void loadAudit()}>Auditoria</a></>}</nav><p>Horários em Brasília · valores em R$.</p>{canManage && <section id="empresas"><h2>Empresas</h2><button onClick={() => void loadCompanies()}>Atualizar empresas</button>{companiesLoading && <p role="status">Carregando empresas…</p>}{companiesError && <p role="alert">{companiesError}</p>} {!companiesLoading && !companiesError && companies.length === 0 && <p>Nenhuma empresa cadastrada.</p>}<form onSubmit={createCompany}><h3>Cadastrar empresa</h3><label>CNPJ<input value={newCompany.cnpj} onChange={(event) => setNewCompany({ ...newCompany, cnpj: event.target.value })} required /></label><label>Razão social<input value={newCompany.legal_name} onChange={(event) => setNewCompany({ ...newCompany, legal_name: event.target.value })} required /></label><button type="submit">Cadastrar</button></form><table><thead><tr><th>Razão social</th><th>CNPJ</th><th>Estado</th><th>Fluxos</th><th>Ações</th></tr></thead><tbody>{companies.map((company) => <tr key={company.id} onClick={() => { setSelectedCompany(company); setEditCompany({ cnpj: company.cnpj, legal_name: company.legal_name }); }}><td>{company.legal_name}</td><td>{company.cnpj}</td><td>{statusLabel(company.status)}</td><td>NF-e: {company.flows.nfe?.state} · NFS-e: {company.flows.nfse?.state}</td><td>{company.status === "ativa" ? <button onClick={(event) => { event.stopPropagation(); void companyAction(company, "deactivate"); }}>Desativar</button> : <button onClick={(event) => { event.stopPropagation(); void companyAction(company, "activate"); }}>Ativar</button>}</td></tr>)}</tbody></table>{selectedCompany && <article><h3>Detalhe: {selectedCompany.legal_name}</h3><form onSubmit={updateCompany}><label>CNPJ<input value={editCompany.cnpj} onChange={(event) => setEditCompany({ ...editCompany, cnpj: event.target.value })} required /></label><label>Razão social<input value={editCompany.legal_name} onChange={(event) => setEditCompany({ ...editCompany, legal_name: event.target.value })} required /></label><button type="submit">Salvar empresa</button></form><p>CNPJ {selectedCompany.cnpj} · {statusLabel(selectedCompany.status)}</p><p>Primeira coleta durável: {selectedCompany.first_collection_at ?? "ainda não realizada"}</p>{selectedCompany.status === "ativa" && <p><button onClick={() => void toggleFlow(selectedCompany, "nfe")}>NF-e {selectedCompany.flows.nfe?.state === "pausado" ? "habilitar" : "pausar"}</button> <button onClick={() => void toggleFlow(selectedCompany, "nfse")}>NFS-e {selectedCompany.flows.nfse?.state === "pausado" ? "habilitar" : "pausar"}</button></p>}<button onClick={() => void enrichCompany(selectedCompany)}>Atualizar dados públicos</button>{selectedCompany.enrichment && <p>OpenCNPJ: {selectedCompany.enrichment.status} · público e não autoritativo.</p>}</article>}</section>}{isAdmin && <section id="usuarios"><h2>Usuários</h2><button onClick={() => void loadUsers()}>Atualizar usuários</button><form onSubmit={createManagedUser}><label>Nome<input value={newUser.name} onChange={(event) => setNewUser({ ...newUser, name: event.target.value })} required /></label><label>E-mail<input type="email" value={newUser.email} onChange={(event) => setNewUser({ ...newUser, email: event.target.value })} required /></label><label>Papel<select value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value })}><option value="administrador">Administrador</option><option value="operador">Operador</option><option value="visualizador">Visualizador</option></select></label><label>Senha inicial<input type="password" value={newUser.password} onChange={(event) => setNewUser({ ...newUser, password: event.target.value })} required /></label><button type="submit">Criar usuário</button></form><table><thead><tr><th>Nome</th><th>E-mail</th><th>Papel</th><th>Estado</th></tr></thead><tbody>{managedUsers.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.email}</td><td>{item.role}</td><td>{item.active ? "Ativo" : "Desativado"}</td></tr>)}</tbody></table></section>}{isAdmin && <section id="auditoria"><h2>Auditoria</h2><button onClick={() => void loadAudit()}>Atualizar auditoria</button><table><thead><tr><th>Data/hora</th><th>Ação</th><th>Entidade</th><th>Resultado</th><th>Motivo</th></tr></thead><tbody>{auditEvents.map((item) => <tr key={item.id}><td>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium", timeZone: "America/Sao_Paulo" }).format(new Date(item.occurred_at))}</td><td>{item.action}</td><td>{item.entity_type}{item.entity_id ? ` · ${item.entity_id}` : ""}</td><td>{item.result}</td><td>{item.reason}</td></tr>)}</tbody></table></section>}</main>;
}

const root = document.getElementById("root");
if (!root) throw new Error("root element is required");
createRoot(root).render(<App />);
