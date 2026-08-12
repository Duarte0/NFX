import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
import { Badge, Button, DataTable, Field, Panel } from "../../shared/ui/primitives";
import { listAuditEvents } from "./api";
import { AuditEvent, AuditFilters, AuditResponse } from "./types";

const actionLabels: Record<string, string> = {
  "auth.login": "Login concluído",
  "auth.login_failed": "Falha de login",
  "auth.logout": "Logout",
  "user.create": "Usuário criado",
  "user.update": "Usuário atualizado",
  "user.role_change": "Papel alterado",
  "user.password_reset": "Senha redefinida",
  "user.password_change": "Senha própria alterada",
  "user.activate": "Usuário ativado",
  "user.deactivate": "Usuário desativado",
  "retention.list": "Retenção consultada",
  "retention.detail": "Detalhe de retenção consultado",
  "retention.preview": "Prévia de retenção gerada",
  "document.delete": "Exclusão solicitada",
  "document.delete.denied": "Exclusão bloqueada",
  "health.read": "Saúde consultada",
};

const entityLabels: Record<string, string> = {
  user: "Usuário",
  document: "Documento fiscal",
  retention: "Retenção",
  audit: "Auditoria",
  health: "Saúde operacional",
  session: "Sessão",
};

const resultLabels: Record<string, string> = {
  success: "Concluído",
  empty: "Resultado vazio válido",
  denied: "Negado",
  blocked: "Bloqueado",
  failure: "Falhou",
  unavailable: "Indisponível",
  not_found: "Não encontrado",
  stale: "Prévia desatualizada",
  requested: "Solicitado",
  recovery_requested: "Recuperação solicitada",
  completed: "Concluído",
  failed: "Falhou",
  recovery_required: "Recuperação necessária",
};

const filterOptions = {
  action: [
    ["user.create", "Usuário criado"], ["user.update", "Usuário atualizado"], ["user.role_change", "Papel alterado"],
    ["user.password_reset", "Senha redefinida"], ["user.activate", "Usuário ativado"], ["user.deactivate", "Usuário desativado"],
    ["retention.preview", "Prévia de retenção"], ["document.delete", "Exclusão solicitada"], ["document.delete.denied", "Exclusão bloqueada"],
  ],
  entity_type: [["user", "Usuário"], ["document", "Documento fiscal"], ["retention", "Retenção"], ["health", "Saúde operacional"]],
  result: [["success", "Concluído"], ["empty", "Vazio válido"], ["denied", "Negado"], ["blocked", "Bloqueado"], ["failure", "Falhou"], ["stale", "Desatualizado"]],
} as const;

export type AuditPresentationProps = {
  result: AuditResponse | null;
  filters: AuditFilters;
  loading: boolean;
  stale: boolean;
  error: string;
  onReload: () => void;
  onRetry: () => void;
  onFilterChange: (filters: AuditFilters) => void;
  onNextPage: () => void;
};

export function auditActionLabel(action: string): string {
  return actionLabels[action] ?? "Ação administrativa registrada";
}

export function auditEntityLabel(entity: string): string {
  return entityLabels[entity] ?? "Entidade administrativa";
}

export function auditResultLabel(result: string): string {
  return resultLabels[result] ?? "Resultado informado pelo servidor";
}

