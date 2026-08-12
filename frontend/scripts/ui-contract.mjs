import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import App, { AuthenticatedApp, navigationItemsForRole, navigationKeyFromHash } from "../src/App";
import { DashboardPresentation } from "../src/features/dashboard/DashboardSection";
import { DocumentsPresentation } from "../src/features/documents/DocumentsSection";
import { CompaniesPresentation, companyStatusLabel, flowStateLabel } from "../src/features/companies/CompaniesSection";
import { CertificateInventoryPresentation, certificateFreshnessLabel, certificateStatusLabel } from "../src/features/certificates/CertificateInventoryPanel";
import { CollectionsPresentation, collectionStateLabel, coverageLabel } from "../src/features/collections/CollectionsSection";
import { ExportsPresentation, exportStateLabel } from "../src/features/exports/ExportsSection";
import { UsersPresentation, roleLabel, userActiveLabel } from "../src/features/users/UsersSection";
import { AuditPresentation, auditActionLabel, auditEntityLabel, auditResultLabel } from "../src/features/audit/AuditSection";
import { RetentionPresentation, deletionStateLabel, retentionStateLabel } from "../src/features/retention/RetentionSection";
import { Button, DataTable, Field, Panel, Badge } from "../src/shared/ui/primitives";
import { Feedback, feedbackStates } from "../src/shared/ui/Feedback";

const css = readFileSync(resolve(process.cwd(), "src/shared/ui/tokens.css"), "utf8");
const primitiveSource = readFileSync(resolve(process.cwd(), "src/shared/ui/primitives.ts"), "utf8");
const feedbackSource = readFileSync(resolve(process.cwd(), "src/shared/ui/Feedback.ts"), "utf8");
const appSource = readFileSync(resolve(process.cwd(), "src/App.tsx"), "utf8");
const companiesSource = readFileSync(resolve(process.cwd(), "src/features/companies/CompaniesSection.tsx"), "utf8");
const certificatesSource = readFileSync(resolve(process.cwd(), "src/features/certificates/CertificateInventoryPanel.tsx"), "utf8");
const certificatePanelSource = readFileSync(resolve(process.cwd(), "src/features/certificates/CertificatePanel.tsx"), "utf8");
const collectionsSource = readFileSync(resolve(process.cwd(), "src/features/collections/CollectionsSection.tsx"), "utf8");
const documentsSource = readFileSync(resolve(process.cwd(), "src/features/documents/DocumentsSection.tsx"), "utf8");
const exportsSource = readFileSync(resolve(process.cwd(), "src/features/exports/ExportsSection.tsx"), "utf8");
const usersSource = readFileSync(resolve(process.cwd(), "src/features/users/UsersSection.tsx"), "utf8");
const auditSource = readFileSync(resolve(process.cwd(), "src/features/audit/AuditSection.tsx"), "utf8");
const retentionSource = readFileSync(resolve(process.cwd(), "src/features/retention/RetentionSection.tsx"), "utf8");

function cssVariables(source) {
  return Object.fromEntries(
    [...source.matchAll(/^\s*(--[\w-]+):\s*([^;]+);/gm)].map((match) => [match[1], match[2].trim()]),
  );
}

const variables = cssVariables(css);
const expectedTokens = {
  "--color-brand-700": "#6b1e3b",
  "--color-brand-800": "#4e132b",
  "--color-brand-050": "#f9f1f4",
  "--color-ink": "#1f2937",
  "--color-muted": "#4b5563",
  "--color-line": "#d1d5db",
  "--color-canvas": "#f5f5f5",
  "--color-surface": "#ffffff",
  "--color-white": "#ffffff",
  "--color-success": "#166534",
  "--color-success-surface": "#f0fdf4",
  "--color-warning": "#92400e",
  "--color-warning-surface": "#fffbeb",
  "--color-danger": "#b91c1c",
  "--color-danger-surface": "#fef2f2",
  "--color-info": "#1d4ed8",
  "--color-info-surface": "#eff6ff",
  "--color-focus": "#1d4ed8",
};

for (const [name, value] of Object.entries(expectedTokens)) {
  assert.equal(variables[name]?.toLowerCase(), value, `${name} must remain a documented token`);
}

