import { createRoot } from "react-dom/client";
import { useState } from "react";
import { AuditPresentation } from "../src/features/audit/AuditSection";
import { RetentionPresentation } from "../src/features/retention/RetentionSection";
import { UsersPresentation } from "../src/features/users/UsersSection";
import type { AuditResponse } from "../src/features/audit/types";
import type { DeletionOperation, RetentionResponse } from "../src/features/retention/types";
import type { ManagedUser, UserCriticalAction, UserForm, OwnPasswordForm } from "../src/features/users/types";
import "../src/shared/ui/tokens.css";

const params = new URLSearchParams(window.location.search);
const role = params.get("role") ?? "visualizador";
const session = params.get("session") ?? "authenticated";
const state = params.get("state") ?? "default";
const hash = "redacted-scope-hash";

const user: ManagedUser = {
  id: "user-browser-admin",
  name: "Administrador sintético",
  email: "admin@example.test",
  role: "administrador",
  active: true,
  version: 3,
};
const userForm: UserForm = { name: "", email: "", role: "visualizador", password: "" };
const ownPassword: OwnPasswordForm = { current_password: "", password: "" };
const userResult = { users: [user], next_cursor: null };
const auditResult: AuditResponse = {
  events: [{
    id: "audit-browser-event",
    sequence: 1,
    occurred_at: "2026-08-12T12:00:00+00:00",
    action: "user.deactivate",
    entity_type: "user",
    entity_id: "bounded-by-owner",
    result: "denied",
    reason: "Motivo administrativo sintético",
    actor_id: "bounded-by-owner",
    actor_role: "administrador",
    context: { count: 1, scope: "bounded" },
  }],
  next_cursor: 2,
  integrity: false,
};
const retentionResult: RetentionResponse = {
  documents: [
    { id: "retained-browser", company_id: "company-browser", family: "nfe", category: "document", flow: "distribution", state: "retained", reason_code: "within_retention_period", rule_version: "retention-v1", basis_date: "2026-08-12", eligibility_date: "2037-08-12", calculated_on: "2026-08-12", scope_hash: hash, detail_url: "", preview_url: "" },
    { id: "eligible-browser", company_id: "company-browser", family: "nfse", category: "document", flow: "distribution", state: "eligible", reason_code: "retention_complete", rule_version: "retention-v1", basis_date: "2026-01-01", eligibility_date: "2032-01-01", calculated_on: "2026-08-12", scope_hash: hash, detail_url: "", preview_url: "" },
    { id: "blocked-browser", company_id: "company-browser", family: "nfse", category: "document", flow: "distribution", state: "non_executable", reason_code: "artifact_missing", rule_version: "retention-v1", basis_date: null, eligibility_date: null, calculated_on: "2026-08-12", scope_hash: hash, detail_url: "", preview_url: "" },
  ],
  next_cursor: "opaque.browser.retention.cursor",
  as_of: "2026-08-12",
  rule_version: "retention-v1",
};
const retentionPreview = {
  document: { id: "eligible-browser", company_id: "company-browser", family: "nfse", category: "document", flow: "distribution", emitted_at: "2026-01-01T00:00:00+00:00", authorized_at: null },
  decision: { state: "eligible" as const, reason_code: "retention_complete", rule_version: "retention-v1", basis_date: "2026-01-01", eligibility_date: "2032-01-01", calculated_on: "2026-08-12" },
  scope: { hash, version: "scope-v1" },
  evidence: [{ id: "evidence-browser", artifact_id: "artifact-browser", digest_prefix: "bounded", size_bytes: 12, content_type: "application/xml", availability: "available" as const }],
  events: [],
  renders: [],
  deletion: { authorized: false as const, message: "A prévia não autoriza exclusão." },
};
const recoveryOperation: DeletionOperation = {
  id: "operation-browser",
  target_document_id: "eligible-browser",
  state: "recovery_required",
  scope: { hash, version: "scope-v1" },
  reason: "Motivo sintético",
  current_step: "recovery",
  safe_error: "artifact_divergent",
  result_code: "recovery_required",
  requested_at: "2026-08-12T12:00:00+00:00",
  started_at: null,
  completed_at: null,
  checkpoint: {},
  items: [],
};

