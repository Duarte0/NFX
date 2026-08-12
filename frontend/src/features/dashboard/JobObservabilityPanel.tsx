import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../shared/http";
import { Button, DataTable } from "../../shared/ui/primitives";
import { Feedback } from "../../shared/ui/Feedback";
import { listJobObservability } from "./api";
import { JobObservabilityFilter, JobObservabilityResponse } from "./types";

function filterFromLocation(): JobObservabilityFilter | null {
  if (window.location.hash && window.location.hash !== "#dashboard") return null;
  const query = new URLSearchParams(window.location.search);
  if (!(query.has("from") || query.has("to") || query.has("filter"))) return null;
  return {
    from: query.get("from") ?? "",
    to: query.get("to") ?? "",
    filter: query.get("filter") ?? "",
  };
}

function filterLabel(filter: string): string {
  return {
    pending: "Processamento pendente",
    failed: "Processamento com falha",
    blocked: "Processamento bloqueado",
  }[filter] ?? filter;
}

function stateLabel(state: string): string {
  return {
    queued: "Na fila",
    running: "Em execução",
    completed: "Concluído",
    blocked: "Bloqueado",
  }[state] ?? "Estado desconhecido";
}

function outcomeLabel(outcome: string | null): string {
  return {
    success: "Sucesso",
    temporary: "Temporário",
    cooldown: "Cooldown",
    permanent: "Permanente",
    partial: "Parcial",
  }[outcome ?? ""] ?? "—";
}

function queryErrorFor(status: number): "unavailable" | "invalid" | "degraded" {
  return status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable";
}

type JobObservabilityPanelProps = { loadSignal: number; notify: (message: string) => void };

export function JobObservabilityPanel({ loadSignal, notify }: JobObservabilityPanelProps) {
  const [filter, setFilter] = useState<JobObservabilityFilter | null>(() => filterFromLocation());
  const [result, setResult] = useState<JobObservabilityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [queryError, setQueryError] = useState<"unavailable" | "invalid" | "degraded" | "">("");

  const loadJobs = useCallback(async (selected: JobObservabilityFilter) => {
    setLoading(true);
    setError("");
    setQueryError("");
    try {
      setResult(await listJobObservability(selected));
    } catch (caught: unknown) {
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(queryErrorFor(status));
      setResult(null);
      setError("Não foi possível consultar os jobs de processamento.");
      notify("Não foi possível consultar os jobs de processamento.");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    const refreshLocation = () => setFilter(filterFromLocation());
    window.addEventListener("hashchange", refreshLocation);
    window.addEventListener("popstate", refreshLocation);
    return () => {
      window.removeEventListener("hashchange", refreshLocation);
      window.removeEventListener("popstate", refreshLocation);
    };
  }, []);

  useEffect(() => {
    if (filter !== null) void loadJobs(filter);
  }, [filter, loadJobs, loadSignal]);

  if (filter === null) return null;

  return (
    <section id="processamento" aria-label="Jobs de processamento">
      <h3>Jobs de processamento</h3>
      <p>Filtro solicitado: {filterLabel(filter.filter)}</p>
      <Button variant="secondary" onClick={() => void loadJobs(filter)}>Atualizar jobs</Button>
      {loading && <Feedback state="loading" message="Carregando jobs de processamento…" />}
      <Feedback message={error} state="error" />
      {queryError === "invalid" && <Feedback state="error" message="O filtro de jobs é inválido." />}
      {queryError === "unavailable" && <Feedback state="unavailable" message="Os jobs de processamento estão indisponíveis." />}
      {queryError === "degraded" && <Feedback state="degraded" message="A consulta de jobs está degradada." />}
      {!loading && !error && result && (
        <>
          <p>
            Filtro aplicado: {filterLabel(result.filter.filter)} · {result.filter.from} até {result.filter.to} · limite {result.limit} · {result.boundary}
          </p>
          <p role="status">
            Total reconciliado: {result.total}
            {result.truncated ? " (mostrando somente a primeira página limitada)" : ""}
          </p>
          {result.jobs.length === 0 ? (
            <Feedback state="empty" message="Nenhum job encontrado para este filtro." />
          ) : (
            <DataTable caption="Jobs de processamento">
              <thead><tr><th>Tipo</th><th>Estado</th><th>Resultado</th><th>Tentativas</th><th>Criado em</th><th>Erro seguro</th></tr></thead>
              <tbody>
                {result.jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{job.job_type}</td>
                    <td>{stateLabel(job.state)}</td>
                    <td>{outcomeLabel(job.outcome)}</td>
                    <td>{job.attempt_count}</td>
                    <td>{job.created_at}</td>
                    <td>{job.safe_error || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </>
      )}
    </section>
  );
}
