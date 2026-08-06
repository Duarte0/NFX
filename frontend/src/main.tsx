import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type User = { id: string; name: string; role: "administrador" | "operador" | "visualizador" };
type AuditEvent = { id: string; sequence: number; occurred_at: string; action: string; entity_type: string; entity_id: string; result: string; reason: string; actor_id: string | null };
type ManagedUser = User & { email: string; active: boolean; version: number };

function cookie(name: string): string {
  return document.cookie.split("; ").find((part) => part.startsWith(`${name}=`))?.split("=")[1] ?? "";
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [newUser, setNewUser] = useState({ name: "", email: "", role: "visualizador", password: "" });

  useEffect(() => {
    void fetch("/api/auth/csrf", { credentials: "same-origin" })
      .then(() => fetch("/api/auth/session", { credentials: "same-origin" }))
      .then(async (response) => (response.ok ? (response.json() as Promise<{ user: User }>) : null))
      .then((payload) => setUser(payload?.user ?? null));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setMessage("Não foi possível iniciar a sessão. Verifique suas credenciais.");
      return;
    }
    const payload = (await response.json()) as { user: User };
    setPassword("");
    setMessage("");
    setUser(payload.user);
  }

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": cookie("csrftoken") } });
    setUser(null);
    setMessage("Sessão encerrada.");
  }

  async function loadAudit() {
    const response = await fetch("/api/audit/events", { credentials: "same-origin" });
    if (!response.ok) { setMessage("Não foi possível consultar a auditoria."); return; }
    const payload = (await response.json()) as { events: AuditEvent[] };
    setAuditEvents(payload.events);
  }

  async function loadUsers() {
    const response = await fetch("/api/users", { credentials: "same-origin" });
    if (!response.ok) { setMessage("Não foi possível consultar usuários."); return; }
    const payload = (await response.json()) as { users: ManagedUser[] };
    setManagedUsers(payload.users);
  }

  async function createManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/users/create", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") }, body: JSON.stringify(newUser) });
    if (!response.ok) { setMessage("Não foi possível criar o usuário."); return; }
    setNewUser({ name: "", email: "", role: "visualizador", password: "" });
    await loadUsers();
  }

  if (!user) return <main lang="pt-BR"><h1>NFX INOV</h1><p>{message || "Acesse sua conta."}</p><form onSubmit={submit}><label>E-mail<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Senha<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label><button type="submit">Entrar</button></form></main>;
  const canManage = user.role !== "visualizador";
  const isAdmin = user.role === "administrador";
  return <main lang="pt-BR"><header><h1>NFX INOV</h1><p>{user.name} · {user.role}</p><button onClick={() => void signOut()}>Sair</button></header><nav aria-label="Navegação principal"><a href="#documentos">Documentos</a><a href="#exportacoes">Exportações</a>{canManage && <><a href="#empresas">Empresas</a><a href="#certificados">Certificados</a><a href="#coletas">Coletas</a></>}{isAdmin && <><a href="#usuarios" onClick={() => void loadUsers()}>Usuários</a><a href="#auditoria" onClick={() => void loadAudit()}>Auditoria</a></>}</nav><p>Horários em Brasília · valores em R$.</p>{isAdmin && <section id="usuarios"><h2>Usuários</h2><button onClick={() => void loadUsers()}>Atualizar usuários</button><form onSubmit={createManagedUser}><label>Nome<input value={newUser.name} onChange={(event) => setNewUser({ ...newUser, name: event.target.value })} required /></label><label>E-mail<input type="email" value={newUser.email} onChange={(event) => setNewUser({ ...newUser, email: event.target.value })} required /></label><label>Papel<select value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value })}><option value="administrador">Administrador</option><option value="operador">Operador</option><option value="visualizador">Visualizador</option></select></label><label>Senha inicial<input type="password" value={newUser.password} onChange={(event) => setNewUser({ ...newUser, password: event.target.value })} required /></label><button type="submit">Criar usuário</button></form><table><thead><tr><th>Nome</th><th>E-mail</th><th>Papel</th><th>Estado</th></tr></thead><tbody>{managedUsers.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.email}</td><td>{item.role}</td><td>{item.active ? "Ativo" : "Desativado"}</td></tr>)}</tbody></table></section>}{isAdmin && <section id="auditoria"><h2>Auditoria</h2><button onClick={() => void loadAudit()}>Atualizar auditoria</button><table><thead><tr><th>Data/hora</th><th>Ação</th><th>Entidade</th><th>Resultado</th><th>Motivo</th></tr></thead><tbody>{auditEvents.map((item) => <tr key={item.id}><td>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium", timeZone: "America/Sao_Paulo" }).format(new Date(item.occurred_at))}</td><td>{item.action}</td><td>{item.entity_type}{item.entity_id ? ` · ${item.entity_id}` : ""}</td><td>{item.result}</td><td>{item.reason}</td></tr>)}</tbody></table></section>}</main>;
}

const root = document.getElementById("root");
if (!root) throw new Error("root element is required");

createRoot(root).render(<App />);
