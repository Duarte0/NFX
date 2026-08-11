import { useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { createExport, downloadExport, getExport, listExports } from "./api";
import { ExportDetail, ExportItemSummary } from "./types";

type ExportsSectionProps = { loadSignal: number; notify: (message: string) => void };

function stateLabel(state: ExportItemSummary["state"]): string {
  return {
    pending: "Pendente", processing: "Processando", complete: "Completa", partial: "Parcial",
    failed: "Falhou", available: "Disponível", expired: "Expirada", excluded: "Excluída",
  }[state];
}

export function ExportsSection({ loadSignal, notify }: ExportsSectionProps) {
  const [exports, setExports] = useState<ExportItemSummary[]>([]);
  const [detail, setDetail] = useState<ExportDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadExports = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setExports((await listExports()).exports);
    } catch {
      setError("Não foi possível consultar as exportações.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (loadSignal > 0) void loadExports();
  }, [loadExports, loadSignal]);

  async function requestExport() {
    try {
      const created = await createExport({}, `ui-${Date.now()}`);
      setExports((current) => [created, ...current]);
      notify("Exportação enfileirada.");
    } catch {
      notify("Não foi possível solicitar a exportação.");
    }
  }

  async function showDetail(id: string) {
    try {
      setDetail(await getExport(id));
    } catch {
      notify("Não foi possível consultar a exportação.");
    }
  }

  return (
    <section id="exportacoes">
      <h2>Exportações</h2>
      <button onClick={() => void requestExport()}>Exportar documentos consultados</button>
      <button onClick={() => void loadExports()}>Atualizar exportações</button>
      {loading && <p role="status">Carregando exportações…</p>}
      <Feedback message={error} error />
      {!loading && !error && exports.length === 0 && <p>Nenhuma exportação solicitada.</p>}
      {!loading && !error && exports.length > 0 && (
        <table>
          <thead><tr><th>Solicitada</th><th>Estado</th><th>Itens</th><th>Expira</th><th>Ações</th></tr></thead>
          <tbody>{exports.map((item) => (
            <tr key={item.id}>
              <td>{new Date(item.created_at).toLocaleString("pt-BR")}</td>
              <td>{stateLabel(item.state)}{item.safe_error ? ` · ${item.safe_error}` : ""}</td>
              <td>{item.produced_count}/{item.expected_count}</td>
              <td>{new Date(item.expires_at).toLocaleString("pt-BR")}</td>
              <td>
                <button onClick={() => void showDetail(item.id)}>Detalhes</button>
                {item.download_url && <button onClick={() => void downloadExport(item.download_url!).catch(() => notify("Exportação indisponível."))}>Baixar ZIP</button>}
              </td>
            </tr>
          ))}</tbody>
        </table>
      )}
      {detail && <aside aria-label="Detalhe da exportação">
        <h3>Detalhe da exportação</h3>
        <p>{stateLabel(detail.state)} · {detail.produced_count}/{detail.expected_count} itens</p>
        <p>Expira em {new Date(detail.expires_at).toLocaleString("pt-BR")}</p>
        {detail.items.some((item) => item.safe_error) && <p>Itens indisponíveis são exibidos explicitamente como parciais.</p>}
        <button onClick={() => setDetail(null)}>Fechar detalhe</button>
      </aside>}
    </section>
  );
}