function relativeLuminance(hex) {
  const channels = [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset + 1, offset + 3), 16) / 255);
  const linear = channels.map((channel) =>
    channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrast(foreground, background) {
  const light = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const dark = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (light + 0.05) / (dark + 0.05);
}

const contrastPairs = [
  ["--color-ink", "--color-surface", 4.5],
  ["--color-muted", "--color-surface", 4.5],
  ["--color-white", "--color-brand-700", 4.5],
  ["--color-white", "--color-brand-800", 4.5],
  ["--color-brand-800", "--color-brand-050", 4.5],
  ["--color-success", "--color-success-surface", 4.5],
  ["--color-warning", "--color-warning-surface", 4.5],
  ["--color-danger", "--color-danger-surface", 4.5],
  ["--color-info", "--color-info-surface", 4.5],
  ["--color-focus", "--color-surface", 3],
];

for (const [foreground, background, minimum] of contrastPairs) {
  const ratio = contrast(variables[foreground], variables[background]);
  assert.ok(ratio >= minimum, `${foreground} on ${background} has contrast ${ratio.toFixed(2)}`);
}

assert.match(css, /:where\(button, input, select, textarea, a, \[tabindex\]\):focus-visible/);
assert.match(css, /border: var\(--border-width\) solid var\(--color-ink\)/);
assert.doesNotMatch(primitiveSource, /#[0-9a-f]{3,8}/i);
assert.doesNotMatch(feedbackSource, /fetch\(|localStorage|sessionStorage|document\.cookie/);

const blockedButton = renderToStaticMarkup(
  React.createElement(Button, { blocked: true, variant: "danger", children: "Excluir" }),
);
const primaryButton = renderToStaticMarkup(React.createElement(Button, { children: "Salvar" }));
const secondaryButton = renderToStaticMarkup(
  React.createElement(Button, { variant: "secondary", children: "Cancelar" }),
);
assert.match(blockedButton, /<button[^>]*disabled=""/);
assert.match(blockedButton, /aria-disabled="true"/);
assert.match(blockedButton, /ui-button--danger/);
assert.match(primaryButton, /ui-button--primary/);
assert.match(secondaryButton, /ui-button--secondary/);

const field = renderToStaticMarkup(
  React.createElement(Field, {
    id: "sample-field",
    label: "Campo",
    hint: "Ajuda sintética",
    error: "Valor inválido",
    children: React.createElement("input", { type: "text" }),
  }),
);
assert.match(field, /<label[^>]*for="sample-field"/);
assert.match(field, /id="sample-field"/);
assert.match(field, /aria-describedby="sample-field-hint sample-field-error"/);
assert.match(field, /aria-invalid="true"/);

const panel = renderToStaticMarkup(
  React.createElement(Panel, { id: "sample-panel", title: "Painel sintético", children: "Conteúdo" }),
);
const table = renderToStaticMarkup(
  React.createElement(DataTable, {
    caption: "Tabela sintética",
    children: React.createElement("tbody", null, React.createElement("tr", null, React.createElement("td", null, "Valor"))),
  }),
);
const badge = renderToStaticMarkup(React.createElement(Badge, { variant: "success", children: "Concluído" }));
assert.match(panel, /<section[^>]*aria-labelledby="sample-panel-title"/);
assert.match(panel, /<h3[^>]*id="sample-panel-title"[^>]*>Painel sintético<\/h3>/);
assert.match(table, /<caption>Tabela sintética<\/caption>/);
assert.match(table, /class="ui-table"/);
assert.match(badge, /role="status"/);

for (const state of feedbackStates) {
  const rendered = renderToStaticMarkup(
    React.createElement(Feedback, { state, message: `Mensagem ${state}` }),
  );
  assert.match(rendered, new RegExp(`ui-feedback--${state}`));
  assert.match(rendered, state === "error" || state === "blocked" || state === "critical-action" || state === "unavailable" || state === "degraded" ? /role="alert"/ : /role="status"/);
  assert.match(rendered, new RegExp(`Mensagem ${state}`));
}

const unsafe = renderToStaticMarkup(
  React.createElement(Feedback, { state: "error", message: "Error: password=synthetic <xml> /internal/file.xml" }),
);
assert.doesNotMatch(unsafe, /password=synthetic|<xml>|internal\/file\.xml/);
assert.match(unsafe, /Não foi possível concluir a operação\./);

const syntheticWindow = {
  location: { hash: "#empresas", search: "" },
  addEventListener() {},
  removeEventListener() {},
};
globalThis.window = syntheticWindow;

const adminUser = { id: "admin", name: "Admin sintético", email: "admin@example.test", role: "administrador" };
const operatorUser = { id: "operator", name: "Operador sintético", email: "operator@example.test", role: "operador" };
const viewerUser = { id: "viewer", name: "Visualizador sintético", email: "viewer@example.test", role: "visualizador" };
const noop = async () => {};
const notify = () => {};

const adminMarkup = renderToStaticMarkup(
  React.createElement(AuthenticatedApp, { user: adminUser, signOut: noop, notify, message: "" }),
);
const operatorMarkup = renderToStaticMarkup(
  React.createElement(AuthenticatedApp, { user: operatorUser, signOut: noop, notify, message: "" }),
);
const viewerMarkup = renderToStaticMarkup(
  React.createElement(AuthenticatedApp, { user: viewerUser, signOut: noop, notify, message: "" }),
);

assert.match(adminMarkup, /<header class="app-shell__header">/);
assert.match(adminMarkup, /<aside class="app-shell__sidebar" aria-label="Barra lateral">/);
assert.match(adminMarkup, /<nav class="app-shell__nav" aria-label="Navegação principal">/);
assert.match(adminMarkup, /<a class="app-shell__skip" href="#main-content">Pular para o conteúdo principal<\/a>/);
assert.match(adminMarkup, /<main id="main-content" class="app-shell__main" tabindex="-1">/);
assert.match(adminMarkup, /href="#empresas"[^>]*aria-current="page"/);
assert.equal((adminMarkup.match(/id="certificados"/g) ?? []).length, 1);

for (const anchor of ["dashboard", "documentos", "exportacoes", "empresas", "certificados", "coletas", "usuarios", "auditoria", "retencao"]) {
  assert.match(adminMarkup, new RegExp(`href="#${anchor}"`), `administrator navigation must publish #${anchor}`);
}

for (const item of navigationItemsForRole("administrador")) assert.match(adminMarkup, new RegExp(`href="${item.href}"`));
for (const item of navigationItemsForRole("operador")) assert.match(operatorMarkup, new RegExp(`href="${item.href}"`));
for (const item of navigationItemsForRole("visualizador")) assert.match(viewerMarkup, new RegExp(`href="${item.href}"`));
assert.doesNotMatch(operatorMarkup, /href="#usuarios"|href="#auditoria"|href="#retencao"/);
assert.doesNotMatch(viewerMarkup, /href="#empresas"|href="#certificados"|href="#usuarios"|href="#auditoria"|href="#retencao"/);
assert.doesNotMatch(viewerMarkup, /id="certificados"/);

assert.equal(navigationKeyFromHash("#dashboard"), "dashboard");
assert.equal(navigationKeyFromHash("#certificados"), "certificates");
assert.equal(navigationKeyFromHash("#empresas"), "companies");
assert.equal(navigationKeyFromHash("#unknown"), null);
assert.match(appSource, /addEventListener\("hashchange"/);
assert.match(appSource, /onClick=\{\(\) => selectNavigation\(item\)\}/);
assert.match(companiesSource, /<section id="certificados"/);
assert.equal((companiesSource.match(/id="certificados"/g) ?? []).length, 1);
assert.doesNotMatch(appSource, /fetch\(|localStorage|sessionStorage|document\.cookie/);

const adminUserRows = [
  { id: "admin-row", name: "Admin sintético", email: "admin@example.test", role: "administrador", active: true, version: 4 },
  { id: "viewer-row", name: "Viewer sintético", email: "viewer@example.test", role: "visualizador", active: false, version: 2 },
];
const usersMarkup = renderToStaticMarkup(React.createElement(UsersPresentation, {
  result: { users: adminUserRows, next_cursor: "opaque.user.cursor" }, loading: true, stale: true, error: "", actionError: "", createError: "E-mail já cadastrado.", ownPasswordError: "", actionBusy: "",
  filters: { active: "", role: "", cursor: "" }, newUser: { name: "", email: "", role: "visualizador", password: "" }, editUser: { name: "Admin sintético", email: "admin@example.test", role: "administrador", password: "" }, editingUser: adminUserRows[0], ownPassword: { current_password: "", password: "" },
  pendingAction: { kind: "deactivate", user: adminUserRows[0], role: "administrador", active: false, reason: "", password: "" },
  onReload: () => {}, onRetry: () => {}, onFilterChange: () => {}, onNextPage: () => {}, onCreate: () => {}, onEdit: () => {}, onNewUserChange: () => {}, onEditUserChange: () => {}, onOwnPasswordChange: () => {}, onOwnPasswordSubmit: () => {}, onSelectEdit: () => {}, onRequestAction: () => {}, onPendingActionChange: () => {}, onCancelAction: () => {}, onConfirmAction: () => {},
}));
assert.match(usersMarkup, /Usuários/);
assert.match(usersMarkup, /Administrador/);
assert.match(usersMarkup, /Visualizador/);
assert.match(usersMarkup, /Leitura desatualizada/);
assert.match(usersMarkup, /Confirmar ação/);
assert.match(usersMarkup, /Cancelar/);
assert.match(usersMarkup, /role="dialog"/);
assert.match(usersMarkup, /aria-labelledby="usuario-acao-dialog-title"/);
assert.match(usersMarkup, /tabindex="-1"/);
assert.doesNotMatch(usersMarkup, /opaque\.user\.cursor|password_hash|synthetic-password/);
assert.equal(roleLabel("administrador"), "Administrador");
assert.equal(userActiveLabel(false), "Desativado");
assert.match(usersSource, /requestSequence/);
assert.match(usersSource, /updateUser\(/);
assert.match(usersSource, /changeUserRole\(/);
assert.match(usersSource, /setUserActive\(/);
assert.match(usersSource, /await loadUsers\(filters\)/);

const auditMarkup = renderToStaticMarkup(React.createElement(AuditPresentation, {
  result: { events: [{ id: "event-synthetic", sequence: 3, occurred_at: "2026-08-12T12:00:00+00:00", action: "user.deactivate", entity_type: "user", entity_id: "sensitive-entity-id", result: "denied", reason: "Motivo administrativo sintético", actor_id: "sensitive-actor-id", actor_role: "administrador", context: { count: 1, scope: "bounded", operation_id: "not-rendered", hash: "not-rendered" } }], next_cursor: 4, integrity: false },
  filters: { actor_id: "", action: "", entity_type: "", result: "", cursor: "" }, loading: true, stale: true, error: "Não foi possível consultar a auditoria.", onReload: () => {}, onRetry: () => {}, onFilterChange: () => {}, onNextPage: () => {},
}));
assert.match(auditMarkup, /Filtros da auditoria/);
assert.match(auditMarkup, /Falha de integridade/);
assert.match(auditMarkup, /Usuário desativado/);
assert.match(auditMarkup, /Negado/);
assert.match(auditMarkup, /Próxima página/);
assert.doesNotMatch(auditMarkup, /sensitive-entity-id|sensitive-actor-id|operation_id|not-rendered|hash/);
assert.equal(auditActionLabel("user.deactivate"), "Usuário desativado");
assert.equal(auditEntityLabel("user"), "Usuário");
assert.equal(auditResultLabel("denied"), "Negado");
assert.match(auditSource, /sequence/);
assert.match(auditSource, /next_cursor/);
assert.match(auditSource, /safeContext/);

const retentionHash = "redacted-scope-hash";
const retentionMarkup = renderToStaticMarkup(React.createElement(RetentionPresentation, {
  retention: { documents: [
    { id: "retained-document", company_id: "company-synthetic", family: "nfe", category: "document", flow: "distribution", state: "retained", reason_code: "within_retention_period", rule_version: "retention-v1", basis_date: "2026-08-12", eligibility_date: "2037-08-12", calculated_on: "2026-08-12", scope_hash: retentionHash, detail_url: "", preview_url: "" },
    { id: "eligible-document", company_id: "company-synthetic", family: "nfse", category: "document", flow: "distribution", state: "eligible", reason_code: "retention_complete", rule_version: "retention-v1", basis_date: "2026-01-01", eligibility_date: "2032-01-01", calculated_on: "2026-08-12", scope_hash: retentionHash, detail_url: "", preview_url: "" },
    { id: "blocked-document", company_id: "company-synthetic", family: "nfse", category: "document", flow: "distribution", state: "non_executable", reason_code: "artifact_missing", rule_version: "retention-v1", basis_date: null, eligibility_date: null, calculated_on: "2026-08-12", scope_hash: retentionHash, detail_url: "", preview_url: "" },
  ], next_cursor: "opaque.retention.cursor", as_of: "2026-08-12", rule_version: "retention-v1" },
  preview: { document: { id: "eligible-document", company_id: "company-synthetic", family: "nfse", category: "document", flow: "distribution", emitted_at: "2026-01-01T00:00:00+00:00", authorized_at: null }, decision: { state: "eligible", reason_code: "retention_complete", rule_version: "retention-v1", basis_date: "2026-01-01", eligibility_date: "2032-01-01", calculated_on: "2026-08-12" }, scope: { hash: retentionHash, version: "scope-v1" }, evidence: [{ id: "evidence", artifact_id: "artifact", digest_prefix: "not-rendered", size_bytes: 12, content_type: "application/xml", availability: "available" }], events: [], renders: [], deletion: { authorized: false, message: "A prévia não autoriza exclusão." } },
  operation: { id: "operation-synthetic", target_document_id: "eligible-document", state: "recovery_required", scope: { hash: retentionHash, version: "scope-v1" }, reason: "Motivo sintético", current_step: "recovery", safe_error: "artifact_divergent", result_code: "recovery_required", requested_at: "2026-08-12T12:00:00+00:00", started_at: null, completed_at: null, checkpoint: {}, items: [] },
  loading: true, previewLoading: false, operationLoading: false, stale: true, previewStale: false, error: "", previewError: "", operationError: "", reason: "Motivo sintético", deleteDialogOpen: true,
  onReload: () => {}, onRetry: () => {}, onRetryPreview: () => {}, onPreview: () => {}, onNextPage: () => {}, onReasonChange: () => {}, onOpenDeleteDialog: () => {}, onCancelDelete: () => {}, onConfirmDelete: () => {}, onRefreshOperation: () => {}, onResumeOperation: () => {},
}));
assert.match(retentionMarkup, /Retido durante o prazo/);
assert.match(retentionMarkup, /Elegível para exclusão manual/);
assert.match(retentionMarkup, /Não executável/);
assert.match(retentionMarkup, /Recuperação necessária/);
assert.match(retentionMarkup, /Confirmar solicitação/);
assert.match(retentionMarkup, /Solicitar recuperação/);
assert.match(retentionMarkup, /A última decisão segura permanece visível/);
assert.match(retentionMarkup, /id="retencao-confirmacao-dialog"/);
assert.match(retentionMarkup, /aria-labelledby="retencao-confirmacao-dialog-title"/);
assert.doesNotMatch(retentionMarkup, /opaque\.retention\.cursor|digest-prefix|not-rendered|aaaaaaaa/);
for (const [state, label] of [["retained", "Retido durante o prazo"], ["eligible", "Elegível para exclusão manual"], ["non_executable", "Não executável"]]) assert.equal(retentionStateLabel(state), label);
for (const [state, label] of [["pending", "Pendente"], ["executing", "Em execução"], ["recovery_required", "Recuperação necessária"], ["failed", "Falha controlada"], ["completed", "Concluída pelo servidor"]]) assert.equal(deletionStateLabel(state), label);
assert.match(retentionSource, /previewSequence/);
assert.match(retentionSource, /operationSequence/);
assert.match(retentionSource, /confirmationFor\(preview\)/);
assert.match(css, /\.ui-table-wrap\s*\{[\s\S]*overflow-x:\s*auto/);

const anonymousMarkup = renderToStaticMarkup(React.createElement(App));
assert.match(anonymousMarkup, /Acesse sua conta\./);
assert.doesNotMatch(anonymousMarkup, /app-shell__sidebar/);

const syntheticDashboard = {
  read_only: true,
  evaluated_at: "2026-08-12T12:00:00+00:00",
  period: {
    current: { from: "2026-08-01", to: "2026-09-01" },
    previous: { from: "2026-07-01", to: "2026-08-01" },
    boundary: "[from,to)",
  },
  cards: [
    {
      id: "companies.active",
      label: "Empresas ativas",
      kind: "snapshot",
      current: { value: 2, status: "ready", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: null,
      status: "ready",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?lifecycle=active#empresas", filters: { lifecycle: "active" } },
    },
    {
      id: "documents.total",
      label: "Documentos no período",
      kind: "period",
      current: { value: 5, status: "ready", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: { value: 0, status: "zero", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      status: "ready",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?from=2026-08-01&to=2026-09-01#documentos", filters: { from: "2026-08-01", to: "2026-09-01" } },
    },
    {
      id: "documents.nfse",
      label: "NFS-e",
      kind: "period",
      current: { value: null, status: "unavailable", freshness: { status: "unknown", evaluated_at: null, age_seconds: null } },
      previous: { value: null, status: "unavailable", freshness: { status: "unknown", evaluated_at: null, age_seconds: null } },
      status: "unavailable",
      freshness: { status: "unknown", evaluated_at: null, age_seconds: null },
      drilldown: null,
    },
    {
      id: "collections.partial",
      label: "Coletas parciais",
      kind: "period",
      current: { value: 1, status: "partial", freshness: { status: "stale", evaluated_at: "2026-08-12T11:00:00+00:00", age_seconds: 3600 } },
      previous: { value: null, status: "unavailable", freshness: { status: "unknown", evaluated_at: null, age_seconds: null } },
      status: "degraded",
      freshness: { status: "stale", evaluated_at: "2026-08-12T11:00:00+00:00", age_seconds: 3600 },
      drilldown: { href: "?from=2026-08-01&to=2026-09-01&state=partial#coletas", filters: { from: "2026-08-01", to: "2026-09-01", state: "partial" } },
    },
    {
      id: "jobs.pending",
      label: "Processamento pendente",
      kind: "period",
      current: { value: 1, status: "ready", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: { value: 0, status: "zero", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      status: "ready",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?from=2026-08-01&to=2026-09-01&filter=pending#dashboard", filters: { from: "2026-08-01", to: "2026-09-01", filter: "pending" } },
    },
    {
      id: "certificates.expired",
      label: "Certificados vencidos",
      kind: "snapshot",
      current: { value: 0, status: "zero", freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 } },
      previous: null,
      status: "zero",
      freshness: { status: "fresh", evaluated_at: "2026-08-12T12:00:00+00:00", age_seconds: 0 },
      drilldown: { href: "?filter=expired#empresas", filters: { filter: "expired" } },
    },
  ],
  capabilities: {
    fiscal_sources: { status: "unavailable", reason: "not_implemented" },
    documents: { status: "available", reason: "persisted_document_contract" },
    rendering: { status: "available", reason: "brazilfiscalreport:1.0.1" },
    backup: { status: "available", reason: "p9_backup_status" },
  },
  operational_health: {
    status: "degraded",
    dependencies: { postgres: "ready", schema: "ready", minio: "unavailable" },
    processes: { worker: { status: "stale", age_seconds: 60 }, scheduler: { status: "ready", age_seconds: 0 } },
    jobs: { status: "ready", queue_counts: { queued: 2, running: 1 } },
    backlog: { status: "delayed", oldest_due_age_seconds: 600 },
    backup: {
      status: "success",
      latest_backup: { state: "complete", safe_error: "" },
      latest_success_age_seconds: 60,
      retention: { daily: 2, weekly: 1, monthly: 1 },
      latest_restore: { state: "success", safe_error: "" },
    },
  },
};

const dashboardMarkup = renderToStaticMarkup(
  React.createElement(DashboardPresentation, {
    dashboard: syntheticDashboard,
    loading: true,
    error: "Não foi possível carregar o dashboard.",
    onRetry: () => {},
    onOpenJobDrilldown: () => {},
  }),
);
assert.match(dashboardMarkup, /dashboard-group-fiscal/);
assert.match(dashboardMarkup, /dashboard-group-processing/);
assert.match(dashboardMarkup, /dashboard-group-certificates/);
assert.match(dashboardMarkup, /Indicadores fiscais e operacionais/);
assert.match(dashboardMarkup, /Coletas e processamento/);
assert.match(dashboardMarkup, /Certificados e capacidades/);
assert.match(dashboardMarkup, /Período atual/);
assert.match(dashboardMarkup, /Comparativo anterior/);
assert.match(dashboardMarkup, /Fronteira: \[from,to\)/);
assert.match(dashboardMarkup, /Zero real no período/);
assert.match(dashboardMarkup, /Não disponível/);
assert.match(dashboardMarkup, /Desatualizada/);
assert.match(dashboardMarkup, /Indisponível/);
assert.match(dashboardMarkup, /A última leitura segura permanece visível/);
assert.match(dashboardMarkup, /Tentar novamente/);
assert.match(dashboardMarkup, /href="\?from=2026-08-01&amp;to=2026-09-01&amp;filter=pending#dashboard"/);
assert.match(dashboardMarkup, /Fontes fiscais/);
assert.match(dashboardMarkup, /Banco de dados/);
assert.match(dashboardMarkup, /Backup/);
assert.doesNotMatch(dashboardMarkup, /fiscal_sources|not_implemented|persisted_document_contract|brazilfiscalreport/);

const viewerDashboard = { ...syntheticDashboard, operational_health: undefined, capabilities: { backup: { status: "admin_only", reason: "restricted" } } };
const viewerDashboardMarkup = renderToStaticMarkup(
  React.createElement(DashboardPresentation, {
    dashboard: viewerDashboard,
    loading: false,
    error: "",
    onRetry: () => {},
    onOpenJobDrilldown: () => {},
  }),
);
assert.doesNotMatch(viewerDashboardMarkup, /dashboard-operational-health|Dependências|Processos|Backlog/);
assert.match(viewerDashboardMarkup, /Somente Administrador/);

const documentItem = {
  id: "document-synthetic-1",
  company_id: "company-synthetic-1",
  company_name: "Empresa sintética",
  family: "nfe",
  role: "entrada",
  category: "document",
  source: "simulator",
  flow: "distribution",
  identity: "doc-synthetic-1",
  identity_kind: "synthetic",
  emitted_at: "2026-08-12T10:00:00+00:00",
  authorized_at: "2026-08-12T10:01:00+00:00",
  competence: "2026-08-01",
  situation: "authorized",
  outcome: "persisted",
  evidence_available: true,
  xml_available: true,
  pdf_available: true,
  pdf_state: "available",
  pdf_error: null,
  detail_url: "/api/documents/document-synthetic-1",
  download_url: "/api/documents/document-synthetic-1/download",
  reason_code: null,
};

const documentResponse = {
  status: "available",
  reason_code: "documents_available",
  documents: [documentItem],
  collection_states: [{ company_id: "company-synthetic-1", family: "nfe", flow: "distribution", status: "available", reason_code: "documents_available" }],
  total: 3,
  limit: 1,
  truncated: true,
  filter: { from: "2026-08-01", to: "2026-09-01", family: "nfe", direction: "entrada" },
  boundary: "[from,to)",
  next_cursor: "opaque.synthetic.cursor",
};

const documentDetail = {
  id: "document-synthetic-1",
  company: { id: "company-synthetic-1", name: "Empresa sintética" },
  family: "nfe",
  role: "entrada",
  category: "document",
  source: "simulator",
  flow: "distribution",
  identity: { kind: "synthetic", value: "doc-synthetic-1" },
  dates: { emitted_at: "2026-08-12T10:00:00+00:00", authorized_at: "2026-08-12T10:01:00+00:00", competence: "2026-08-01" },
  situation: "authorized",
  state: "authorized",
  collection: { origin_execution_ref: "execution-synthetic-1" },
  parties: { issuer: null, recipient: null, provider: null },
  value_total: null,
  artifacts: [{ id: "artifact-synthetic-1", digest_prefix: "redacted", size_bytes: 12, content_type: "application/xml", availability: "available" }],
  events: [{ id: "event-synthetic-1", family: "nfe", category: "substitution", source: "simulator", flow: "distribution", identity: "event-synthetic-1", occurred_at: "2026-08-12T11:00:00+00:00", situation: "cancelled", relationship_type: "substitution", state: "cancelled", artifacts: [] }],
  availability: { xml: true, original: true, pdf: true },
  pdf: { id: "render-synthetic-1", state: "available", safe_error: null, renderer_id: "redacted", renderer_version: "redacted", representation: "danfe", pdf_type: "danfe", digest_prefix: "redacted", size_bytes: 20, content_type: "application/pdf", request_url: "/api/documents/document-synthetic-1/pdf/render", download_url: "/api/documents/document-synthetic-1/pdf" },
  download_url: "/api/documents/document-synthetic-1/download",
};

const documentPresentationProps = {
  documents: documentResponse,
  activeQuery: new globalThis.URLSearchParams("from=2026-08-01&to=2026-09-01&family=nfe&direction=entrada&cursor=opaque.synthetic.cursor"),
  detail: documentDetail,
  loading: false,
  detailLoading: false,
  stale: false,
  error: "",
  queryError: "",
  detailError: "",
  pdfActionError: "",
  selectedDocumentId: documentDetail.id,
  pdfBusyId: null,
  onRetry: () => {},
  onRetryDetail: () => {},
  onNextPage: () => {},
  onSelectDocument: () => {},
  onDownload: () => {},
  onRequestPdf: () => {},
  onCloseDetail: () => {},
};

const documentMarkup = renderToStaticMarkup(
  React.createElement(DocumentsPresentation, documentPresentationProps),
);
assert.match(documentMarkup, /Resultados dos documentos/);
assert.match(documentMarkup, /total informado pelo servidor: 3/);
assert.match(documentMarkup, /Próxima página/);
assert.match(documentMarkup, /Baixar XML/);
assert.match(documentMarkup, /Baixar PDF/);
assert.match(documentMarkup, /Regenerar PDF/);
assert.match(documentMarkup, /Substituição/);
assert.match(documentMarkup, /Cancelado/);
assert.doesNotMatch(documentMarkup, /documents_available|content_hash_mismatch|renderer_id|execution-synthetic-1|object_key/);
assert.match(documentsSource, /listInFlight/);
assert.match(documentsSource, /detailInFlight/);
assert.match(documentsSource, /pdfBusyId/);
assert.match(documentsSource, /document\.pdf\.request_url/);
assert.doesNotMatch(documentsSource, /`\/api\/documents\/\$\{document\.id\}\/pdf`/);

const expectedDocumentStatuses = {
  available: "Documentos disponíveis",
  valid_empty: "Consulta válida sem documentos",
  unavailable: "Documentos indisponíveis",
  no_coverage: "Sem cobertura",
  unknown: "Estado não reconhecido",
  partial: "Resultado parcial",
  retry: "Nova tentativa pendente",
  blocked: "Coleta bloqueada",
};
for (const [status, label] of Object.entries(expectedDocumentStatuses)) {
  const stateMarkup = renderToStaticMarkup(
    React.createElement(DocumentsPresentation, {
      ...documentPresentationProps,
      documents: { ...documentResponse, status, documents: [] },
      detail: null,
      selectedDocumentId: null,
    }),
  );
  assert.match(stateMarkup, new RegExp(label));
  assert.doesNotMatch(stateMarkup, /source_unavailable|collection_blocked|provider details/);
}

for (const pdfState of ["pending", "failed", "unsupported", "unavailable"]) {
  const stateMarkup = renderToStaticMarkup(
    React.createElement(DocumentsPresentation, {
      ...documentPresentationProps,
      detail: { ...documentDetail, pdf: { ...documentDetail.pdf, state: pdfState, download_url: null, safe_error: "renderer_unavailable" } },
    }),
  );
  assert.match(stateMarkup, new RegExp(pdfState === "pending" ? "Em processamento" : pdfState === "failed" ? "Falha na geração" : pdfState === "unsupported" ? "Não suportado" : "Indisponível"));
  assert.doesNotMatch(stateMarkup, /renderer_unavailable/);
}

const staleDocumentMarkup = renderToStaticMarkup(
  React.createElement(DocumentsPresentation, {
    ...documentPresentationProps,
    loading: true,
    stale: true,
    error: "Não foi possível consultar os documentos.",
    detail: null,
    selectedDocumentId: null,
    queryError: "degraded",
  }),
);
assert.match(staleDocumentMarkup, /Leitura desatualizada/);
assert.match(staleDocumentMarkup, /Tentar novamente/);
assert.match(staleDocumentMarkup, /Empresa sintética/);

const syntheticCompany = {
  id: "company-synthetic-1",
  cnpj: "00000000000000",
  legal_name: "Empresa sintética",
  status: "ativa",
  first_collection_at: null,
  deactivation_reason: null,
  version: 2,
  flows: {
    nfe: { id: "flow-nfe", state: "habilitado" },
    nfse: { id: "flow-nfse", state: "pausado" },
  },
  enrichment: {
    status: "sucesso",
    public_non_authoritative: true,
    payload: { should_not_render: true },
    error_code: "",
  },
};
const companyResponse = {
  companies: [syntheticCompany],
  filter: { lifecycle: "active" },
  total: 2,
  limit: 1,
  truncated: true,
  next_cursor: "opaque.company.cursor",
};
const companyMarkup = renderToStaticMarkup(
  React.createElement(CompaniesPresentation, {
    companies: companyResponse.companies,
    companyResult: companyResponse,
    selectedCompany: syntheticCompany,
    loading: false,
    stale: false,
    error: "",
    queryError: "",
    actionBusy: "",
    newCompany: { cnpj: "", legal_name: "" },
    editCompany: { cnpj: syntheticCompany.cnpj, legal_name: syntheticCompany.legal_name },
    onReload: () => {},
    onRetry: () => {},
    onCreate: () => {},
    onEdit: () => {},
    onSelect: () => {},
    onCompanyAction: () => {},
    onToggleFlow: () => {},
    onEnrich: () => {},
    onNewCompanyChange: () => {},
    onEditCompanyChange: () => {},
    children: null,
  }),
);
assert.match(companyMarkup, /Empresas ativas/);
assert.match(companyMarkup, /Empresa ativa/);
assert.match(companyMarkup, /NF-e: Fluxo habilitado/);
assert.match(companyMarkup, /NFS-e: Fluxo pausado/);
assert.match(companyMarkup, /Enriquecimento público não autoritativo/);
assert.match(companyMarkup, /Consulta pública concluída/);
assert.doesNotMatch(companyMarkup, /opaque\.company\.cursor/);
assert.doesNotMatch(companyMarkup, /should_not_render/);
assert.doesNotMatch(companyMarkup, />(?:ativa|habilitado|pausado)</);
for (const [status, label] of [["cadastrada", "Empresa cadastrada"], ["ativa", "Empresa ativa"], ["desativada", "Empresa desativada"]]) {
  assert.equal(companyStatusLabel(status), label);
}
for (const [state, label] of [["habilitado", "Fluxo habilitado"], ["pausado", "Fluxo pausado"]]) {
  assert.equal(flowStateLabel(state), label);
}
const staleCompanyMarkup = renderToStaticMarkup(
  React.createElement(CompaniesPresentation, {
    companies: companyResponse.companies,
    companyResult: companyResponse,
    selectedCompany: syntheticCompany,
    loading: true,
    stale: true,
    error: "Não foi possível carregar empresas.",
    queryError: "unavailable",
    actionBusy: "",
    newCompany: { cnpj: "", legal_name: "" },
    editCompany: { cnpj: syntheticCompany.cnpj, legal_name: syntheticCompany.legal_name },
    onReload: () => {},
    onRetry: () => {},
    onCreate: () => {},
    onEdit: () => {},
    onSelect: () => {},
    onCompanyAction: () => {},
    onToggleFlow: () => {},
    onEnrich: () => {},
    onNewCompanyChange: () => {},
    onEditCompanyChange: () => {},
    children: null,
  }),
);
assert.match(staleCompanyMarkup, /Leitura desatualizada/);
assert.match(staleCompanyMarkup, /Tentar novamente/);
assert.match(staleCompanyMarkup, /Empresa sintética/);
assert.match(companiesSource, /companyRequestSequence/);
assert.match(companiesSource, /actionBusy/);
assert.match(companiesSource, /popstate/);
assert.match(companiesSource, /next_cursor/);

const inventoryResponse = {
  certificates: [
    {
      id: "certificate-synthetic-1",
      company: { id: "company-synthetic-1", cnpj: "00000000000000", legal_name: "Empresa sintética" },
      state: "current",
      status: "proximo_vencimento",
      not_before: "2026-01-01T00:00:00+00:00",
      not_after: "2026-08-20T00:00:00+00:00",
      days_until_expiry: 8,
    },
  ],
  filter: { filter: "expiring" },
  evaluated_at: "2026-08-12T12:00:00+00:00",
  freshness: { status: "stale", evaluated_at: "2026-08-12T11:00:00+00:00", age_seconds: 3600 },
  total: 3,
  limit: 1,
  truncated: true,
  next_cursor: "opaque.certificate.cursor",
};
const inventoryMarkup = renderToStaticMarkup(
  React.createElement(CertificateInventoryPresentation, {
    filter: "expiring",
    cursor: "opaque.certificate.cursor",
    result: inventoryResponse,
    loading: false,
    stale: true,
    error: "",
    queryError: "",
    onFilterChange: () => {},
    onReload: () => {},
    onRetry: () => {},
    onNextPage: () => {},
  }),
);
assert.match(inventoryMarkup, /Certificados próximos do vencimento/);
assert.match(inventoryMarkup, /Certificado próximo do vencimento/);
assert.match(inventoryMarkup, /Leitura desatualizada/);
assert.match(inventoryMarkup, /Próxima página/);
assert.doesNotMatch(inventoryMarkup, /opaque\.certificate\.cursor/);
assert.doesNotMatch(inventoryMarkup, /fingerprint_sha256|certificate_cnpj|password|payload/);
for (const [status, label] of [
  ["valido", "Certificado válido"],
  ["proximo_vencimento", "Certificado próximo do vencimento"],
  ["expirado", "Certificado vencido"],
  ["invalido", "Certificado inválido"],
  ["falha_armazenamento", "Certificado indisponível para armazenamento"],
]) {
  assert.equal(certificateStatusLabel(status), label);
}
for (const [freshness, label] of [["fresh", "Leitura atual"], ["stale", "Leitura desatualizada"], ["unknown", "Atualidade não determinada"]]) {
  assert.equal(certificateFreshnessLabel(freshness), label);
}
assert.match(certificatesSource, /next_cursor/);
assert.match(certificatesSource, /certificateRequestSequence/);
assert.match(certificatesSource, /popstate/);
assert.match(certificatePanelSource, /uploadBusy/);

const collectionFlow = (family, collection_state, coverage) => ({
  family,
  flow_state: "habilitado",
  collection_state,
  last_attempt_at: "2026-08-12T10:00:00+00:00",
  last_success_at: null,
  next_scheduled_at: null,
  cooldown_until: null,
  blocked_reason: "policy_block",
  safe_error: "temporary_failure",
  progress: { current: 2, total: 4 },
  coverage,
  active_execution: null,
  latest_execution: { id: `execution-${family}`, state: collection_state, safe_error: "temporary_failure", origin: "manual" },
});
const collectionResponse = {
  collections: [{
    company_id: "company-synthetic-1",
    legal_name: "Empresa sintética",
    status: "ativa",
    flows: [
      collectionFlow("nfe", "running", null),
      collectionFlow("nfse", "blocked", { status: "none", source: "synthetic", verified_at: "2026-08-12T10:00:00+00:00", policy_version: "synthetic-policy" }),
      collectionFlow("nfse", "partial", { status: "unknown", source: "synthetic", verified_at: "2026-08-12T10:00:00+00:00", policy_version: "synthetic-policy" }),
      collectionFlow("nfse", "failed", { status: "error", source: "synthetic", verified_at: "2026-08-12T10:00:00+00:00", policy_version: "synthetic-policy" }),
    ],
  }],
};
const executionResponse = {
  read_only: true,
  filter: { from: "2026-08-01", to: "2026-09-01", state: "partial" },
  boundary: "[from,to)",
  total: 4,
  limit: 100,
  truncated: false,
  executions: [
    { id: "execution-synthetic", company_id: "company-synthetic-1", company_name: "Empresa sintética", family: "nfe", requested_scope: "nfe", state: "partial", outcome: "partial", recovery: "retry", safe_error: "partial_result", created_at: "2026-08-12T10:00:00+00:00", started_at: null, finished_at: null },
    { id: "execution-blocked", company_id: "company-synthetic-1", company_name: "Empresa sintética", family: "nfse", requested_scope: "nfse", state: "blocked", outcome: "permanent_failure", recovery: "blocked", safe_error: "permanent_failure", created_at: "2026-08-12T10:00:00+00:00", started_at: null, finished_at: null },
  ],
};
const collectionMarkup = renderToStaticMarkup(
  React.createElement(CollectionsPresentation, {
    companies: collectionResponse.collections,
    executionResult: executionResponse,
    executionFilter: executionResponse.filter,
    executionLoading: false,
    executionStale: true,
    collectionStale: false,
    error: "",
    executionError: "",
    canManage: true,
    actionBusy: "",
    onReload: () => {},
    onRetry: () => {},
    onFilterChange: () => {},
    onRequest: () => {},
    onRetryCollection: () => {},
  }),
);
assert.match(collectionMarkup, /Cobertura ADN ausente/);
assert.match(collectionMarkup, /Cobertura ADN desconhecida/);
assert.match(collectionMarkup, /Cobertura ADN indisponível/);
assert.match(collectionMarkup, /Coleta em execução/);
assert.match(collectionMarkup, /Coleta parcial/);
assert.match(collectionMarkup, /Coleta bloqueada/);
assert.match(collectionMarkup, /Falha na coleta/);
assert.match(collectionMarkup, /Execução parcial/);
assert.match(collectionMarkup, /Execução bloqueada/);
assert.match(collectionMarkup, /Leitura desatualizada/);
assert.doesNotMatch(collectionMarkup, /temporary_failure|permanent_failure|policy_block/);
for (const [state, label] of [
  ["idle", "Coleta não iniciada"],
  ["queued", "Coleta na fila"],
  ["running", "Coleta em execução"],
  ["concluded", "Coleta concluída"],
  ["empty", "Consulta válida sem documentos"],
  ["partial", "Coleta parcial"],
  ["retrying", "Nova tentativa de coleta agendada"],
  ["cooldown", "Coleta em cooldown"],
  ["blocked", "Coleta bloqueada"],
  ["failed", "Falha na coleta"],
]) {
  assert.equal(collectionStateLabel(state), label);
}
for (const [coverage, label] of [
  [null, "Cobertura ADN não consultada"],
  ["available", "Cobertura ADN disponível"],
  ["none", "Cobertura ADN ausente"],
  ["unknown", "Cobertura ADN desconhecida"],
  ["error", "Cobertura ADN indisponível"],
  ["degraded", "Cobertura ADN degradada"],
]) {
  assert.equal(coverageLabel(coverage), label);
}
const viewerCollectionMarkup = renderToStaticMarkup(
  React.createElement(CollectionsPresentation, {
    companies: collectionResponse.collections,
    executionResult: null,
    executionFilter: null,
    executionLoading: false,
    executionStale: false,
    collectionStale: false,
    error: "",
    executionError: "",
    canManage: false,
    actionBusy: "",
    onReload: () => {},
    onRetry: () => {},
    onFilterChange: () => {},
    onRequest: () => {},
    onRetryCollection: () => {},
  }),
);
assert.doesNotMatch(viewerCollectionMarkup, /Solicitar coleta|Retry/);
assert.match(collectionsSource, /collectionRequestSequence/);
assert.match(collectionsSource, /Promise\.allSettled/);
assert.match(collectionsSource, /popstate/);

const exportStates = [
  ["pending", "Pendente", "Exportação aguardando processamento."],
  ["processing", "Processando", "Exportação em processamento."],
  ["complete", "Concluída", "Exportação concluída, aguardando disponibilização."],
  ["available", "Disponível para download", "Exportação disponível dentro do prazo informado."],
  ["partial", "Parcial", "Exportação parcial: parte do escopo autorizado não foi produzida."],
  ["failed", "Falhou", "A exportação não foi concluída."],
  ["expired", "Expirada", "A exportação expirou; os documentos de origem permanecem no acervo."],
  ["excluded", "Excluída", "Esta exportação não está disponível."],
];
for (const [state, label] of exportStates) assert.equal(exportStateLabel(state), label);

const exportMarkup = renderToStaticMarkup(
  React.createElement(ExportsPresentation, {
    exports: exportStates.map(([state], index) => ({
      id: `export-synthetic-${index}`,
      state,
      expected_count: index === 0 ? 4 : 4,
      produced_count: index === 4 ? 3 : index === 5 ? 0 : 4,
      expected_bytes: 4096,
      produced_bytes: index === 4 ? 3072 : index === 5 ? 0 : 4096,
      created_at: "2026-08-12T10:00:00+00:00",
      expires_at: "2026-08-13T10:00:00+00:00",
      safe_error: index === 4 ? "partial_result" : index === 5 ? "all_items_failed" : null,
      download_url: state === "available" || state === "partial" ? "/api/exports/synthetic/download" : null,
    })),
    listReady: true,
    detail: {
      id: "export-synthetic-4",
      state: "partial",
      expected_count: 4,
      produced_count: 3,
      expected_bytes: 4096,
      produced_bytes: 3072,
      created_at: "2026-08-12T10:00:00+00:00",
      expires_at: "2026-08-13T10:00:00+00:00",
      safe_error: "partial_result",
      download_url: "/api/exports/synthetic/download",
      requester_id: "requester-synthetic",
      filter_snapshot: { family: "nfe", company_ids: ["not-rendered"] },
      selection_snapshot: { document_ids: ["not-rendered"] },
      items: [{ document_id: "not-rendered", state: "missing", archive_path: "/not-rendered", safe_error: "source_missing", size_bytes: 1024 }],
    },
    loading: true,
    stale: true,
    error: "",
    detailLoading: false,
    detailStale: true,
    detailError: "Não foi possível consultar a exportação.",
    requestBusy: true,
    actionBusy: "export-synthetic-4",
    selectedExportId: "export-synthetic-4",
    onRequest: () => {},
    onReload: () => {},
    onRetry: () => {},
    onSelectExport: () => {},
    onRetryDetail: () => {},
    onDownload: () => {},
    onCloseDetail: () => {},
  }),
);
assert.match(exportMarkup, /Pendente/);
assert.match(exportMarkup, /Processando/);
assert.match(exportMarkup, /Concluída/);
assert.match(exportMarkup, /Disponível para download/);
assert.match(exportMarkup, /Parcial/);
assert.match(exportMarkup, /Falhou/);
assert.match(exportMarkup, /Expirada/);
assert.match(exportMarkup, /Excluída/);
assert.match(exportMarkup, /Leitura desatualizada/);
assert.match(exportMarkup, /A última leitura segura permanece visível/);
assert.match(exportMarkup, /Itens produzidos pelo servidor:<\/strong> 3/);
assert.match(exportMarkup, /Itens esperados pelo servidor:<\/strong> 4/);
assert.match(exportMarkup, /A exportação não foi concluída\./);
assert.doesNotMatch(exportMarkup, /partial_result|all_items_failed|source_missing|not-rendered|not-rendered|internal|archive_path/);
assert.doesNotMatch(exportMarkup, /Baixar ZIP[^<]*export-synthetic-4/);
const sparseExportMarkup = renderToStaticMarkup(
  React.createElement(ExportsPresentation, {
    exports: [{
      id: "export-sparse",
      state: "processing",
      expected_count: undefined,
      produced_count: 2,
      expected_bytes: undefined,
      produced_bytes: undefined,
      created_at: undefined,
      expires_at: undefined,
      safe_error: null,
      download_url: null,
    }],
    listReady: true,
    detail: null,
    loading: false,
    stale: false,
    error: "",
    detailLoading: false,
    detailStale: false,
    detailError: "",
    requestBusy: false,
    actionBusy: null,
    selectedExportId: null,
    onRequest: () => {},
    onReload: () => {},
    onRetry: () => {},
    onSelectExport: () => {},
    onRetryDetail: () => {},
    onDownload: () => {},
    onCloseDetail: () => {},
  }),
);
assert.match(sparseExportMarkup, /Itens produzidos pelo servidor:<\/strong> 2/);
assert.doesNotMatch(sparseExportMarkup, /Itens esperados pelo servidor|Bytes produzidos pelo servidor|Bytes esperados pelo servidor|dateTime/);
assert.match(exportsSource, /listRequestSequence/);
assert.match(exportsSource, /detailRequestSequence/);
assert.match(exportsSource, /downloadBusyRef/);
assert.match(exportsSource, /createExport\(\{\}, idempotencyKey\)/);
assert.match(exportsSource, /await loadExports\(true\)/);

console.log(`UI contract verified: ${feedbackStates.length} feedback states, ${contrastPairs.length} contrast pairs, shell landmarks, dashboard groups/states/RBAC, role navigation, anchors, active state, focus and blocked action behavior.`);