function Denied() {
  return <main lang="pt-BR"><h1>Administração</h1><p role="alert">Área administrativa indisponível para esta sessão.</p></main>;
}

function AdminFixture() {
  const [notice, setNotice] = useState("");
  const [pendingAction, setPendingAction] = useState<UserCriticalAction | null>(state === "confirm" ? { kind: "deactivate", user, role: user.role, active: false, reason: "", password: "" } : null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(state === "delete-confirm");
  const [reason, setReason] = useState("Motivo sintético");

  if (role !== "administrador" || session !== "authenticated") return <Denied />;

  return <main lang="pt-BR">
    <h1>Administração sintética</h1>
    {notice && <p role="status">{notice}</p>}
    <UsersPresentation
      result={userResult}
      loading={false}
      stale={state === "stale"}
      error=""
      actionError=""
      createError=""
      ownPasswordError=""
      actionBusy=""
      filters={{ active: "", role: "", cursor: "" }}
      newUser={userForm}
      editUser={{ ...userForm, name: user.name, email: user.email, role: user.role }}
      editingUser={null}
      ownPassword={ownPassword}
      pendingAction={pendingAction}
      onReload={() => setNotice("Atualização solicitada.")}
      onRetry={() => setNotice("Nova tentativa solicitada.")}
      onFilterChange={() => setNotice("Filtros preservados.")}
      onNextPage={() => setNotice("Cursor opaco preservado sem ser exibido.")}
      onCreate={(event) => event.preventDefault()}
      onEdit={(event) => event.preventDefault()}
      onNewUserChange={() => undefined}
      onEditUserChange={() => undefined}
      onOwnPasswordChange={() => undefined}
      onOwnPasswordSubmit={(event) => event.preventDefault()}
      onSelectEdit={() => undefined}
      onRequestAction={(_, kind) => setPendingAction({ kind, user, role: user.role, active: kind === "activate", reason: "", password: "" })}
      onPendingActionChange={setPendingAction}
      onCancelAction={() => setPendingAction(null)}
      onConfirmAction={() => setNotice("Ação crítica enviada ao owner.")}
    />
    <AuditPresentation result={auditResult} filters={{ actor_id: "", action: "", entity_type: "", result: "", cursor: "" }} loading={false} stale={state === "stale"} error="" onReload={() => setNotice("Auditoria atualizada.")} onRetry={() => setNotice("Nova tentativa da auditoria.")} onFilterChange={() => setNotice("Filtros de auditoria preservados.")} onNextPage={() => setNotice("Cursor de auditoria preservado sem ser exibido.")} />
    <RetentionPresentation retention={retentionResult} preview={retentionPreview} operation={recoveryOperation} loading={false} previewLoading={false} operationLoading={false} stale={state === "stale"} previewStale={state === "preview-stale"} error="" previewError="" operationError="" reason={reason} deleteDialogOpen={deleteDialogOpen} onReload={() => setNotice("Retenção atualizada.")} onRetry={() => setNotice("Nova tentativa da retenção.")} onRetryPreview={() => setNotice("Nova prévia solicitada.")} onPreview={() => setNotice("Prévia solicitada.")} onNextPage={() => setNotice("Cursor de retenção preservado sem ser exibido.")} onReasonChange={setReason} onOpenDeleteDialog={() => setDeleteDialogOpen(true)} onCancelDelete={() => setDeleteDialogOpen(false)} onConfirmDelete={() => setNotice("Solicitação de exclusão enviada ao owner.")} onRefreshOperation={() => setNotice("Estado da operação atualizado.")} onResumeOperation={() => setNotice("Recuperação solicitada ao owner.")} />
  </main>;
}

window.fetch = async () => { throw new Error("Browser fixture does not permit network requests"); };
createRoot(document.getElementById("root")!).render(<AdminFixture />);
