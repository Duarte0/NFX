import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
import { Badge, Button, DataTable, Field, Panel } from "../../shared/ui/primitives";
import { getDeletionStatus, getRetentionPreview, listRetention, requestDeletion, resumeDeletion } from "./api";
import { DeletionOperation, DeletionOperationState, RetentionItem, RetentionPreview, RetentionResponse } from "./types";

const retentionLabels: Record<string, string> = {
  retained: "Retido durante o prazo",
  eligible: "Elegível para exclusão manual",
  non_executable: "Não executável",
};

const retentionReasons: Record<string, string> = {
  within_retention_period: "O prazo fiscal ainda não foi concluído.",
  retention_complete: "O prazo fiscal foi concluído; a exclusão continua sendo manual.",
  missing_authorized_at: "A data de autorização necessária não está disponível.",
  missing_emitted_at: "A data de emissão necessária não está disponível.",
  artifact_missing: "Há evidência necessária indisponível para executar a decisão.",
};

const deletionLabels: Record<DeletionOperationState, string> = {
  pending: "Pendente",
  executing: "Em execução",
  recovery_required: "Recuperação necessária",
  failed: "Falha controlada",
  completed: "Concluída pelo servidor",
};

const deletionSteps: Record<string, string> = {
  requested: "Solicitação recebida",
  resume_requested: "Recuperação solicitada",
  revalidate: "Escopo revalidado",
  artifact: "Tratamento de evidências",
  recovery: "Aguardando recuperação administrativa",
  failed: "Execução interrompida com falha",
  completed: "Conjunto concluído",
};

const deletionErrors: Record<string, string> = {
  scope_changed: "A prévia mudou; gere uma nova prévia antes de tentar novamente.",
  operation_active: "Já existe uma operação ativa para este escopo.",
  audit_unavailable: "A auditoria está indisponível; a operação não foi declarada concluída.",
  artifact_missing: "Uma evidência necessária está ausente; a recuperação é necessária.",
  artifact_divergent: "Uma evidência divergiu; a recuperação é necessária.",
  relational_cleanup_blocked: "A limpeza relacional foi bloqueada; a recuperação é necessária.",
  deletion_failed: "A operação falhou sem declarar exclusão concluída.",
};

export type RetentionPresentationProps = {
  retention: RetentionResponse | null;
  preview: RetentionPreview | null;
  operation: DeletionOperation | null;
  loading: boolean;
  previewLoading: boolean;
  operationLoading: boolean;
  stale: boolean;
  previewStale: boolean;
  error: string;
  previewError: string;
  operationError: string;
  reason: string;
  deleteDialogOpen: boolean;
  onReload: () => void;
  onRetry: () => void;
  onRetryPreview: () => void;
  onPreview: (item: RetentionItem) => void;
  onNextPage: () => void;
  onReasonChange: (value: string) => void;
  onOpenDeleteDialog: () => void;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  onRefreshOperation: () => void;
  onResumeOperation: () => void;
};

export function retentionStateLabel(state: string): string {
  return retentionLabels[state] ?? "Decisão de retenção não reconhecida";
}

export function retentionReasonLabel(reason: string): string {
  return retentionReasons[reason] ?? "A decisão exige análise administrativa segura.";
}

function retentionFieldLabel(value: string | undefined): string {
  const labels: Record<string, string> = {
    document: "Documento fiscal",
    distribution: "Distribuição",
  };
  return labels[value ?? ""] ?? "Informado pelo servidor";
}

export function deletionStateLabel(state: string): string {
  return deletionLabels[state as DeletionOperationState] ?? "Estado de exclusão não reconhecido";
}

export function deletionStepLabel(step: string | null): string {
  return step ? deletionSteps[step] ?? "Etapa informada pelo servidor" : "Etapa não informada";
}

export function deletionErrorLabel(error: string | null): string {
  return error ? deletionErrors[error] ?? "A operação não foi concluída; consulte o estado retornado." : "";
}

function retentionVariant(state: string): "success" | "warning" | "danger" | "neutral" {
  if (state === "eligible") return "success";
  if (state === "retained") return "warning";
  if (state === "non_executable") return "danger";
  return "neutral";
}

function operationVariant(state: string): "success" | "warning" | "danger" | "neutral" {
  if (state === "completed") return "success";
  if (state === "pending" || state === "executing") return "warning";
  if (state === "recovery_required" || state === "failed") return "danger";
  return "neutral";
}

function safePreviewReason(preview: RetentionPreview): string {
  return retentionReasonLabel(preview.decision.reason_code);
}

function confirmationFor(preview: RetentionPreview): string {
  return `EXCLUIR:${preview.document.id}:${preview.scope.hash}`;
}

