import { useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { getDeletionStatus, getRetentionPreview, listRetention, requestDeletion, resumeDeletion } from "./api";
import { DeletionOperation, RetentionItem, RetentionPreview, RetentionResponse } from "./types";

function stateLabel(state: RetentionItem["state"]): string {
  return {
    retained: "Retido",
    eligible: "Elegível",
    non_executable: "Não executável",
  }[state];
}

export function RetentionSection({ loadSignal, notify }: { loadSignal: number; notify: (message: string) => void }) {
  const [retention, setRetention] = useState<RetentionResponse | null>(null);
  const [preview, setPreview] = useState<RetentionPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const [reason, setReason] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [operation, setOperation] = useState<DeletionOperation | null>(null);

  const loadRetention = useCallback(async () => {
    setLoading(true);
    setError("");
    setStale(false);
    try {
      setRetention(await listRetention());
    } catch {
      setRetention(null);
      setError("Não foi possível consultar a retenção.");
      notify("Não foi possível consultar a retenção.");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0) void loadRetention();
  }, [loadRetention, loadSignal]);

  async function showPreview(item: RetentionItem) {
    setStale(false);
    try {
      setPreview(await getRetentionPreview(item.id, item.scope_hash));
      setReason("");
      setConfirmation("");
    } catch (caught) {
      if (caught instanceof Error && "status" in caught && (caught as { status: number }).status === 409) {
        setStale(true);
      } else {
        notify("Não foi possível gerar a prévia de retenção.");
      }
      setPreview(null);
    }
  }

  function expectedConfirmation(): string {
    return preview ? `EXCLUIR:${preview.document.id}:${preview.scope.hash}` : "";
  }

  async function submitDeletion() {
    if (!preview) return;
    try {
      const created = await requestDeletion(preview.document.id, {
        scope_hash: preview.scope.hash,
        scope_version: preview.scope.version,
        confirmation,
        reason,
      });
      setOperation(created);
      notify("Exclusão controlada enfileirada.");
    } catch (caught) {
      if (caught instanceof Error && "status" in caught && (caught as { status: number }).status === 409) {
        setStale(true);
      }
      notify("Não foi possível solicitar a exclusão controlada.");
    }
  }

  async function refreshOperation() {
    if (!operation) return;
    try {
      setOperation(await getDeletionStatus(operation.id));
    } catch {
      notify("Não foi possível consultar a exclusão controlada.");
    }
  }

  async function resumeOperation() {
    if (!operation) return;
    try {
      setOperation(await resumeDeletion(operation.id));
      notify("Recuperação da exclusão enfileirada.");
    } catch {
      notify("Não foi possível retomar a exclusão controlada.");
    }
  }

  return (
    <section id="retencao">
      <h2>Retenção</h2>
      <p>A prévia é somente metadados e não autoriza exclusão.</p>
      <button onClick={() => void loadRetention()}>Atualizar retenção</button>
      {loading && <p role="status">Carregando retenção…</p>}
      <Feedback message={error} error />
      {stale && <p role="alert">A prévia ficou desatualizada; atualize a lista antes de tentar novamente.</p>}
      {!loading && !error && retention && (
        retention.documents.length === 0 ? (
          <p>Nenhum documento possui decisão de retenção neste escopo.</p>
        ) : (
          <table>
            <thead><tr><th>Documento</th><th>Família</th><th>Estado</th><th>Elegível em</th><th>Regra</th><th>Ação</th></tr></thead>
            <tbody>
              {retention.documents.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.family}</td>
                  <td>{stateLabel(item.state)} · {item.reason_code}</td>
                  <td>{item.eligibility_date ?? "—"}</td>
                  <td>{item.rule_version}</td>
                  <td><button onClick={() => void showPreview(item)}>Ver prévia</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
      {preview && (
        <aside aria-label="Prévia de retenção">
          <h3>Prévia de retenção</h3>
          <p>Escopo {preview.scope.version}: {preview.scope.hash}</p>
          <p>Estado: {stateLabel(preview.decision.state)} · Regra: {preview.decision.rule_version}</p>
          <p>Evidências originais/XML: {preview.evidence.length} · Eventos: {preview.events.length} · PDFs derivados: {preview.renders.length}</p>
          <p>{preview.deletion.message}</p>
          {preview.decision.state === "eligible" && (
            <div>
              <label>
                Motivo bounded
                <input value={reason} maxLength={1000} onChange={(event) => setReason(event.target.value)} />
              </label>
              <label>
                Confirmação exata: <code>{expectedConfirmation()}</code>
                <input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
              </label>
              <button onClick={() => void submitDeletion()}>Solicitar exclusão</button>
            </div>
          )}
          <button onClick={() => setPreview(null)}>Fechar prévia</button>
        </aside>
      )}
      {operation && (
        <aside aria-label="Estado da exclusão controlada">
          <h3>Exclusão controlada</h3>
          <p>{operation.state}{operation.safe_error ? ` · ${operation.safe_error}` : ""}</p>
          <p>Etapa: {operation.current_step ?? "—"}</p>
          <button onClick={() => void refreshOperation()}>Atualizar exclusão</button>
          {(operation.state === "recovery_required" || operation.state === "failed") && (
            <button onClick={() => void resumeOperation()}>Retomar recuperação</button>
          )}
        </aside>
      )}
    </section>
  );
}
