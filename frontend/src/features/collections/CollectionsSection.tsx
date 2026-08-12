import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback, FeedbackState } from "../../shared/ui/Feedback";
import { Badge, Button, Field, Panel } from "../../shared/ui/primitives";
import {
  listCollectionExecutions,
  listCollections,
  requestCollection as requestCollectionApi,
  retryCollection as retryCollectionApi,
} from "./api";
import {
  CollectionCompany,
  CollectionExecutionFilter,
  CollectionExecutionResponse,
  CollectionExecutionSummary,
} from "./types";

export type CollectionsPresentationProps = {
  companies: CollectionCompany[];
  executionResult: CollectionExecutionResponse | null;
  executionFilter: CollectionExecutionFilter | null;
  executionLoading: boolean;
  executionStale: boolean;
  collectionStale: boolean;
  error: string;
  executionError: "unavailable" | "invalid" | "degraded" | "";
  canManage: boolean;
  actionBusy: string;
  onReload: () => void;
  onRetry: () => void;
  onFilterChange: (filter: CollectionExecutionFilter) => void;
  onRequest: (companyId: string, scope: "completa" | "nfe" | "nfse") => void;
  onRetryCollection: (companyId: string, executionId: string) => void;
  collectionLoading?: boolean;
};

export function collectionStateLabel(state: string): string {
  return {
    idle: "Coleta não iniciada",
    queued: "Coleta na fila",
    running: "Coleta em execução",
    concluded: "Coleta concluída",
    empty: "Consulta válida sem documentos",
    partial: "Coleta parcial",
    retrying: "Nova tentativa de coleta agendada",
    cooldown: "Coleta em cooldown",
    blocked: "Coleta bloqueada",
    failed: "Falha na coleta",
  }[state] ?? "Estado da coleta informado pelo servidor";
}

export function coverageLabel(status: string | null): string {
  if (status === null) return "Cobertura ADN não consultada";
  return {
    available: "Cobertura ADN disponível",
    none: "Cobertura ADN ausente",
    unknown: "Cobertura ADN desconhecida",
    error: "Cobertura ADN indisponível",
    unavailable: "Cobertura ADN indisponível",
    degraded: "Cobertura ADN degradada",
  }[status] ?? "Estado da cobertura ADN informado pelo servidor";
}

function collectionVariant(state: string): "success" | "warning" | "danger" | "info" | "neutral" {
  if (["concluded", "empty"].includes(state)) return "success";
  if (["partial", "cooldown", "retrying"].includes(state)) return "warning";
  if (["blocked", "failed"].includes(state)) return "danger";
  if (["queued", "running"].includes(state)) return "info";
  return "neutral";
}

function coverageVariant(status: string | null): "success" | "warning" | "danger" | "neutral" {
  if (status === "available") return "success";
  if (status === "none" || status === "unknown" || status === null) return "neutral";
  return "warning";
}

function executionStateLabel(state: string): string {
  return {
    recent: "Todas as execuções",
    running: "Execuções em andamento",
    failed: "Execuções com falha",
    blocked: "Execuções bloqueadas",
    partial: "Execuções parciais",
  }[state] ?? "Filtro de execuções informado pelo servidor";
}

function executionItemLabel(execution: CollectionExecutionSummary): string {
  const state = {
    queued: "Execução na fila",
    running: "Execução em andamento",
    concluded: "Execução concluída",
    empty: "Execução válida sem documentos",
    partial: "Execução parcial",
    retrying: "Execução em nova tentativa",
    cooldown: "Execução em cooldown",
    blocked: "Execução bloqueada",
    failed: "Execução com falha",
  }[execution.state] ?? "Estado da execução informado pelo servidor";
  if (execution.safe_error === "partial_result") return `${state}; resultado parcial`;
  if (execution.safe_error === "temporary_failure") return `${state}; nova tentativa permitida`;
  if (execution.safe_error === "permanent_failure") return `${state}; bloqueio de política`;
  return state;
}

function safeFlowMessage(value: string): string {
  return {
    temporary_failure: "A fonte apresentou uma falha transitória.",
    permanent_failure: "A política do servidor bloqueou a coleta.",
    partial_result: "Parte do resultado foi processada; uma nova tentativa pode ser necessária.",
    official_cooldown: "A fonte determinou um intervalo antes da próxima tentativa.",
    retry_exhausted: "As tentativas permitidas foram esgotadas; revise a condição indicada.",
  }[value] ?? "O servidor informou uma condição de atenção para esta coleta.";
}

function executionErrorState(error: CollectionsPresentationProps["executionError"]): FeedbackState {
  if (error === "invalid") return "error";
  if (error === "degraded") return "degraded";
  return "unavailable";
}

