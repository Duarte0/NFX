import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../shared/http";
import { listCertificateInventory } from "./api";
import { CertificateInventoryResponse } from "./types";

type CertificateInventoryPanelProps = { loadSignal: number };

function filterFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("filter");
  return value === null ? null : value;
}

function filterLabel(filter: string): string {
  return {
    current: "Certificados atuais",
    expired: "Certificados vencidos",
    expiring: "Certificados próximos do vencimento",
  }[filter] ?? filter;
}

function freshnessLabel(result: CertificateInventoryResponse): string {
  return result.freshness.status === "fresh" ? "Atual" : "Frescura desconhecida";
}

export function CertificateInventoryPanel({ loadSignal }: CertificateInventoryPanelProps) {
  const [filter, setFilter] = useState<string | null>(() => filterFromLocation());
  const [result, setResult] = useState<CertificateInventoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [queryError, setQueryError] = useState<"unavailable" | "invalid" | "degraded" | "">("");

  const loadInventory = useCallback(async (selectedFilter: string) => {
    setLoading(true);
    setError("");
    setQueryError("");
    try {
      setResult(await listCertificateInventory(selectedFilter));
    } catch (caught: unknown) {
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
      setResult(null);
      setError("Não foi possível carregar o inventário de certificados.");
    } finally {
      setLoading(false);
    }
  }, []);

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
    if (filter !== null) void loadInventory(filter);
  }, [filter, loadInventory, loadSignal]);

  if (filter === null) return null;

  return (
    <section aria-label="Inventário de certificados">
      <h3>Inventário de certificados</h3>
      <p>Filtro solicitado: {filterLabel(filter)}</p>
      <button onClick={() => void loadInventory(filter)}>Atualizar inventário</button>
      {loading && <p role="status">Carregando inventário de certificados…</p>}
      {error && <p role="alert">{error}</p>}
      {queryError === "invalid" && <p role="status">O filtro de certificados é inválido.</p>}
      {queryError === "unavailable" && <p role="status">Os certificados estão indisponíveis.</p>}
      {queryError === "degraded" && <p role="status">A consulta de certificados está degradada.</p>}
      {!loading && !error && result && (
        <p role="status">
          Filtro aplicado: {filterLabel(result.filter.filter)} · Total reconciliado: {result.total}
          {result.truncated ? " (mostrando somente a primeira página limitada)" : ""}
          {" · "}{freshnessLabel(result)} · Avaliado em: {result.evaluated_at}
        </p>
      )}
      {!loading && !error && result && result.certificates.length === 0 && (
        <p>Nenhum certificado encontrado para este filtro.</p>
      )}
      {!loading && !error && result && result.certificates.length > 0 && (
        <table>
          <thead><tr><th>Empresa</th><th>CNPJ</th><th>Status</th><th>Válido até</th><th>Dias</th></tr></thead>
          <tbody>
            {result.certificates.map((certificate) => (
              <tr key={certificate.id}>
                <td>{certificate.company.legal_name}</td>
                <td>{certificate.company.cnpj}</td>
                <td>{certificate.status}</td>
                <td>{certificate.not_after}</td>
                <td>{certificate.days_until_expiry ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
