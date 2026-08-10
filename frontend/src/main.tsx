import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type User = {
  id: string;
  name: string;
  role: "administrador" | "operador" | "visualizador";
};
type AuditEvent = {
  id: string;
  sequence: number;
  occurred_at: string;
  action: string;
  entity_type: string;
  entity_id: string;
  result: string;
  reason: string;
  actor_id: string | null;
};
type ManagedUser = User & { email: string; active: boolean; version: number };
type CompanyFlow = { id: string; state: "habilitado" | "pausado" };
type Company = {
  id: string;
  cnpj: string;
  legal_name: string;
  status: "cadastrada" | "ativa" | "desativada";
  first_collection_at: string | null;
  deactivation_reason: string | null;
  version: number;
  flows: Record<string, CompanyFlow>;
  enrichment: {
    status: string;
    public_non_authoritative: boolean;
    payload: unknown;
    error_code: string;
  } | null;
};
type Certificate = {
  id: string;
  state: string;
  status: string;
  fingerprint_sha256: string;
  certificate_cnpj: string;
  not_before: string;
  not_after: string;
  days_until_expiry: number | null;
  key_version: number;
};
type CollectionFlow = {
  family: "nfe" | "nfse";
  flow_state: string;
  collection_state: string;
  last_attempt_at: string | null;
  last_success_at: string | null;
  next_scheduled_at: string | null;
  cooldown_until: string | null;
  blocked_reason: string;
  safe_error: string;
  progress: { current: number; total: number };
  active_execution: {
    id: string;
    state: string;
    safe_error: string;
    safe_summary: Record<string, unknown>;
  } | null;
  latest_execution: {
    id: string;
    state: string;
    safe_error: string;
    origin: string;
  } | null;
};
type CollectionCompany = {
  company_id: string;
  legal_name: string;
  status: string;
  flows: CollectionFlow[];
};
type DocumentItem = {
  id: string;
  company_id: string;
  company_name: string;
  family: string;
  role: string | null;
  category: string;
  source: string | null;
  flow: string;
  identity: string;
  identity_kind: string | null;
  emitted_at: string | null;
  authorized_at: string | null;
  competence: string | null;
  situation: string | null;
  outcome: "persisted" | "quarantine" | "conflict";
  evidence_available: boolean;
  reason_code: string | null;
};
type DocumentResponse = {
  status:
    | "available"
    | "valid_empty"
    | "unavailable"
    | "no_coverage"
    | "unknown"
    | "partial"
    | "retry"
    | "blocked";
  reason_code: string;
  documents: DocumentItem[];
  collection_states: Array<{
    company_id: string | null;
    family: string | null;
    flow: string | null;
    status: string;
    reason_code: string;
  }>;
  next_cursor: string | null;
};

function cookie(name: string): string {
  return (
    document.cookie
      .split("; ")
      .find((part) => part.startsWith(`${name}=`))
      ?.split("=")[1] ?? ""
  );
}

function statusLabel(status: Company["status"]): string {
  return { cadastrada: "Cadastrada", ativa: "Ativa", desativada: "Desativada" }[
    status
  ];
}

