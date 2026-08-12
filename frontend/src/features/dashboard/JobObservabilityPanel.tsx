import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Badge, Button, DataTable } from "../../shared/ui/primitives";
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
  }[filter] ?? "Filtro não reconhecido";
}

function stateLabel(state: string): string {
  return {
    queued: "Na fila",
    running: "Em execução",
    completed: "Concluído",
    blocked: "Bloqueado",
  }[state] ?? "Estado não reconhecido";
}

function outcomeLabel(outcome: string | null): string {
  return {
    success: "Sucesso",
    temporary: "Temporário",
    cooldown: "Cooldown",
    permanent: "Permanente",
    partial: "Parcial",
  }[outcome ?? ""] ?? "Resultado não reconhecido";
}

function safeJobErrorLabel(code: string): string {
  return {
    artifact_unavailable: "Artefato indisponível.",
    authorization_blocked: "Autorização bloqueada.",
    authorization_revoked: "Autorização revogada.",
    certificate_invalid: "Certificado inválido.",
    deletion_failed: "Falha na exclusão controlada.",
    handler_failed: "Falha no processamento.",
    handler_not_registered: "Processamento não disponível.",
    invalid_export_reference: "Referência de exportação inválida.",
    invalid_operation: "Operação inválida.",
    lease_expired: "Execução recuperada após expiração.",
    operation_missing: "Operação não encontrada.",
    official_cooldown: "Aguardando janela da fonte oficial.",
    partial_result: "Resultado parcial.",
    permanent_failure: "Falha permanente.",
    policy_required: "Política de processamento necessária.",
    recovery_required: "Recuperação manual necessária.",
    render_audit_unavailable: "Auditoria de renderização indisponível.",
    render_reference_invalid: "Referência de renderização inválida.",
    render_reference_missing: "Referência de renderização ausente.",
    renderer_failed: "Falha na renderização.",
    retry_exhausted: "Tentativas esgotadas.",
    temporary_failure: "Falha temporária.",
  }[code] ?? "Falha de processamento sem detalhes.";
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
  const requestSequence = useRef(0);

  const loadJobs = useCallback(async (selected: JobObservabilityFilter) => {
    const sequence = requestSequence.current + 1;
    requestSequence.current = sequence;
    setLoading(true);
    setError("");
    setQueryError("");
    try {
      const nextResult = await listJobObservability(selected);
      if (sequence !== requestSequence.current) return;
      setResult(nextResult);
    } catch (caught: unknown) {
      if (sequence !== requestSequence.current) return;
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(queryErrorFor(status));
      setError("Não foi possível consultar os jobs de processamento.");
      notify("Não foi possível consultar os jobs de processamento.");
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
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
      {result && (loading || error) && (
        <div className="dashboard-state dashboard-state--stale" role="status" aria-live="polite">
          <Badge variant="warning">Desatualizado</Badge>
          <p>A última leitura segura dos jobs permanece visível enquanto a consulta é atualizada ou revalidada.</p>
        </div>
      )}
      {result && (
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
                    <td>{job.safe_error ? safeJobErrorLabel(job.safe_error) : "—"}</td>
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
