import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type User = { id: string; name: string; role: "administrador" | "operador" | "visualizador" };
type AuditEvent = { id: string; sequence: number; occurred_at: string; action: string; entity_type: string; entity_id: string; result: string; reason: string; actor_id: string | null };

function cookie(name: string): string {
  return document.cookie.split("; ").find((part) => part.startsWith(`${name}=`))?.split("=")[1] ?? "";
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);

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

  if (!user) return <main lang="pt-BR"><h1>NFX INOV</h1><p>{message || "Acesse sua conta."}</p><form onSubmit={submit}><label>E-mail<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Senha<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label><button type="submit">Entrar</button></form></main>;
  const canManage = user.role !== "visualizador";
  const isAdmin = user.role === "administrador";
  return <main lang="pt-BR"><header><h1>NFX INOV</h1><p>{user.name} · {user.role}</p><button onClick={() => void signOut()}>Sair</button></header><nav aria-label="Navegação principal"><a href="#documentos">Documentos</a><a href="#exportacoes">Exportações</a>{canManage && <><a href="#empresas">Empresas</a><a href="#certificados">Certificados</a><a href="#coletas">Coletas</a></>}{isAdmin && <a href="#auditoria" onClick={() => void loadAudit()}>Auditoria</a>}</nav><p>Horários em Brasília · valores em R$.</p>{isAdmin && <section id="auditoria"><h2>Auditoria</h2><button onClick={() => void loadAudit()}>Atualizar auditoria</button><table><thead><tr><th>Data/hora</th><th>Ação</th><th>Entidade</th><th>Resultado</th><th>Motivo</th></tr></thead><tbody>{auditEvents.map((item) => <tr key={item.id}><td>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium", timeZone: "America/Sao_Paulo" }).format(new Date(item.occurred_at))}</td><td>{item.action}</td><td>{item.entity_type}{item.entity_id ? ` · ${item.entity_id}` : ""}</td><td>{item.result}</td><td>{item.reason}</td></tr>)}</tbody></table></section>}</main>;
}

const root = document.getElementById("root");
if (!root) throw new Error("root element is required");

createRoot(root).render(<App />);