function staleNotice(stale: boolean) {
  return stale ? (
    <div className="feature-stale" role="status">
      <Badge variant="warning">Leitura desatualizada</Badge>
      <span>A última leitura segura permanece visível enquanto a atualização termina.</span>
    </div>
  ) : null;
}

export function CollectionsPresentation({
  companies,
  executionResult,
  executionFilter,
  executionLoading,
  executionStale,
  collectionStale,
  error,
  executionError,
  canManage,
  actionBusy,
  onReload,
  onRetry,
  onFilterChange,
  onRequest,
  onRetryCollection,
  collectionLoading = false,
}: CollectionsPresentationProps) {
  function submitFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    onFilterChange({
      from: String(values.get("from") ?? ""),
      to: String(values.get("to") ?? ""),
      state: String(values.get("state") ?? ""),
    });
  }

  return (
    <section id="coletas" aria-labelledby="coletas-title" className="feature-section">
      <div className="feature-heading">
        <div>
          <p className="feature-eyebrow">Cobertura e execução</p>
          <h2 id="coletas-title">Coletas</h2>
          <p className="feature-intro">Cada fluxo conserva seu estado durável, cobertura e possibilidade de recuperação.</p>
        </div>
        <Button variant="secondary" onClick={onReload} disabled={collectionLoading || executionLoading}>Atualizar coletas</Button>
      </div>
      {collectionLoading && <Feedback state="loading" message="Carregando estado das coletas…" />}
      {staleNotice(collectionStale)}
      {error && <Feedback state="unavailable" message={error} />}
      {error && <Button variant="secondary" onClick={onRetry} disabled={collectionLoading}>Tentar novamente</Button>}
      <Panel as="section" title="Execuções filtradas" className="feature-panel collection-executions">
        <form key={`${executionFilter?.from ?? ""}-${executionFilter?.to ?? ""}-${executionFilter?.state ?? ""}`} className="feature-filter-form" onSubmit={submitFilter}>
          <Field id="collection-from" label="De"><input type="date" name="from" defaultValue={executionFilter?.from ?? ""} /></Field>
          <Field id="collection-to" label="Até"><input type="date" name="to" defaultValue={executionFilter?.to ?? ""} /></Field>
          <Field id="collection-state" label="Estado da execução">
            <select name="state" defaultValue={executionFilter?.state ?? ""}>
              <option value="">Todas as execuções</option>
              <option value="running">Execuções em andamento</option>
              <option value="failed">Execuções com falha</option>
              <option value="blocked">Execuções bloqueadas</option>
              <option value="partial">Execuções parciais</option>
            </select>
          </Field>
          <Button type="submit" variant="secondary">Aplicar filtro</Button>
        </form>
        {executionFilter && <p className="feature-context">Consulta: {executionStateLabel(executionFilter.state)} · {executionFilter.from} até {executionFilter.to} · fronteira [from,to)</p>}
        {executionLoading && <Feedback state="loading" message="Carregando execuções filtradas…" />}
        {staleNotice(executionStale)}
        {executionError === "invalid" && <Feedback state={executionErrorState(executionError)} message="O filtro de execuções é inválido." />}
        {executionError === "unavailable" && <Feedback state={executionErrorState(executionError)} message="As execuções filtradas estão indisponíveis." />}
        {executionError === "degraded" && <Feedback state={executionErrorState(executionError)} message="A consulta de execuções está degradada." />}
        {executionError && <Button variant="secondary" onClick={onRetry} disabled={executionLoading}>Tentar novamente</Button>}
        {executionResult && (
          <>
            <div className="feature-summary" role="status"><span>Total reconciliado: {executionResult.total}</span><span>Limite: {executionResult.limit}</span><span>{executionResult.truncated ? "Há mais resultados" : "Todos os resultados desta consulta foram apresentados"}</span></div>
            {executionResult.executions.length === 0 ? <Feedback state="empty" message="Nenhuma execução encontrada para este filtro." /> : (
              <ul className="execution-list">
                {executionResult.executions.map((execution) => <li key={execution.id}><strong>{execution.company_name}</strong><span>{execution.family === "nfe" ? "NF-e" : execution.family === "nfse" ? "NFS-e" : "Família informada"}</span><Badge variant={collectionVariant(execution.state)}>{executionItemLabel(execution)}</Badge><time dateTime={execution.created_at}>{execution.created_at}</time></li>)}
              </ul>
            )}
          </>
        )}
        {!executionFilter && <Feedback state="empty" message="Escolha um período ou estado para consultar execuções históricas." />}
      </Panel>
      {companies.length === 0 && !error && <Feedback state="empty" message="Nenhuma empresa disponível para acompanhar coletas." />}
      <div className="collection-company-grid">
        {companies.map((item) => (
          <Panel as="article" key={item.company_id} title={item.legal_name} className="feature-panel collection-company">
            <div className="feature-summary"><Badge variant={item.status === "ativa" ? "success" : item.status === "desativada" ? "danger" : "neutral"}>{item.status === "ativa" ? "Empresa ativa" : item.status === "desativada" ? "Empresa desativada" : "Empresa cadastrada"}</Badge></div>
            {canManage && <Button onClick={() => onRequest(item.company_id, "completa")} disabled={Boolean(actionBusy)}>Solicitar coleta completa</Button>}
            <div className="collection-flow-grid">
              {item.flows.map((flow) => (
                <Panel as="section" key={flow.family} title={flow.family === "nfe" ? "NF-e" : "NFS-e"} className="feature-subpanel">
                  <Badge variant={collectionVariant(flow.collection_state)}>{collectionStateLabel(flow.collection_state)}</Badge>
                  <Badge variant={flow.flow_state === "habilitado" ? "success" : "warning"}>{flow.flow_state === "habilitado" ? "Fluxo habilitado" : flow.flow_state === "pausado" ? "Fluxo pausado" : "Estado do fluxo informado pelo servidor"}</Badge>
                  {flow.progress.total > 0 && <p>Progresso informado: {flow.progress.current} de {flow.progress.total}</p>}
                  <p>Tentativa: {flow.last_attempt_at ?? "Não informada"} · Sucesso: {flow.last_success_at ?? "Não informado"}</p>
                  {flow.family === "nfse" && <div className="feature-enrichment"><Badge variant={coverageVariant(flow.coverage?.status ?? null)}>{coverageLabel(flow.coverage?.status ?? null)}</Badge>{flow.coverage && <span>Verificada em: {flow.coverage.verified_at}</span>}</div>}
                  {flow.safe_error && <Feedback state={flow.collection_state === "blocked" ? "blocked" : "degraded"} message={safeFlowMessage(flow.safe_error)} />}
                  {flow.blocked_reason && flow.collection_state === "blocked" && <Feedback state="blocked" message="A coleta está bloqueada por uma política do servidor." />}
                  {flow.active_execution && <p role="status">Execução atual: {executionItemLabel({ ...flow.active_execution, company_id: item.company_id, company_name: item.legal_name, family: flow.family, requested_scope: flow.family, outcome: "unknown", recovery: "none", created_at: "", started_at: null, finished_at: null })}</p>}
                  {flow.latest_execution && <p role="status">Última execução: {executionItemLabel({ ...flow.latest_execution, company_id: item.company_id, company_name: item.legal_name, family: flow.family, requested_scope: flow.family, outcome: "unknown", recovery: "none", created_at: "", started_at: null, finished_at: null })}</p>}
                  {canManage && <div className="feature-actions"><Button variant="secondary" onClick={() => onRequest(item.company_id, flow.family)} disabled={Boolean(actionBusy) || (flow.collection_state !== "idle" && flow.active_execution !== null)}>Solicitar {flow.family === "nfe" ? "NF-e" : "NFS-e"}</Button>{flow.latest_execution && ["failed", "partial"].includes(flow.latest_execution.state) && <Button variant="secondary" onClick={() => onRetryCollection(item.company_id, flow.latest_execution?.id ?? "")} disabled={Boolean(actionBusy)}>Tentar novamente</Button>}</div>}
                </Panel>
              ))}
            </div>
          </Panel>
        ))}
      </div>
    </section>
  );
}