export function RetentionPresentation({
  retention,
  preview,
  operation,
  loading,
  previewLoading,
  operationLoading,
  stale,
  previewStale,
  error,
  previewError,
  operationError,
  reason,
  deleteDialogOpen,
  onReload,
  onRetry,
  onRetryPreview,
  onPreview,
  onNextPage,
  onReasonChange,
  onOpenDeleteDialog,
  onCancelDelete,
  onConfirmDelete,
  onRefreshOperation,
  onResumeOperation,
}: RetentionPresentationProps) {
  const eligibleCurrentPreview = Boolean(preview && preview.decision.state === "eligible" && !previewStale);
  const confirmationReady = Boolean(eligibleCurrentPreview && reason.trim());
  return (
    <section id="retencao" className="feature-section">
      <div className="feature-heading"><div><p className="feature-eyebrow">Administração</p><h2>Retenção e exclusão controlada</h2><p className="feature-intro">Decisões fiscais e operações duráveis permanecem sob autoridade do servidor.</p></div><Button variant="secondary" onClick={onReload} disabled={loading}>{loading ? "Atualizando…" : "Atualizar retenção"}</Button></div>
      <p className="feature-context">A prévia é somente metadados; ela não exclui documentos nem substitui a revalidação do owner.</p>
      {loading && <Feedback state="loading" message="Carregando decisões de retenção…" />}
      {stale && <div className="feature-stale" role="status"><Badge variant="warning">Leitura desatualizada</Badge><span>A última decisão segura permanece visível enquanto o servidor é consultado.</span></div>}
      {error && <div className="feature-actions"><Feedback state="unavailable" message={error} /><Button variant="secondary" onClick={onRetry}>Tentar novamente</Button></div>}
      {retention && <Panel title="Decisões do escopo" className="feature-panel">
        <div className="feature-pagination" role="status"><span>{retention.documents.length} decisão(ões) nesta página; data-base fornecida pelo servidor.</span>{retention.next_cursor && <Button variant="secondary" onClick={onNextPage} disabled={loading}>Próxima página</Button>}</div>
        {retention.documents.length === 0 ? <Feedback state="empty" message="Nenhum documento possui decisão neste escopo limitado." /> : <DataTable caption="Decisões de retenção" className="admin-table">
          <thead><tr><th>Documento</th><th>Família</th><th>Decisão</th><th>Elegível em</th><th>Regra</th><th>Ação</th></tr></thead>
          <tbody>{retention.documents.map((item) => <tr key={item.id}>
            <td>Documento do escopo informado pelo servidor<br /><small>{retentionFieldLabel(item.category)} · {retentionFieldLabel(item.flow)}</small></td>
            <td>{item.family === "nfe" ? "NF-e" : item.family === "nfse" ? "NFS-e" : "Família não reconhecida"}</td>
            <td><Badge variant={retentionVariant(item.state)}>{retentionStateLabel(item.state)}</Badge><br /><small>{retentionReasonLabel(item.reason_code)}</small></td>
            <td>{item.eligibility_date ?? "Não informada"}</td>
            <td>{item.rule_version || "Regra não informada"}</td>
            <td><Button variant="secondary" onClick={() => onPreview(item)} disabled={previewLoading}>Ver prévia</Button></td>
          </tr>)}</tbody>
        </DataTable>}
      </Panel>}
      {previewLoading && <Feedback state="loading" message="Gerando prévia segura…" />}
      {previewError && <div className="feature-actions"><Feedback state={previewStale ? "blocked" : "error"} message={previewError} /><Button variant="secondary" onClick={onRetryPreview}>Tentar nova prévia</Button></div>}
      {preview && <Panel as="aside" title="Prévia de retenção" className={`feature-panel retention-preview${previewStale ? " is-stale" : ""}`}>
        {previewStale && <Feedback state="blocked" message="Esta prévia ficou desatualizada; uma nova prévia é obrigatória antes de qualquer ação." />}
        <div className="feature-summary"><Badge variant={retentionVariant(preview.decision.state)}>{retentionStateLabel(preview.decision.state)}</Badge><span>{safePreviewReason(preview)}</span></div>
        <p><strong>Escopo:</strong> versão {preview.scope.version} · hash de escopo preservado para revalidação.</p>
        <p><strong>Evidências limitadas:</strong> {preview.evidence.length} original/XML · {preview.events.length} evento(s) · {preview.renders.length} derivado(s). Conteúdo fiscal não é copiado para a interface.</p>
        <p>{preview.deletion.message}</p>
        {eligibleCurrentPreview && <Button variant="danger" onClick={onOpenDeleteDialog}>Preparar solicitação de exclusão</Button>}
        {!eligibleCurrentPreview && preview.decision.state !== "eligible" && <Feedback state="blocked" message="Esta decisão não pode iniciar exclusão controlada." />}
        <Button variant="secondary" onClick={onReload}>Atualizar decisão</Button>
      </Panel>}
      {deleteDialogOpen && preview && <Panel as="aside" title="Confirmar exclusão controlada" role="dialog" aria-modal="true" aria-describedby="retencao-confirmacao-consequencia" className="admin-dialog">
        <p><strong>Alvo seguro:</strong> o documento e os artefatos enumerados na prévia atual.</p>
        <p id="retencao-confirmacao-consequencia">A operação é manual, auditada e pode exigir recuperação. Nenhum estado local será tratado como exclusão concluída.</p>
        <Field id="retencao-motivo" label="Motivo bounded" hint="Obrigatório e enviado ao servidor." required><textarea value={reason} maxLength={1000} onChange={(event) => onReasonChange(event.target.value)} required /></Field>
        <p className="feature-context">A confirmação explícita será vinculada automaticamente à versão e ao escopo atuais; o servidor fará a revalidação final.</p>
        <div className="feature-actions"><Button variant="danger" onClick={onConfirmDelete} disabled={!confirmationReady}>Confirmar solicitação</Button><Button variant="secondary" onClick={onCancelDelete}>Cancelar</Button></div>
      </Panel>}
      {operationLoading && <Feedback state="loading" message="Consultando estado da operação…" />}
      {operationError && <Feedback state="error" message={operationError} />}
      {operation && <Panel as="aside" title="Estado da exclusão controlada" className="feature-panel deletion-operation">
        <div className="feature-summary"><Badge variant={operationVariant(operation.state)}>{deletionStateLabel(operation.state)}</Badge><span>{operation.state === "completed" ? "O servidor confirmou o encerramento da operação." : "O servidor ainda não confirmou exclusão concluída."}</span></div>
        <p><strong>Escopo:</strong> versão {operation.scope.version} preservada para auditoria.</p>
        <p><strong>Etapa:</strong> {deletionStepLabel(operation.current_step)}</p>
        {operation.safe_error && <Feedback state={operation.state === "recovery_required" ? "critical-action" : "error"} message={deletionErrorLabel(operation.safe_error)} />}
        <div className="feature-actions"><Button variant="secondary" onClick={onRefreshOperation} disabled={operationLoading}>Atualizar estado</Button>{(operation.state === "recovery_required" || operation.state === "failed") && <Button variant="danger" onClick={onResumeOperation} disabled={operationLoading}>Solicitar recuperação</Button>}</div>
      </Panel>}
    </section>
  );
}

