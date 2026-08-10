import { useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { getRetentionPreview, listRetention } from "./api";
import { RetentionItem, RetentionPreview, RetentionResponse } from "./types";

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
    } catch (caught) {
      if (caught instanceof Error && "status" in caught && (caught as { status: number }).status === 409) {
        setStale(true);
      } else {
        notify("Não foi possível gerar a prévia de retenção.");
      }
      setPreview(null);
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
          <p>Evidências originais/XML: {preview.evidence.length} · Eventos: {preview.events.length}</p>
          <p>{preview.deletion.message}</p>
          <button onClick={() => setPreview(null)}>Fechar prévia</button>
        </aside>
      )}
    </section>
  );
}