function filterFromLocation(): CollectionExecutionFilter | null {
  const query = new URLSearchParams(window.location.search);
  if (!["from", "to", "state"].some((key) => query.has(key))) return null;
  return { from: query.get("from") ?? "", to: query.get("to") ?? "", state: query.get("state") ?? "" };
}

export function CollectionsSection({ canManage, loadSignal, notify }: { canManage: boolean; loadSignal: number; notify: (message: string) => void }) {
  const [companies, setCompanies] = useState<CollectionCompany[]>([]);
  const [executionResult, setExecutionResult] = useState<CollectionExecutionResponse | null>(null);
  const [executionFilter, setExecutionFilter] = useState<CollectionExecutionFilter | null>(() => filterFromLocation());
  const [collectionLoading, setCollectionLoading] = useState(false);
  const [executionLoading, setExecutionLoading] = useState(false);
  const [collectionStale, setCollectionStale] = useState(false);
  const [executionStale, setExecutionStale] = useState(false);
  const [executionError, setExecutionError] = useState<CollectionsPresentationProps["executionError"]>("");
  const [error, setError] = useState("");
  const [actionBusy, setActionBusy] = useState("");
  const collectionRequestSequence = useRef(0);
  const companiesRef = useRef<CollectionCompany[]>([]);
  const executionRef = useRef<CollectionExecutionResponse | null>(null);

  const loadCollections = useCallback(async (requestedFilter: CollectionExecutionFilter | null = filterFromLocation()) => {
    const requestId = ++collectionRequestSequence.current;
    setCollectionLoading(true);
    setError("");
    setExecutionError("");
    setExecutionLoading(requestedFilter !== null);
    setCollectionStale(companiesRef.current.length > 0);
    setExecutionStale(requestedFilter !== null && executionRef.current !== null);
    const [collectionRead, executionRead] = await Promise.allSettled([
      listCollections(),
      requestedFilter ? listCollectionExecutions(requestedFilter) : Promise.resolve(null),
    ]);
    if (requestId !== collectionRequestSequence.current) return;
    if (collectionRead.status === "fulfilled") {
      companiesRef.current = collectionRead.value.collections;
      setCompanies(collectionRead.value.collections);
      setCollectionStale(false);
    } else {
      setCollectionStale(companiesRef.current.length > 0);
      setError("Não foi possível consultar o estado das coletas. A última leitura segura continua disponível.");
    }
    if (requestedFilter && executionRead.status === "fulfilled" && executionRead.value) {
      executionRef.current = executionRead.value;
      setExecutionResult(executionRead.value);
      setExecutionStale(false);
    } else if (requestedFilter && executionRead.status === "rejected") {
      const status = executionRead.reason instanceof ApiError ? executionRead.reason.status : 0;
      setExecutionError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
      setExecutionStale(executionRef.current !== null);
    } else if (!requestedFilter) {
      setExecutionResult(null);
      setExecutionStale(false);
    }
    if (collectionRead.status === "rejected" || (requestedFilter && executionRead.status === "rejected")) notify("Não foi possível consultar o estado das coletas.");
    setCollectionLoading(false);
    setExecutionLoading(false);
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0 || executionFilter !== null) void loadCollections(executionFilter);
  }, [executionFilter, loadCollections, loadSignal]);

  useEffect(() => {
    const loadLocation = () => setExecutionFilter(filterFromLocation());
    window.addEventListener("hashchange", loadLocation);
    window.addEventListener("popstate", loadLocation);
    return () => {
      window.removeEventListener("hashchange", loadLocation);
      window.removeEventListener("popstate", loadLocation);
    };
  }, []);

  function changeFilter(filter: CollectionExecutionFilter) {
    const url = new URL(window.location.href);
    for (const key of ["from", "to", "state"] as const) {
      const value = filter[key];
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    }
    window.history.pushState(null, "", `${url.pathname}${url.search}${url.hash || "#coletas"}`);
    setExecutionFilter(filter);
  }

  async function runMutation(key: string, operation: () => Promise<void>) {
    if (actionBusy) return;
    setActionBusy(key);
    try {
      await operation();
    } finally {
      setActionBusy("");
    }
  }

  async function requestCollection(companyId: string, scope: "completa" | "nfe" | "nfse") {
    await runMutation(`request-${companyId}-${scope}`, async () => {
      try {
        await requestCollectionApi(companyId, scope);
        notify("Solicitação de coleta registrada; o estado durável será atualizado pelo servidor.");
        await loadCollections();
      } catch (caught: unknown) {
        notify(caught instanceof ApiError ? caught.detail : "A coleta não foi aceita.");
      }
    });
  }

  async function retryCollection(companyId: string, executionId: string) {
    await runMutation(`retry-${executionId}`, async () => {
      try {
        await retryCollectionApi(companyId, executionId);
        notify("Nova tentativa de coleta registrada.");
        await loadCollections();
      } catch (caught: unknown) {
        notify(caught instanceof ApiError ? caught.detail : "A nova tentativa não foi aceita.");
      }
    });
  }

  return (
    <CollectionsPresentation
      companies={companies}
      executionResult={executionResult}
      executionFilter={executionFilter}
      executionLoading={executionLoading}
      executionStale={executionStale}
      collectionStale={collectionStale}
      collectionLoading={collectionLoading}
      error={error}
      executionError={executionError}
      canManage={canManage}
      actionBusy={actionBusy}
      onReload={() => void loadCollections()}
      onRetry={() => void loadCollections()}
      onFilterChange={changeFilter}
      onRequest={(companyId, scope) => void requestCollection(companyId, scope)}
      onRetryCollection={(companyId, executionId) => void retryCollection(companyId, executionId)}
    />
  );
}
