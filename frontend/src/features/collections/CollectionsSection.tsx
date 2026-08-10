import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
import {
  listCollections,
  requestCollection as requestCollectionApi,
  retryCollection as retryCollectionApi,
} from "./api";
import { CollectionCompany } from "./types";

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

type CollectionsSectionProps = {
  canManage: boolean;
  loadSignal: number;
  notify: (message: string) => void;
};

export function CollectionsSection({ canManage, loadSignal, notify }: CollectionsSectionProps) {
  const [companies, setCompanies] = useState<CollectionCompany[]>([]);
  const [error, setError] = useState("");

  const loadCollections = useCallback(async () => {
    try {
      setError("");
      setCompanies((await listCollections()).collections);
    } catch {
      setError("Não foi possível consultar o estado das coletas.");
      notify("Não foi possível consultar o estado das coletas.");
    }
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0) void loadCollections();
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
      <Feedback message={error} error />
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
