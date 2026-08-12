import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
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

function collectionLabel(status: string): string {
  return (
    {
      idle: "Sem coleta", queued: "Na fila", running: "Em execução",
      concluded: "Concluída", empty: "Consulta válida sem documentos",
      partial: "Parcial", retrying: "Retry agendado", cooldown: "Cooldown",
      blocked: "Bloqueada", failed: "Falha",
    }[status] ?? status
  );
}

function coverageLabel(status: string): string {
  return {
    available: "Cobertura ADN disponível",
    none: "Sem cobertura automática no ADN",
    unknown: "Cobertura ADN desconhecida",
  }[status] ?? "Cobertura ADN não verificada";
}

function executionStateLabel(state: string): string {
  return {
    recent: "Todas as execuções",
    running: "Em execução",
    failed: "Com falha",
    blocked: "Bloqueadas",
    partial: "Parciais",
  }[state] ?? state;
}

function executionOutcomeLabel(execution: CollectionExecutionSummary): string {
  const state = executionStateLabel(execution.state);
  return execution.safe_error ? `${state} · ${execution.safe_error}` : state;
}

function executionFilterFromLocation(): CollectionExecutionFilter | null {
  const query = new URLSearchParams(window.location.search);
  if (!["from", "to", "state"].some((key) => query.has(key))) return null;
  return {
    from: query.get("from") ?? "",
    to: query.get("to") ?? "",
    state: query.get("state") ?? "",
  };
}

type CollectionsSectionProps = {
  canManage: boolean;
  loadSignal: number;
  notify: (message: string) => void;
};

export function CollectionsSection({ canManage, loadSignal, notify }: CollectionsSectionProps) {
  const [companies, setCompanies] = useState<CollectionCompany[]>([]);
  const [executionResult, setExecutionResult] = useState<CollectionExecutionResponse | null>(null);
  const [executionLoading, setExecutionLoading] = useState(false);
  const [executionError, setExecutionError] = useState<"unavailable" | "invalid" | "degraded" | "">("");
  const [error, setError] = useState("");

  const loadCollections = useCallback(async () => {
    const filter = executionFilterFromLocation();
    try {
      setError("");
      setExecutionError("");
      setExecutionLoading(filter !== null);
      const [collectionResponse, executionResponse] = await Promise.all([
        listCollections(),
        filter ? listCollectionExecutions(filter) : Promise.resolve(null),
      ]);
      setCompanies(collectionResponse.collections);
      setExecutionResult(executionResponse);
    } catch (error: unknown) {
      if (filter !== null) {
        const status = error instanceof ApiError ? error.status : 0;
        setExecutionError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
        setExecutionResult(null);
      }
      setError("Não foi possível consultar o estado das coletas.");
      notify("Não foi possível consultar o estado das coletas.");
    } finally {
      setExecutionLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0 || executionFilterFromLocation() !== null) void loadCollections();
  }, [loadCollections, loadSignal]);

  async function requestCollection(companyId: string, scope: "completa" | "nfe" | "nfse") {
    try {
      await requestCollectionApi(companyId, scope);
      notify("Solicitação de coleta registrada.");
      await loadCollections();
    } catch (error: unknown) {
      notify(error instanceof ApiError ? error.detail : "A coleta não foi aceita.");
    }
  }

  async function retryCollection(companyId: string, executionId: string) {
    try {
      await retryCollectionApi(companyId, executionId);
      notify("Retry de coleta registrado.");
      await loadCollections();
    } catch (error: unknown) {
      notify(error instanceof ApiError ? error.detail : "O retry não foi aceito.");
    }
  }

  return (
    <section id="coletas">
      <h2>Coletas</h2>
      <button onClick={() => void loadCollections()}>Atualizar coletas</button>
      <Feedback message={error} state="error" />
      {executionLoading && <p role="status">Carregando execuções filtradas…</p>}
      {executionFilterFromLocation() && executionError === "invalid" && (
        <p role="status">O filtro de execuções é inválido.</p>
      )}
      {executionFilterFromLocation() && executionError === "unavailable" && (
        <p role="status">As execuções filtradas estão indisponíveis.</p>
      )}
      {executionFilterFromLocation() && executionError === "degraded" && (
        <p role="status">A consulta de execuções está degradada.</p>
      )}
      {executionResult && (
        <section aria-label="Execuções filtradas">
          <h3>Execuções filtradas</h3>
          <p>
            {executionStateLabel(executionResult.filter.state)} · {executionResult.filter.from} até {executionResult.filter.to} · limite {executionResult.boundary}
          </p>
          <p role="status">
            Total reconciliado: {executionResult.total}
            {executionResult.truncated ? " (mostrando somente a primeira página limitada)" : ""}
          </p>
          {executionResult.executions.length === 0 ? (
            <p>Nenhuma execução encontrada para este filtro.</p>
          ) : (
            <ul>
              {executionResult.executions.map((execution) => (
                <li key={execution.id}>
                  {execution.company_name} · {execution.family} · {executionOutcomeLabel(execution)} · {execution.created_at}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {companies.length === 0 && <p>Nenhuma empresa disponível.</p>}
      {companies.map((item) => (
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
                {flow.family === "nfe" ? "NF-e" : "NFS-e"}: {collectionLabel(flow.collection_state)}
              </strong>
              <p>Tentativa: {flow.last_attempt_at ?? "—"} · Sucesso: {flow.last_success_at ?? "—"}</p>
              {flow.family === "nfse" && flow.coverage && (
                <p role="status">
                  {coverageLabel(flow.coverage.status)} · verificada em {flow.coverage.verified_at}
                </p>
              )}
              {flow.safe_error && <p role="status">Correção: {flow.safe_error}</p>}
              {canManage && (
                <>
                  <button
                    disabled={flow.collection_state !== "idle" && flow.active_execution !== null}
                    onClick={() => void requestCollection(item.company_id, flow.family)}
                  >
                    Solicitar {flow.family}
                  </button>
                  {flow.latest_execution && ["failed", "partial"].includes(flow.latest_execution.state) && (
                    <button onClick={() => void retryCollection(item.company_id, flow.latest_execution?.id ?? "")}>
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
  );
}
