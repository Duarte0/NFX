import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback, FeedbackState } from "../../shared/ui/Feedback";
import { Badge, Button, DataTable, Field, Panel } from "../../shared/ui/primitives";
import { listCertificateInventory } from "./api";
import { CertificateInventoryResponse } from "./types";

type CertificateInventoryPanelProps = { loadSignal: number };

export type CertificateInventoryQuery = { filter: string | null; cursor: string | null };

export type CertificateInventoryPresentationProps = {
  filter: string | null;
  cursor: string | null;
  result: CertificateInventoryResponse | null;
  loading: boolean;
  stale: boolean;
  error: string;
  queryError: "unavailable" | "invalid" | "degraded" | "";
  onFilterChange: (filter: string) => void;
  onReload: () => void;
  onRetry: () => void;
  onNextPage: () => void;
};

export function certificateInventoryQueryFromLocation(): CertificateInventoryQuery {
  const query = new URLSearchParams(window.location.search);
  return {
    filter: query.get("filter"),
    cursor: query.get("cursor"),
  };
}

function filterLabel(filter: string | null): string {
  return {
    current: "Certificados atuais",
    expired: "Certificados vencidos",
    expiring: "Certificados próximos do vencimento",
  }[filter ?? ""] ?? "Filtro de certificados informado pelo servidor";
}

export function certificateStatusLabel(status: string): string {
  return {
    valido: "Certificado válido",
    proximo_vencimento: "Certificado próximo do vencimento",
    expirado: "Certificado vencido",
    invalido: "Certificado inválido",
    pendente: "Certificado pendente de validação",
    substituido: "Certificado substituído",
    falha_armazenamento: "Certificado indisponível para armazenamento",
  }[status] ?? "Estado do certificado informado pelo servidor";
}

function certificateStatusVariant(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "valido") return "success";
  if (status === "proximo_vencimento") return "warning";
  if (["expirado", "invalido", "falha_armazenamento"].includes(status)) return "danger";
  return "neutral";
}

export function certificateFreshnessLabel(status: string): string {
  return {
    fresh: "Leitura atual",
    stale: "Leitura desatualizada",
    unknown: "Atualidade não determinada",
  }[status] ?? "Atualidade não informada";
}