function retentionQueryFromLocation(): URLSearchParams {
  const current = new URLSearchParams(window.location.search);
  const query = new URLSearchParams();
  const state = current.get("state");
  const family = current.get("family");
  if (state && ["retained", "eligible", "non_executable"].includes(state)) query.set("state", state);
  if (family && ["nfe", "nfse"].includes(family)) query.set("family", family);
  for (const key of ["cursor", "as_of"]) if (current.get(key)) query.set(key, current.get(key)!);
  return query;
}

export function RetentionSection({ loadSignal, notify }: { loadSignal: number; notify: (message: string) => void }) {
  const [retention, setRetention] = useState<RetentionResponse | null>(null);
  const [preview, setPreview] = useState<RetentionPreview | null>(null);
  const [operation, setOperation] = useState<DeletionOperation | null>(null);
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [operationLoading, setOperationLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [previewStale, setPreviewStale] = useState(false);
  const [error, setError] = useState("");
  const [previewError, setPreviewError] = useState("");
  const [operationError, setOperationError] = useState("");
  const [reason, setReason] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const listSequence = useRef(0);
  const previewSequence = useRef(0);
  const operationSequence = useRef(0);
  const retentionRef = useRef<RetentionResponse | null>(null);
  const previewItemRef = useRef<RetentionItem | null>(null);

  const loadRetention = useCallback(async (query = retentionQueryFromLocation()) => {
    const requestId = ++listSequence.current;
    setLoading(true); setError(""); setStale(retentionRef.current !== null);
    try {
      const payload = await listRetention(new URLSearchParams(query));
      if (requestId !== listSequence.current) return;
      const previousItem = preview && payload.documents.find((item) => item.id === preview.document.id);
      if (previousItem && previousItem.scope_hash !== preview.scope.hash) setPreviewStale(true);
      retentionRef.current = payload; setRetention(payload); setStale(false);
    } catch (caught: unknown) {
      if (requestId !== listSequence.current) return;
      setError(caught instanceof ApiError && caught.status === 403 ? "A sessão sem permissão não pode consultar retenção." : "A retenção está indisponível; a última decisão segura continua visível.");
      setStale(retentionRef.current !== null); notify("Não foi possível consultar a retenção.");
    } finally { if (requestId === listSequence.current) setLoading(false); }
  }, [notify, preview]);

  useEffect(() => { if (loadSignal > 0 || window.location.hash === "#retencao" || retentionQueryFromLocation().toString()) void loadRetention(); }, [loadRetention, loadSignal]);
  useEffect(() => {
    const loadLocation = () => { if (window.location.hash === "#retencao" || retentionQueryFromLocation().toString()) void loadRetention(); };
    window.addEventListener("hashchange", loadLocation); window.addEventListener("popstate", loadLocation);
    return () => { window.removeEventListener("hashchange", loadLocation); window.removeEventListener("popstate", loadLocation); };
  }, [loadRetention]);

  async function showPreview(item: RetentionItem) {
    previewItemRef.current = item;
    const requestId = ++previewSequence.current;
    setPreviewLoading(true); setPreviewError(""); setPreviewStale(false); setDeleteDialogOpen(false);
    try {
      const payload = await getRetentionPreview(item.id, item.scope_hash);
      if (requestId !== previewSequence.current) return;
      setPreview(payload); setReason("");
    } catch (caught: unknown) {
      if (requestId !== previewSequence.current) return;
      const staleResponse = caught instanceof ApiError && caught.status === 409;
      setPreviewStale(staleResponse);
      setPreviewError(staleResponse ? "A prévia está desatualizada; consulte uma nova prévia." : "Não foi possível gerar a prévia segura.");
      notify("Não foi possível gerar a prévia de retenção.");
    } finally { if (requestId === previewSequence.current) setPreviewLoading(false); }
  }

  async function confirmDeletion() {
    if (!preview || previewStale || preview.decision.state !== "eligible" || !reason.trim()) return;
    setOperationLoading(true); setOperationError("");
    try {
      const created = await requestDeletion(preview.document.id, { scope_hash: preview.scope.hash, scope_version: preview.scope.version, confirmation: confirmationFor(preview), reason });
      setOperation(created); setDeleteDialogOpen(false); notify("Solicitação de exclusão enviada ao servidor.");
    } catch (caught: unknown) {
      const staleResponse = caught instanceof ApiError && caught.status === 409;
      if (staleResponse) setPreviewStale(true);
      const message = staleResponse ? "A prévia mudou ou a operação foi bloqueada; gere uma nova prévia." : "A solicitação não foi aceita pelo servidor.";
      setOperationError(message); notify(message);
      await loadRetention();
    } finally { setOperationLoading(false); }
  }

  function retryPreview() {
    if (previewItemRef.current) void showPreview(previewItemRef.current);
  }

  async function refreshOperation() {
    if (!operation || operationLoading) return;
    const requestId = ++operationSequence.current;
    setOperationLoading(true); setOperationError("");
    try { const payload = await getDeletionStatus(operation.id); if (requestId === operationSequence.current) setOperation(payload); }
    catch { if (requestId === operationSequence.current) { setOperationError("Não foi possível consultar o estado seguro da operação."); notify("Não foi possível consultar a exclusão controlada."); } }
    finally { if (requestId === operationSequence.current) setOperationLoading(false); }
  }

  async function resumeOperation() {
    if (!operation || operationLoading || !["recovery_required", "failed"].includes(operation.state)) return;
    const requestId = ++operationSequence.current;
    setOperationLoading(true); setOperationError("");
    try { const payload = await resumeDeletion(operation.id); if (requestId === operationSequence.current) { setOperation(payload); notify("Recuperação solicitada ao servidor."); } }
    catch { if (requestId === operationSequence.current) { setOperationError("Não foi possível solicitar a recuperação."); notify("Não foi possível retomar a exclusão controlada."); } }
    finally { if (requestId === operationSequence.current) setOperationLoading(false); }
  }

  function nextPage() {
    if (!retention?.next_cursor) return;
    const query = retentionQueryFromLocation(); query.set("cursor", retention.next_cursor);
    window.history.pushState(null, "", `${window.location.pathname}?${query.toString()}${window.location.hash || "#retencao"}`);
    void loadRetention(query);
  }

  return <RetentionPresentation retention={retention} preview={preview} operation={operation} loading={loading} previewLoading={previewLoading} operationLoading={operationLoading} stale={stale} previewStale={previewStale} error={error} previewError={previewError} operationError={operationError} reason={reason} deleteDialogOpen={deleteDialogOpen} onReload={() => void loadRetention()} onRetry={() => void loadRetention()} onRetryPreview={retryPreview} onPreview={showPreview} onNextPage={nextPage} onReasonChange={setReason} onOpenDeleteDialog={() => setDeleteDialogOpen(true)} onCancelDelete={() => setDeleteDialogOpen(false)} onConfirmDelete={() => void confirmDeletion()} onRefreshOperation={() => void refreshOperation()} onResumeOperation={() => void resumeOperation()} />;
}