function collectionLabel(status: string): string {
  return (
    {
      idle: "Sem coleta",
      queued: "Na fila",
      running: "Em execução",
      concluded: "Concluída",
      empty: "Consulta válida sem documentos",
      partial: "Parcial",
      retrying: "Retry agendado",
      cooldown: "Cooldown",
      blocked: "Bloqueada",
      failed: "Falha",
    }[status] ?? status
  );
}

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
  return {
    persisted: "Persistido",
    quarantine: "Quarentena",
    conflict: "Conflito",
  }[outcome];
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [newUser, setNewUser] = useState({
    name: "",
    email: "",
    role: "visualizador",
    password: "",
  });
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [companiesLoading, setCompaniesLoading] = useState(false);
  const [companiesError, setCompaniesError] = useState("");
  const [newCompany, setNewCompany] = useState({ cnpj: "", legal_name: "" });
  const [editCompany, setEditCompany] = useState({ cnpj: "", legal_name: "" });
  const [certificate, setCertificate] = useState<Certificate | null>(null);
  const [certificateFile, setCertificateFile] = useState<File | null>(null);
  const [certificatePassword, setCertificatePassword] = useState("");
  const [collectionCompanies, setCollectionCompanies] = useState<
    CollectionCompany[]
  >([]);
  const [documents, setDocuments] = useState<DocumentResponse | null>(null);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState("");

  useEffect(() => {
    void fetch("/api/auth/csrf", { credentials: "same-origin" })
      .then(() => fetch("/api/auth/session", { credentials: "same-origin" }))
      .then(async (response) =>
        response.ok ? (response.json() as Promise<{ user: User }>) : null,
      )
      .then((payload) => setUser(payload?.user ?? null));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": cookie("csrftoken"),
      },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setMessage(
        "Não foi possível iniciar a sessão. Verifique suas credenciais.",
      );
      return;
    }
    const payload = (await response.json()) as { user: User };
    setPassword("");
    setMessage("");
    setUser(payload.user);
  }

  async function signOut() {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": cookie("csrftoken") },
    });
    setUser(null);
    setMessage("Sessão encerrada.");
  }

  async function loadAudit() {
    const response = await fetch("/api/audit/events", {
      credentials: "same-origin",
    });
    if (!response.ok) {
      setMessage("Não foi possível consultar a auditoria.");
      return;
    }
    const payload = (await response.json()) as { events: AuditEvent[] };
    setAuditEvents(payload.events);
  }

  async function loadUsers() {
    const response = await fetch("/api/users", { credentials: "same-origin" });
    if (!response.ok) {
      setMessage("Não foi possível consultar usuários.");
      return;
    }
    const payload = (await response.json()) as { users: ManagedUser[] };
    setManagedUsers(payload.users);
  }

  async function createManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/users/create", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": cookie("csrftoken"),
      },
      body: JSON.stringify(newUser),
    });
    if (!response.ok) {
      setMessage("Não foi possível criar o usuário.");
      return;
    }
    setNewUser({ name: "", email: "", role: "visualizador", password: "" });
    await loadUsers();
  }

  async function loadCompanies() {
    setCompaniesLoading(true);
    setCompaniesError("");
    try {
      const response = await fetch("/api/companies", {
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error("companies");
      const payload = (await response.json()) as { companies: Company[] };
      setCompanies(payload.companies);
      setSelectedCompany(payload.companies[0] ?? null);
      setEditCompany(
        payload.companies[0]
          ? {
              cnpj: payload.companies[0].cnpj,
              legal_name: payload.companies[0].legal_name,
            }
          : { cnpj: "", legal_name: "" },
      );
      if (payload.companies[0]) void loadCertificate(payload.companies[0].id);
    } catch {
      setCompaniesError("Não foi possível carregar empresas. Tente novamente.");
    } finally {
      setCompaniesLoading(false);
    }
  }

  async function loadCertificate(companyId: string) {
    const response = await fetch(`/api/companies/${companyId}/certificate`, {
      credentials: "same-origin",
    });
    if (!response.ok) {
      setCertificate(null);
      return;
    }
    const payload = (await response.json()) as {
      certificate: Certificate | null;
    };
    setCertificate(payload.certificate);
  }

  async function uploadCertificate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCompany || !certificateFile || !certificatePassword) {
      setMessage("Selecione um arquivo .pfx e informe a senha.");
      return;
    }
    const form = new FormData();
    form.append("certificate", certificateFile);
    form.append("password", certificatePassword);
    const response = await fetch(
      `/api/companies/${selectedCompany.id}/certificate/upload`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": cookie("csrftoken") },
        body: form,
      },
    );
    setCertificatePassword("");
    setCertificateFile(null);
    if (!response.ok) {
      setMessage(
        ((await response.json()) as { detail?: string }).detail ??
          "Não foi possível cadastrar o certificado.",
      );
      return;
    }
    setMessage("Certificado validado e armazenado com segurança.");
    await loadCertificate(selectedCompany.id);
    await loadCompanies();
  }

  async function companyAction(
    company: Company,
    action: "activate" | "deactivate",
  ) {
    let body: object = {};
    if (action === "deactivate") {
      if (
        !window.confirm(
          "Deseja desativar esta empresa? O acervo será preservado.",
        )
      )
        return;
      const reason = window.prompt("Informe o motivo da desativação:");
      if (!reason?.trim()) {
        setMessage("A desativação exige um motivo.");
        return;
      }
      body = { confirmed: true, reason };
    }
    const response = await fetch(`/api/companies/${company.id}/${action}`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": cookie("csrftoken"),
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      setMessage("Não foi possível alterar o estado da empresa.");
      return;
    }
    await loadCompanies();
  }

  async function toggleFlow(company: Company, family: "nfe" | "nfse") {
    const state =
      company.flows[family]?.state === "pausado" ? "habilitado" : "pausado";
    const response = await fetch(
      `/api/companies/${company.id}/flows/${family}`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": cookie("csrftoken"),
        },
        body: JSON.stringify({ state }),
      },
    );
    if (!response.ok) {
      setMessage("Só é possível alterar fluxos de empresa ativa.");
      return;
    }
    await loadCompanies();
  }

  async function enrichCompany(company: Company) {
    const response = await fetch(`/api/companies/${company.id}/enrichment`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": cookie("csrftoken") },
    });
    if (!response.ok) {
      setMessage("Não foi possível solicitar o enriquecimento público.");
      return;
    }
    setMessage("Consulta pública registrada; a fonte não é autoritativa.");
    await loadCompanies();
  }

  async function updateCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCompany) return;
    const response = await fetch(`/api/companies/${selectedCompany.id}`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": cookie("csrftoken"),
      },
      body: JSON.stringify({
        ...editCompany,
        version: selectedCompany.version,
      }),
    });
    if (!response.ok) {
      setMessage(
        ((await response.json()) as { detail?: string }).detail ??
          "Não foi possível editar a empresa.",
      );
      return;
    }
    setMessage("Empresa atualizada.");
    await loadCompanies();
  }

  async function createCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/companies/create", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": cookie("csrftoken"),
      },
      body: JSON.stringify(newCompany),
    });
    if (!response.ok) {
      setMessage(
        ((await response.json()) as { detail?: string }).detail ??
          "Não foi possível cadastrar a empresa.",
      );
      return;
    }
    setNewCompany({ cnpj: "", legal_name: "" });
    setMessage("Empresa cadastrada.");
    await loadCompanies();
  }

  async function loadCollections() {
    const response = await fetch("/api/collections", {
      credentials: "same-origin",
    });
    if (!response.ok) {
      setMessage("Não foi possível consultar o estado das coletas.");
      return;
    }
    const payload = (await response.json()) as {
      collections: CollectionCompany[];
    };
    setCollectionCompanies(payload.collections);
  }

  async function requestCollection(
    companyId: string,
    scope: "completa" | "nfe" | "nfse",
  ) {
    const response = await fetch(
      `/api/companies/${companyId}/collection/request`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": cookie("csrftoken"),
        },
        body: JSON.stringify({ scope }),
      },
    );
    if (!response.ok) {
      setMessage(
        ((await response.json()) as { detail?: string }).detail ??
          "A coleta não foi aceita.",
      );
      return;
    }
    setMessage("Solicitação de coleta registrada.");
    await loadCollections();
  }

  async function retryCollection(companyId: string, executionId: string) {
    const response = await fetch(
      `/api/companies/${companyId}/collection/retry/${executionId}`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": cookie("csrftoken") },
      },
    );
    if (!response.ok) {
      setMessage(
        ((await response.json()) as { detail?: string }).detail ??
          "O retry não foi aceito.",
      );
      return;
    }
    setMessage("Retry de coleta registrado.");
    await loadCollections();
  }

  async function loadDocuments() {
    setDocumentsLoading(true);
    setDocumentsError("");
    try {
      const response = await fetch("/api/documents?limit=50", {
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error("documents");
      setDocuments((await response.json()) as DocumentResponse);
    } catch {
      setDocumentsError("Não foi possível consultar os documentos.");
      setDocuments(null);
    } finally {
      setDocumentsLoading(false);
    }
  }

  if (!user)
    return (
      <main lang="pt-BR">
        <h1>NFX INOV</h1>
        <p>{message || "Acesse sua conta."}</p>
        <form onSubmit={submit}>
          <label>
            E-mail
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Senha
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button type="submit">Entrar</button>
        </form>
      </main>
    );
  const canManage = user.role !== "visualizador";
  const isAdmin = user.role === "administrador";
  return (
    <main lang="pt-BR">
      <header>
        <h1>NFX INOV</h1>
        <p>
          {user.name} · {user.role}
        </p>
        <button onClick={() => void signOut()}>Sair</button>
      </header>
      <nav aria-label="Navegação principal">
        <a href="#documentos" onClick={() => void loadDocuments()}>
          Documentos
        </a>
        <a href="#exportacoes">Exportações</a>
        {canManage && (
          <>
            <a href="#empresas" onClick={() => void loadCompanies()}>
              Empresas
            </a>
            <a href="#certificados">Certificados</a>
          </>
        )}
        <a href="#coletas" onClick={() => void loadCollections()}>
          Coletas
        </a>
        {isAdmin && (
          <>
            <a href="#usuarios" onClick={() => void loadUsers()}>
              Usuários
            </a>
            <a href="#auditoria" onClick={() => void loadAudit()}>
              Auditoria
            </a>
          </>
        )}
      </nav>
      <p>{message} · Horários em Brasília · valores em R$.</p>
      <section id="documentos">
        <h2>Documentos</h2>
        <button onClick={() => void loadDocuments()}>Atualizar documentos</button>
        {documentsLoading && <p role="status">Carregando documentos…</p>}
        {documentsError && <p role="alert">{documentsError}</p>}
        {!documentsLoading && !documentsError && documents && (
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
                    <th>Empresa</th>
                    <th>Identidade</th>
                    <th>Família</th>
                    <th>Competência</th>
                    <th>Resultado</th>
                    <th>Evidência</th>
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
      {canManage && (
        <section id="empresas">
          <h2>Empresas</h2>
          <button onClick={() => void loadCompanies()}>
            Atualizar empresas
          </button>
          {companiesLoading && <p role="status">Carregando empresas…</p>}
          {companiesError && <p role="alert">{companiesError}</p>}{" "}
          {!companiesLoading && !companiesError && companies.length === 0 && (
            <p>Nenhuma empresa cadastrada.</p>
          )}
          <form onSubmit={createCompany}>
            <h3>Cadastrar empresa</h3>
            <label>
              CNPJ
              <input
                value={newCompany.cnpj}
                onChange={(event) =>
                  setNewCompany({ ...newCompany, cnpj: event.target.value })
                }
                required
              />
            </label>
            <label>
              Razão social
              <input
                value={newCompany.legal_name}
                onChange={(event) =>
                  setNewCompany({
                    ...newCompany,
                    legal_name: event.target.value,
                  })
                }
                required
              />
            </label>
            <button type="submit">Cadastrar</button>
          </form>
          <table>
            <thead>
              <tr>
                <th>Razão social</th>
                <th>CNPJ</th>
                <th>Estado</th>
                <th>Fluxos</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((company) => (
                <tr
                  key={company.id}
                  onClick={() => {
                    setSelectedCompany(company);
                    setEditCompany({
                      cnpj: company.cnpj,
                      legal_name: company.legal_name,
                    });
                    void loadCertificate(company.id);
                  }}
                >
                  <td>{company.legal_name}</td>
                  <td>{company.cnpj}</td>
                  <td>{statusLabel(company.status)}</td>
                  <td>
                    NF-e: {company.flows.nfe?.state} · NFS-e:{" "}
                    {company.flows.nfse?.state}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {selectedCompany && (
            <article>
              <h3>Detalhe: {selectedCompany.legal_name}</h3>
              <form
                onSubmit={updateCompany}
              >
                <label>
                  CNPJ
                  <input
                    value={editCompany.cnpj}
                    onChange={(event) =>
                      setEditCompany({ ...editCompany, cnpj: event.target.value })
                    }
                    required
                  />
                </label>
                <label>
                  Razão social
                  <input
                    value={editCompany.legal_name}
                    onChange={(event) =>
                      setEditCompany({
                        ...editCompany,
                        legal_name: event.target.value,
                      })
                    }
                  />
                </label>
                <button type="submit">Salvar empresa</button>
              </form>
              <p>
                CNPJ {selectedCompany.cnpj} ·{" "}
                {statusLabel(selectedCompany.status)}
              </p>
              {certificate ? (
                <p>Certificado: {certificate.status}</p>
              ) : (
                <p>Nenhum certificado corrente.</p>
              )}
              {selectedCompany.status === "ativa" && (
                <p>
                  <button onClick={() => void toggleFlow(selectedCompany, "nfe")}>
                    NF-e {selectedCompany.flows.nfe?.state === "pausado" ? "habilitar" : "pausar"}
                  </button>{" "}
                  <button onClick={() => void toggleFlow(selectedCompany, "nfse")}>
                    NFS-e {selectedCompany.flows.nfse?.state === "pausado" ? "habilitar" : "pausar"}
                  </button>
                </p>
              )}
              <button onClick={() => void companyAction(selectedCompany, selectedCompany.status === "ativa" ? "deactivate" : "activate")}>
                {selectedCompany.status === "ativa" ? "Desativar" : "Ativar"}
              </button>{" "}
              <button onClick={() => void enrichCompany(selectedCompany)}>Atualizar dados públicos</button>
              <form onSubmit={uploadCertificate}>
                <label>
                  Arquivo .pfx
                  <input type="file" accept=".pfx,application/x-pkcs12" onChange={(event) => setCertificateFile(event.target.files?.[0] ?? null)} required />
                </label>
                <label>
                  Senha do certificado
                  <input type="password" value={certificatePassword} onChange={(event) => setCertificatePassword(event.target.value)} required />
                </label>
                <button type="submit">Validar e substituir</button>
              </form>
            </article>
          )}
        </section>
      )}
      {
        <section id="coletas">
          <h2>Coletas</h2>
          <button onClick={() => void loadCollections()}>
            Atualizar coletas
          </button>
          {collectionCompanies.length === 0 && (
            <p>Nenhuma empresa disponível.</p>
          )}
          {collectionCompanies.map((item) => (
            <article key={item.company_id}>
              <h3>{item.legal_name}</h3>
              {canManage && (
                <button onClick={() => void requestCollection(item.company_id, "completa")}>
                  Solicitar coleta completa
                </button>
              )}
              {item.flows.map((flow) => (
                <div key={flow.family}>
                  <strong>
                    {flow.family === "nfe" ? "NF-e" : "NFS-e"}:{" "}
                    {collectionLabel(flow.collection_state)}
                  </strong>
                  <p>
                    Tentativa: {flow.last_attempt_at ?? "—"} · Sucesso:{" "}
                    {flow.last_success_at ?? "—"}
                  </p>
                  {flow.safe_error && (
                    <p role="status">Correção: {flow.safe_error}</p>
                  )}
                  {canManage && (
                    <>
                      <button
                        disabled={
                          flow.collection_state !== "idle" &&
                          flow.active_execution !== null
                        }
                        onClick={() =>
                          void requestCollection(item.company_id, flow.family)
                        }
                      >
                        Solicitar {flow.family}
                      </button>
                      {flow.latest_execution &&
                        ["failed", "partial"].includes(
                          flow.latest_execution.state,
                        ) && (
                          <button
                            onClick={() =>
                              void retryCollection(
                                item.company_id,
                                flow.latest_execution?.id ?? "",
                              )
                            }
                          >
                            Retry
                          </button>
                        )}
                    </>
                  )}
                </div>
              ))}
            </article>
          ))}
        </section>
      }
      {isAdmin && (
        <section id="usuarios">
          <h2>Usuários</h2>
          <button onClick={() => void loadUsers()}>Atualizar usuários</button>
          <form onSubmit={createManagedUser}>
            <label>
              Nome
              <input
                value={newUser.name}
                onChange={(event) =>
                  setNewUser({ ...newUser, name: event.target.value })
                }
                required
              />
            </label>
            <label>
              E-mail
              <input
                type="email"
                value={newUser.email}
                onChange={(event) =>
                  setNewUser({ ...newUser, email: event.target.value })
                }
                required
              />
            </label>
            <label>
              Papel
              <select
                value={newUser.role}
                onChange={(event) =>
                  setNewUser({ ...newUser, role: event.target.value })
                }
              >
                <option value="administrador">Administrador</option>
                <option value="operador">Operador</option>
                <option value="visualizador">Visualizador</option>
              </select>
            </label>
            <label>
              Senha inicial
              <input
                type="password"
                value={newUser.password}
                onChange={(event) =>
                  setNewUser({ ...newUser, password: event.target.value })
                }
                required
              />
            </label>
            <button type="submit">Criar usuário</button>
          </form>
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Papel</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {managedUsers.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.email}</td>
                  <td>{item.role}</td>
                  <td>{item.active ? "Ativo" : "Desativado"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {isAdmin && (
        <section id="auditoria">
          <h2>Auditoria</h2>
          <button onClick={() => void loadAudit()}>Atualizar auditoria</button>
          <table>
            <thead>
              <tr>
                <th>Data/hora</th>
                <th>Ação</th>
                <th>Entidade</th>
                <th>Resultado</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              {auditEvents.map((item) => (
                <tr key={item.id}>
                  <td>{item.occurred_at}</td>
                  <td>{item.action}</td>
                  <td>
                    {item.entity_type} · {item.entity_id}
                  </td>
                  <td>{item.result}</td>
                  <td>{item.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}

const root = document.getElementById("root");
if (!root) throw new Error("root element is required");
createRoot(root).render(<App />);