function queryErrorState(error: CertificateInventoryPresentationProps["queryError"]): FeedbackState {
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

export function CertificateInventoryPresentation({
  filter,
  cursor,
  result,
  loading,
  stale,
  error,
  queryError,
  onFilterChange,
  onReload,
  onRetry,
  onNextPage,
}: CertificateInventoryPresentationProps) {
  function submitFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get("filter");
    if (typeof value === "string" && value) onFilterChange(value);
  }

  return (
    <Panel as="section" id="certificate-inventory" title="Inventário de certificados" className="feature-panel certificate-inventory">
      <form key={filter ?? "no-filter"} className="feature-toolbar" onSubmit={submitFilter}>
        <Field id="certificate-filter" label="Filtro de validade" hint="A seleção é validada pelo servidor.">
          <select name="filter" defaultValue={filter ?? ""}>
            <option value="">Escolha um filtro</option>
            <option value="current">Certificados atuais</option>
            <option value="expired">Certificados vencidos</option>
            <option value="expiring">Certificados próximos do vencimento</option>
          </select>
        </Field>
        <Button type="submit" variant="secondary">Aplicar filtro</Button>
        {filter && <Button type="button" variant="secondary" onClick={onReload} disabled={loading}>Atualizar inventário</Button>}
      </form>
      <p className="feature-context">{filter ? `Filtro solicitado: ${filterLabel(filter)}` : "Nenhum filtro de validade selecionado."}</p>
      {loading && <Feedback state="loading" message="Carregando inventário de certificados…" />}
      {staleNotice(stale)}
      {error && <Feedback state={queryErrorState(queryError)} message={error} />}
      {queryError === "invalid" && <Feedback state="error" message="O filtro de certificados é inválido." />}
      {queryError === "unavailable" && <Feedback state="unavailable" message="O inventário de certificados está indisponível." />}
      {queryError === "degraded" && <Feedback state="degraded" message="A consulta de certificados está degradada." />}
      {(error || queryError) && <Button type="button" variant="secondary" onClick={onRetry} disabled={loading}>Tentar novamente</Button>}
      {filter && result && (
        <>
          <div className="feature-summary" role="status">
            <span>Filtro aplicado: {filterLabel(result.filter.filter)}</span>
            <span>Total reconciliado: {result.total}</span>
            <span>Limite: {result.limit}</span>
            <span>{result.truncated ? "Há mais resultados" : "Todos os resultados desta consulta foram apresentados"}</span>
            <span>{certificateFreshnessLabel(result.freshness.status)} · Avaliado em: {result.evaluated_at}</span>
          </div>
          {result.certificates.length === 0 ? (
            <Feedback state="empty" message="Nenhum certificado encontrado para este filtro. A consulta é válida e não indica disponibilidade de certificado." />
          ) : (
            <DataTable caption="Inventário de certificados">
              <thead><tr><th>Empresa</th><th>Status</th><th>Válido até</th><th>Dias restantes</th></tr></thead>
              <tbody>
                {result.certificates.map((certificate) => (
                  <tr key={certificate.id}>
                    <td>{certificate.company.legal_name}</td>
                    <td><Badge variant={certificateStatusVariant(certificate.status)}>{certificateStatusLabel(certificate.status)}</Badge></td>
                    <td>{certificate.not_after}</td>
                    <td>{certificate.days_until_expiry ?? "Não informado"}</td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
          {result.next_cursor && (
            <div className="feature-pagination">
              <Button type="button" variant="secondary" onClick={onNextPage} disabled={loading}>Próxima página</Button>
              <span>Os filtros permanecem ativos na próxima página.</span>
            </div>
          )}
        </>
      )}
      {!filter && <Feedback state="empty" message="Escolha um filtro para consultar o inventário sem transformar ausência em disponibilidade." />}
      {cursor && <span className="sr-only">Página seguinte selecionada pelo servidor.</span>}
    </Panel>
  );
}

export function CertificateInventoryPanel({ loadSignal }: CertificateInventoryPanelProps) {
  const [query, setQuery] = useState<CertificateInventoryQuery>(() => certificateInventoryQueryFromLocation());
  const [result, setResult] = useState<CertificateInventoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [queryError, setQueryError] = useState<CertificateInventoryPresentationProps["queryError"]>("");
  const certificateRequestSequence = useRef(0);
  const resultRef = useRef<CertificateInventoryResponse | null>(null);

  const updateLocation = useCallback((nextFilter: string | null, nextCursor: string | null = null) => {
    const url = new URL(window.location.href);
    if (nextFilter) url.searchParams.set("filter", nextFilter);
    else url.searchParams.delete("filter");
    if (nextCursor) url.searchParams.set("cursor", nextCursor);
    else url.searchParams.delete("cursor");
    window.history.pushState(null, "", `${url.pathname}${url.search}${url.hash}`);
    setQuery({ filter: nextFilter, cursor: nextCursor });
  }, []);

  const loadInventory = useCallback(async (requestedQuery: CertificateInventoryQuery) => {
    if (!requestedQuery.filter) {
      setLoading(false);
      return;
    }
    const requestId = ++certificateRequestSequence.current;
    setLoading(true);
    setError("");
    setQueryError("");
    setStale(resultRef.current !== null);
    try {
      const next = await listCertificateInventory(requestedQuery.filter, 50, requestedQuery.cursor ?? undefined);
      if (requestId !== certificateRequestSequence.current) return;
      resultRef.current = next;
      setResult(next);
      setStale(false);
    } catch (caught: unknown) {
      if (requestId !== certificateRequestSequence.current) return;
      const status = caught instanceof ApiError ? caught.status : 0;
      setQueryError(status === 400 ? "invalid" : status === 503 ? "degraded" : "unavailable");
      setStale(resultRef.current !== null);
      setError("Não foi possível carregar o inventário de certificados. A última leitura segura continua disponível.");
    } finally {
      if (requestId === certificateRequestSequence.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const refreshLocation = () => setQuery(certificateInventoryQueryFromLocation());
    window.addEventListener("hashchange", refreshLocation);
    window.addEventListener("popstate", refreshLocation);
    return () => {
      window.removeEventListener("hashchange", refreshLocation);
      window.removeEventListener("popstate", refreshLocation);
    };
  }, []);

  useEffect(() => {
    if (query.filter) void loadInventory(query);
  }, [query, loadInventory, loadSignal]);

  return (
    <CertificateInventoryPresentation
      filter={query.filter}
      cursor={query.cursor}
      result={result}
      loading={loading}
      stale={stale}
      error={error}
      queryError={queryError}
      onFilterChange={(filter) => updateLocation(filter)}
      onReload={() => void loadInventory(query)}
      onRetry={() => void loadInventory(query)}
      onNextPage={() => updateLocation(query.filter, result?.next_cursor ?? null)}
    />
  );
}