function eventDateLabel(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return "Data não informada";
  const iso = parsed.toISOString();
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)} ${iso.slice(11, 19)} UTC`;
}

function resultVariant(result: string): "success" | "warning" | "danger" | "neutral" {
  if (["success", "completed", "requested", "recovery_requested"].includes(result)) return "success";
  if (["empty", "stale", "recovery_required"].includes(result)) return "warning";
  if (["denied", "blocked", "failure", "failed", "unavailable"].includes(result)) return "danger";
  return "neutral";
}

function safeReason(reason: string): string {
  if (!reason) return "Sem motivo informado";
  if (/(?:password|secret|token|hash|xml|pdf|pfx|object|path|exception|traceback|\/|\\)/i.test(reason)) {
    return "Motivo redigido por segurança";
  }
  return reason.length > 180 ? `${reason.slice(0, 177)}…` : reason;
}

function safeContext(context: Record<string, unknown> | undefined): string {
  if (!context) return "";
  const allowed: string[] = [];
  if (typeof context.count === "number") allowed.push(`Quantidade informada: ${context.count}`);
  if (typeof context.scope === "string") allowed.push("Escopo limitado");
  if (typeof context.rule_version === "string") allowed.push("Regra versionada");
  if (typeof context.latency_ms === "number") allowed.push(`Latência: ${Math.round(context.latency_ms)} ms`);
  return allowed.join(" · ");
}

function actorLabel(event: AuditEvent): string {
  if (event.actor_role === "administrador") return "Administrador autenticado";
  if (event.actor_role === "operador") return "Operador autenticado";
  if (event.actor_role === "visualizador") return "Visualizador autenticado";
  return event.actor_id ? "Ator autenticado" : "Sistema/ator não informado";
}

export function AuditPresentation({ result, filters, loading, stale, error, onReload, onRetry, onFilterChange, onNextPage }: AuditPresentationProps) {
  return (
    <section id="auditoria" className="feature-section">
      <div className="feature-heading"><div><p className="feature-eyebrow">Administração</p><h2>Auditoria</h2><p className="feature-intro">Fluxo append-only consultado com integridade e metadados redigidos.</p></div><Button variant="secondary" onClick={onReload} disabled={loading}>{loading ? "Atualizando…" : "Atualizar auditoria"}</Button></div>
      {loading && <Feedback state="loading" message="Carregando auditoria…" />}
      {stale && <div className="feature-stale" role="status"><Badge variant="warning">Leitura desatualizada</Badge><span>A última página segura permanece visível enquanto os filtros são revalidados.</span></div>}
      {error && <div className="feature-actions"><Feedback state="error" message={error} /><Button variant="secondary" onClick={onRetry}>Tentar novamente</Button></div>}
      <Panel title="Filtros da auditoria" className="feature-panel">
        <div className="feature-filter-form">
          <Field id="auditoria-ator" label="Ator"><input value={filters.actor_id} maxLength={128} placeholder="ID fornecido pelo owner" onChange={(event) => onFilterChange({ ...filters, actor_id: event.target.value, cursor: "" })} /></Field>
          <Field id="auditoria-acao" label="Ação"><select value={filters.action} onChange={(event) => onFilterChange({ ...filters, action: event.target.value, cursor: "" })}><option value="">Todas</option>{filterOptions.action.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
          <Field id="auditoria-entidade" label="Entidade"><select value={filters.entity_type} onChange={(event) => onFilterChange({ ...filters, entity_type: event.target.value, cursor: "" })}><option value="">Todas</option>{filterOptions.entity_type.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
          <Field id="auditoria-resultado" label="Resultado"><select value={filters.result} onChange={(event) => onFilterChange({ ...filters, result: event.target.value, cursor: "" })}><option value="">Todos</option>{filterOptions.result.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
        </div>
      </Panel>
      {result && <Panel title="Eventos registrados" className="feature-panel">
        <div className="feature-summary"><Badge variant={result.integrity ? "success" : "danger"}>{result.integrity ? "Integridade verificada" : "Falha de integridade"}</Badge><span>A cadeia histórica não é editável pela interface.</span></div>
        <div className="feature-pagination" role="status"><span>{result.events.length} evento(s) nesta página; cursor limitado pelo servidor.</span>{result.next_cursor !== null && <Button variant="secondary" onClick={onNextPage} disabled={loading}>Próxima página</Button>}</div>
        {result.events.length === 0 ? <Feedback state="empty" message="Nenhum evento corresponde aos filtros informados." /> : <DataTable caption="Eventos de auditoria" className="admin-table">
          <thead><tr><th>Data UTC</th><th>Ação</th><th>Entidade</th><th>Ator</th><th>Resultado</th><th>Motivo e contexto</th></tr></thead>
          <tbody>{result.events.map((event) => <tr key={event.id}>
            <td><time dateTime={event.occurred_at}>{eventDateLabel(event.occurred_at)}</time></td>
            <td>{auditActionLabel(event.action)}</td>
            <td>{auditEntityLabel(event.entity_type)}</td>
            <td>{actorLabel(event)}</td>
            <td><Badge variant={resultVariant(event.result)}>{auditResultLabel(event.result)}</Badge></td>
            <td>{safeReason(event.reason)}{safeContext(event.context) && <><br /><small>{safeContext(event.context)}</small></>}</td>
          </tr>)}</tbody>
        </DataTable>}
      </Panel>}
    </section>
  );
}

export function auditFiltersFromLocation(): AuditFilters {
  const query = new URLSearchParams(window.location.search);
  const action = query.get("action") ?? "";
  const entityType = query.get("entity_type") ?? "";
  const result = query.get("result") ?? "";
  const allowedAction = filterOptions.action.some(([value]) => value === action) ? action : "";
  const allowedEntity = filterOptions.entity_type.some(([value]) => value === entityType) ? entityType : "";
  const allowedResult = filterOptions.result.some(([value]) => value === result) ? result : "";
  return { actor_id: (query.get("actor_id") ?? "").slice(0, 128), action: allowedAction, entity_type: allowedEntity, result: allowedResult, cursor: query.get("cursor") ?? "" };
}

function auditQuery(filters: AuditFilters): URLSearchParams {
  const query = new URLSearchParams(window.location.search);
  for (const key of ["actor_id", "action", "entity_type", "result", "cursor", "limit"]) query.delete(key);
  for (const [key, value] of Object.entries(filters)) if (value) query.set(key, value);
  query.set("limit", "50");
  return query;
}

export function AuditSection({ loadSignal, notify }: { loadSignal: number; notify: (message: string) => void }) {
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [filters, setFilters] = useState<AuditFilters>(() => auditFiltersFromLocation());
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const resultRef = useRef<AuditResponse | null>(null);

  const loadAudit = useCallback(async (requestedFilters: AuditFilters = auditFiltersFromLocation()) => {
    const requestId = ++sequence.current;
    setLoading(true);
    setError("");
    setStale(resultRef.current !== null);
    try {
      const query = new URLSearchParams();
      for (const [key, value] of Object.entries(requestedFilters)) if (value) query.set(key, value);
      const payload = await listAuditEvents(query);
      if (requestId !== sequence.current) return;
      resultRef.current = payload;
      setResult(payload);
      setStale(false);
    } catch (caught: unknown) {
      if (requestId !== sequence.current) return;
      setError(caught instanceof ApiError && caught.status === 403 ? "A sessão sem permissão não pode consultar a auditoria." : "Não foi possível consultar a auditoria. A última página segura continua disponível.");
      setStale(resultRef.current !== null);
      notify("Não foi possível consultar a auditoria.");
    } finally {
      if (requestId === sequence.current) setLoading(false);
    }
  }, [notify]);

  useEffect(() => { if (loadSignal > 0 || window.location.hash === "#auditoria" || auditFiltersFromLocation().toString()) void loadAudit(); }, [loadAudit, loadSignal]);
  useEffect(() => {
    const loadLocation = () => { if (window.location.hash === "#auditoria" || auditFiltersFromLocation().toString()) { const next = auditFiltersFromLocation(); setFilters(next); void loadAudit(next); } };
    window.addEventListener("hashchange", loadLocation); window.addEventListener("popstate", loadLocation);
    return () => { window.removeEventListener("hashchange", loadLocation); window.removeEventListener("popstate", loadLocation); };
  }, [loadAudit]);

  function changeFilters(next: AuditFilters) {
    setFilters(next);
    const query = auditQuery(next);
    window.history.pushState(null, "", `${window.location.pathname}?${query.toString()}${window.location.hash || "#auditoria"}`);
    void loadAudit(next);
  }

  function nextPage() { if (result?.next_cursor !== null && result?.next_cursor !== undefined) changeFilters({ ...filters, cursor: String(result.next_cursor) }); }

  return <AuditPresentation result={result} filters={filters} loading={loading} stale={stale} error={error} onReload={() => void loadAudit(filters)} onRetry={() => void loadAudit(filters)} onFilterChange={changeFilters} onNextPage={nextPage} />;
}
