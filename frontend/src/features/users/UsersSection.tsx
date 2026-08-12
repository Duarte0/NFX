import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../../shared/http";
import { Feedback, type FeedbackState } from "../../shared/ui/Feedback";
import { Badge, Button, DataTable, Field, Panel } from "../../shared/ui/primitives";
import { Role } from "../auth/types";
import {
  changeOwnPassword,
  changeUserRole,
  createUser,
  listUsers,
  resetUserPassword,
  setUserActive,
  updateUser,
} from "./api";
import {
  ManagedUser,
  OwnPasswordForm,
  UserCriticalAction,
  UserCriticalActionKind,
  UserForm,
  UserListResponse,
} from "./types";

const roleLabels: Record<Role, string> = {
  administrador: "Administrador",
  operador: "Operador",
  visualizador: "Visualizador",
};

const userErrorMessages: Record<string, string> = {
  "E-mail já cadastrado.": "Este e-mail já está cadastrado.",
  "Usuário alterado por outra solicitação.": "A conta mudou em outra solicitação. A lista foi atualizada.",
  "É necessário manter um Administrador ativo.": "A ação foi bloqueada para manter um Administrador ativo.",
  "Dados inválidos.": "Revise os campos informados.",
  "Não foi possível alterar a senha.": "Não foi possível alterar a senha atual.",
};

type UserQuery = { active: string; role: string; cursor: string };

export type UsersPresentationProps = {
  result: UserListResponse | null;
  loading: boolean;
  stale: boolean;
  error: string;
  actionError: string;
  createError: string;
  ownPasswordError: string;
  actionBusy: string;
  filters: UserQuery;
  newUser: UserForm;
  editUser: UserForm;
  editingUser: ManagedUser | null;
  ownPassword: OwnPasswordForm;
  pendingAction: UserCriticalAction | null;
  onReload: () => void;
  onRetry: () => void;
  onFilterChange: (filters: UserQuery) => void;
  onNextPage: () => void;
  onCreate: (event: FormEvent<HTMLFormElement>) => void;
  onEdit: (event: FormEvent<HTMLFormElement>) => void;
  onNewUserChange: (form: UserForm) => void;
  onEditUserChange: (form: UserForm) => void;
  onOwnPasswordChange: (form: OwnPasswordForm) => void;
  onOwnPasswordSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSelectEdit: (user: ManagedUser) => void;
  onRequestAction: (user: ManagedUser, kind: UserCriticalActionKind) => void;
  onPendingActionChange: (action: UserCriticalAction) => void;
  onCancelAction: () => void;
  onConfirmAction: () => void;
};

export function roleLabel(role: string): string {
  return roleLabels[role as Role] ?? "Papel não reconhecido";
}

export function userActiveLabel(active: boolean): string {
  return active ? "Ativo" : "Desativado";
}

function roleVariant(role: string): "brand" | "info" | "neutral" {
  if (role === "administrador") return "brand";
  if (role === "operador") return "info";
  return "neutral";
}

function userError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Não foi possível concluir a operação.";
  return userErrorMessages[error.detail] ?? (error.status === 403
    ? "A sessão não permite esta operação."
    : error.status === 409
      ? "A conta mudou ou a operação foi bloqueada pelo servidor."
      : "Não foi possível concluir a operação.");
}

function requestState(status: number): { state: FeedbackState; message: string } {
  if (status === 403) return { state: "blocked", message: "A sessão não permite consultar usuários." };
  if (status === 503) return { state: "unavailable", message: "A administração de usuários está indisponível." };
  return { state: "error", message: "A consulta de usuários não foi concluída." };
}

function actionTitle(action: UserCriticalAction): string {
  return {
    role: "Alterar papel",
    "password-reset": "Redefinir senha",
    activate: "Ativar usuário",
    deactivate: "Desativar usuário",
  }[action.kind];
}

function actionConsequence(action: UserCriticalAction): string {
  if (action.kind === "deactivate") return "A conta deixará de autenticar e as sessões existentes serão revogadas pelo servidor.";
  if (action.kind === "activate") return "A conta poderá autenticar novamente somente após a confirmação do servidor.";
  if (action.kind === "password-reset") return "As sessões existentes serão revogadas pelo servidor após a redefinição.";
  return `O papel será alterado para ${roleLabel(action.role)} pelo servidor.`;
}

function actionNeedsReason(kind: UserCriticalActionKind): boolean {
  return kind !== "activate";
}

function UserActionDialog({
  action,
  busy,
  onChange,
  onCancel,
  onConfirm,
}: {
  action: UserCriticalAction;
  busy: boolean;
  onChange: (action: UserCriticalAction) => void;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const reasonRequired = actionNeedsReason(action.kind);
  const canConfirm = !busy && (!reasonRequired || action.reason.trim().length > 0)
    && (action.kind !== "password-reset" || action.password.length > 0);

  return (
    <Panel
      as="aside"
      id="usuario-acao-dialog"
      title={actionTitle(action)}
      role="dialog"
      aria-modal="true"
      aria-describedby="usuario-acao-consequence"
      className="admin-dialog"
    >
      <p><strong>Alvo seguro:</strong> conta administrativa selecionada pelo servidor.</p>
      <p id="usuario-acao-consequence"><strong>{action.user.name}</strong> · {roleLabel(action.user.role)}. {actionConsequence(action)}</p>
      {action.kind === "role" && (
        <Field id="usuario-acao-role" label="Novo papel" required>
          <select value={action.role} onChange={(event) => onChange({ ...action, role: event.target.value as Role })}>
            <option value="administrador">Administrador</option>
            <option value="operador">Operador</option>
            <option value="visualizador">Visualizador</option>
          </select>
        </Field>
      )}
      {action.kind === "password-reset" && (
        <Field id="usuario-acao-password" label="Nova senha" hint="A senha é enviada somente ao servidor; nunca aparece no feedback." required>
          <input
            type="password"
            value={action.password}
            autoComplete="new-password"
            onChange={(event) => onChange({ ...action, password: event.target.value })}
            required
          />
        </Field>
      )}
      {reasonRequired && (
        <Field id="usuario-acao-reason" label="Motivo" hint="O servidor exige um motivo bounded para esta ação." required>
          <textarea value={action.reason} maxLength={1000} onChange={(event) => onChange({ ...action, reason: event.target.value })} required />
        </Field>
      )}
      <div className="feature-actions">
        <Button variant="danger" onClick={onConfirm} disabled={!canConfirm}>{busy ? "Enviando…" : "Confirmar ação"}</Button>
        <Button variant="secondary" onClick={onCancel} disabled={busy}>Cancelar</Button>
      </div>
    </Panel>
  );
}

export function UsersPresentation({
  result,
  loading,
  stale,
  error,
  actionError,
  createError,
  ownPasswordError,
  actionBusy,
  filters,
  newUser,
  editUser,
  editingUser,
  ownPassword,
  pendingAction,
  onReload,
  onRetry,
  onFilterChange,
  onNextPage,
  onCreate,
  onEdit,
  onNewUserChange,
  onEditUserChange,
  onOwnPasswordChange,
  onOwnPasswordSubmit,
  onSelectEdit,
  onRequestAction,
  onPendingActionChange,
  onCancelAction,
  onConfirmAction,
}: UsersPresentationProps) {
  const hasRows = Boolean(result && result.users.length > 0);
  const requestFeedback = error === "forbidden"
    ? requestState(403)
    : error === "unavailable"
      ? requestState(503)
      : requestState(400);
  return (
    <section id="usuarios" className="feature-section">
      <div className="feature-heading">
        <div>
          <p className="feature-eyebrow">Administração</p>
          <h2>Usuários</h2>
          <p className="feature-intro">Contas, papéis e sessões permanecem sob autoridade do servidor.</p>
        </div>
        <Button variant="secondary" onClick={onReload} disabled={loading}>{loading ? "Atualizando…" : "Atualizar usuários"}</Button>
      </div>
      {loading && <Feedback state="loading" message="Carregando usuários…" />}
      {stale && <div className="feature-stale" role="status"><Badge variant="warning">Leitura desatualizada</Badge><span>A última lista segura permanece visível enquanto a consulta é atualizada.</span></div>}
      {error && <div className="feature-actions"><Feedback {...requestFeedback} /><Button variant="secondary" onClick={onRetry}>Tentar novamente</Button></div>}
      <Panel title="Criar usuário" className="feature-panel">
        <form className="feature-form" onSubmit={onCreate}>
          <Field id="novo-usuario-nome" label="Nome" required><input value={newUser.name} onChange={(event) => onNewUserChange({ ...newUser, name: event.target.value })} required /></Field>
          <Field id="novo-usuario-email" label="E-mail" required><input type="email" value={newUser.email} onChange={(event) => onNewUserChange({ ...newUser, email: event.target.value })} required /></Field>
          <Field id="novo-usuario-papel" label="Papel" required>
            <select value={newUser.role} onChange={(event) => onNewUserChange({ ...newUser, role: event.target.value as Role })}>
              <option value="administrador">Administrador</option><option value="operador">Operador</option><option value="visualizador">Visualizador</option>
            </select>
          </Field>
          <Field id="novo-usuario-senha" label="Senha inicial" hint="A senha é write-only e não é exibida após o envio." required><input type="password" autoComplete="new-password" value={newUser.password} onChange={(event) => onNewUserChange({ ...newUser, password: event.target.value })} required /></Field>
          <Button type="submit" disabled={actionBusy === "create"}>{actionBusy === "create" ? "Criando…" : "Criar usuário"}</Button>
        </form>
        {createError && <Feedback state="error" message={createError} />}
      </Panel>
      <Panel title="Filtros da lista" className="feature-panel">
        <div className="feature-filter-form">
          <Field id="usuarios-estado" label="Estado"><select value={filters.active} onChange={(event) => onFilterChange({ ...filters, active: event.target.value, cursor: "" })}><option value="">Todos</option><option value="true">Ativos</option><option value="false">Desativados</option></select></Field>
          <Field id="usuarios-papel-filtro" label="Papel"><select value={filters.role} onChange={(event) => onFilterChange({ ...filters, role: event.target.value, cursor: "" })}><option value="">Todos</option><option value="administrador">Administradores</option><option value="operador">Operadores</option><option value="visualizador">Visualizadores</option></select></Field>
        </div>
      </Panel>
      {result && <Panel title="Contas cadastradas" className="feature-panel">
        <div className="feature-pagination" role="status"><span>{result.users.length} conta(s) nesta página; total limitado pelo servidor.</span>{result.next_cursor && <Button variant="secondary" onClick={onNextPage} disabled={loading}>Próxima página</Button>}</div>
        {!hasRows ? <Feedback state="empty" message="Nenhuma conta corresponde aos filtros informados." /> : (
          <DataTable caption="Usuários administrados" className="admin-table">
            <thead><tr><th>Conta</th><th>Papel</th><th>Estado</th><th>Versão</th><th>Ações</th></tr></thead>
            <tbody>{result.users.map((user) => (
              <tr key={user.id} className={editingUser?.id === user.id ? "is-selected" : undefined}>
                <td><strong>{user.name}</strong><br /><small>{user.email}</small></td>
                <td><Badge variant={roleVariant(user.role)}>{roleLabel(user.role)}</Badge></td>
                <td><Badge variant={user.active ? "success" : "warning"}>{userActiveLabel(user.active)}</Badge></td>
                <td>{user.version}</td>
                <td><div className="feature-actions">
                  <Button variant="secondary" onClick={() => onSelectEdit(user)} aria-label={`Editar ${user.name}`}>Editar</Button>
                  <Button variant="secondary" onClick={() => onRequestAction(user, "role")} disabled={Boolean(actionBusy)}>Alterar papel</Button>
                  <Button variant="secondary" onClick={() => onRequestAction(user, "password-reset")} disabled={Boolean(actionBusy)}>Redefinir senha</Button>
                  <Button variant={user.active ? "danger" : "secondary"} onClick={() => onRequestAction(user, user.active ? "deactivate" : "activate")} disabled={Boolean(actionBusy)}>{user.active ? "Desativar" : "Ativar"}</Button>
                </div></td>
              </tr>
            ))}</tbody>
          </DataTable>
        )}
      </Panel>}
      {editingUser && <Panel title={`Editar conta: ${editingUser.name}`} className="feature-panel">
        <form className="feature-form" onSubmit={onEdit}>
          <Field id="editar-usuario-nome" label="Nome" required><input value={editUser.name} onChange={(event) => onEditUserChange({ ...editUser, name: event.target.value })} required /></Field>
          <Field id="editar-usuario-email" label="E-mail" required><input type="email" value={editUser.email} onChange={(event) => onEditUserChange({ ...editUser, email: event.target.value })} required /></Field>
          <Button type="submit" disabled={actionBusy === "edit"}>{actionBusy === "edit" ? "Salvando…" : "Salvar alterações"}</Button>
          <Button variant="secondary" onClick={() => onSelectEdit(editingUser)}>Cancelar edição</Button>
        </form>
      </Panel>}
      <Panel title="Minha senha" className="feature-panel">
        <form className="feature-form" onSubmit={onOwnPasswordSubmit}>
          <Field id="minha-senha-atual" label="Senha atual" required><input type="password" autoComplete="current-password" value={ownPassword.current_password} onChange={(event) => onOwnPasswordChange({ ...ownPassword, current_password: event.target.value })} required /></Field>
          <Field id="minha-senha-nova" label="Nova senha" hint="A sessão atual será revogada pelo servidor." required><input type="password" autoComplete="new-password" value={ownPassword.password} onChange={(event) => onOwnPasswordChange({ ...ownPassword, password: event.target.value })} required /></Field>
          <Button type="submit" disabled={actionBusy === "own-password"}>{actionBusy === "own-password" ? "Alterando…" : "Alterar minha senha"}</Button>
        </form>
        {ownPasswordError && <Feedback state="error" message={ownPasswordError} />}
      </Panel>
      {actionError && <Feedback state="error" message={actionError} />}
      {pendingAction && <UserActionDialog action={pendingAction} busy={Boolean(actionBusy === "critical")} onChange={onPendingActionChange} onCancel={onCancelAction} onConfirm={onConfirmAction} />}
    </section>
  );
}

export function userQueryFromLocation(): UserQuery {
  const query = new URLSearchParams(window.location.search);
  const active = query.get("active") ?? "";
  const role = query.get("role") ?? "";
  return {
    active: active === "true" || active === "false" ? active : "",
    role: role === "administrador" || role === "operador" || role === "visualizador" ? role : "",
    cursor: query.get("cursor") ?? "",
  };
}

function queryForUsers(filters: UserQuery): URLSearchParams {
  const query = new URLSearchParams(window.location.search);
  for (const key of ["active", "role", "cursor", "limit"]) query.delete(key);
  if (filters.active) query.set("active", filters.active);
  if (filters.role) query.set("role", filters.role);
  if (filters.cursor) query.set("cursor", filters.cursor);
  query.set("limit", "50");
  return query;
}

function friendlyUserError(error: unknown): string {
  return userError(error);
}

export function UsersSection({ loadSignal, notify }: { loadSignal: number; notify: (message: string) => void }) {
  const [result, setResult] = useState<UserListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [createError, setCreateError] = useState("");
  const [ownPasswordError, setOwnPasswordError] = useState("");
  const [actionBusy, setActionBusy] = useState("");
  const [filters, setFilters] = useState<UserQuery>(() => userQueryFromLocation());
  const [newUser, setNewUser] = useState<UserForm>({ name: "", email: "", role: "visualizador", password: "" });
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null);
  const [editUser, setEditUser] = useState<UserForm>({ name: "", email: "", role: "visualizador", password: "" });
  const [ownPassword, setOwnPassword] = useState<OwnPasswordForm>({ current_password: "", password: "" });
  const [pendingAction, setPendingAction] = useState<UserCriticalAction | null>(null);
  const requestSequence = useRef(0);
  const resultRef = useRef<UserListResponse | null>(null);

  const loadUsers = useCallback(async (requestedFilters: UserQuery = userQueryFromLocation()) => {
    const requestId = ++requestSequence.current;
    setLoading(true);
    setError("");
    setStale(resultRef.current !== null);
    try {
      const query = new URLSearchParams();
      if (requestedFilters.active) query.set("active", requestedFilters.active);
      if (requestedFilters.role) query.set("role", requestedFilters.role);
      if (requestedFilters.cursor) query.set("cursor", requestedFilters.cursor);
      const payload = await listUsers(query);
      if (requestId !== requestSequence.current) return;
      resultRef.current = payload;
      setResult(payload);
      setStale(false);
    } catch (caught: unknown) {
      if (requestId !== requestSequence.current) return;
      const status = caught instanceof ApiError ? caught.status : 0;
      setError(status === 403 ? "forbidden" : status === 503 ? "unavailable" : "error");
      setStale(resultRef.current !== null);
      notify(requestState(status).message);
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0 || window.location.hash === "#usuarios" || userQueryFromLocation().toString()) void loadUsers();
  }, [loadSignal, loadUsers]);

  useEffect(() => {
    const loadLocation = () => {
      if (window.location.hash === "#usuarios" || userQueryFromLocation().toString()) {
        const next = userQueryFromLocation();
        setFilters(next);
        void loadUsers(next);
      }
    };
    window.addEventListener("hashchange", loadLocation);
    window.addEventListener("popstate", loadLocation);
    return () => {
      window.removeEventListener("hashchange", loadLocation);
      window.removeEventListener("popstate", loadLocation);
    };
  }, [loadUsers]);

  function changeFilters(next: UserQuery) {
    setFilters(next);
    const query = queryForUsers(next);
    window.history.pushState(null, "", `${window.location.pathname}?${query.toString()}${window.location.hash || "#usuarios"}`);
    void loadUsers(next);
  }

  function nextPage() {
    if (!result?.next_cursor) return;
    changeFilters({ ...filters, cursor: result.next_cursor });
  }

  async function runAction(key: string, operation: () => Promise<void>, onSuccess?: () => void) {
    if (actionBusy) return;
    setActionBusy(key);
    setActionError("");
    try {
      await operation();
      onSuccess?.();
    } catch (caught: unknown) {
      const message = friendlyUserError(caught);
      setActionError(message);
      notify(message);
    } finally {
      await loadUsers(filters);
      setActionBusy("");
    }
  }

  async function createManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (actionBusy) return;
    setActionBusy("create");
    setCreateError("");
    try {
      await createUser(newUser);
      setNewUser({ name: "", email: "", role: "visualizador", password: "" });
      await loadUsers(filters);
      notify("Usuário criado pelo servidor.");
    } catch (caught: unknown) {
      const message = friendlyUserError(caught);
      setCreateError(message);
      notify(message);
      await loadUsers(filters);
    } finally {
      setActionBusy("");
    }
  }

  async function editManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingUser) return;
    await runAction("edit", () => updateUser(editingUser.id, { name: editUser.name, email: editUser.email, version: editingUser.version }).then(() => undefined), () => {
      setEditingUser(null);
      notify("Usuário atualizado pelo servidor.");
    });
  }

  async function submitOwnPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (actionBusy) return;
    setActionBusy("own-password");
    setOwnPasswordError("");
    try {
      await changeOwnPassword(ownPassword);
      setOwnPassword({ current_password: "", password: "" });
      notify("Senha alterada pelo servidor; a sessão foi revogada.");
    } catch (caught: unknown) {
      const message = friendlyUserError(caught);
      setOwnPasswordError(message);
      notify(message);
    } finally {
      setActionBusy("");
    }
  }

  function requestAction(user: ManagedUser, kind: UserCriticalActionKind) {
    setActionError("");
    setPendingAction({ kind, user, role: user.role, active: kind === "activate", reason: "", password: "" });
  }

  async function confirmAction() {
    if (!pendingAction || actionBusy) return;
    const action = pendingAction;
    await runAction("critical", async () => {
      if (action.kind === "role") await changeUserRole(action.user.id, { role: action.role, version: action.user.version, reason: action.reason });
      if (action.kind === "password-reset") await resetUserPassword(action.user.id, { password: action.password, version: action.user.version, reason: action.reason });
      if (action.kind === "activate" || action.kind === "deactivate") await setUserActive(action.user.id, { active: action.active, version: action.user.version, reason: action.reason || undefined });
    }, () => {
      setPendingAction(null);
      notify(`${actionTitle(action)} enviada ao servidor.`);
    });
  }

  function selectEdit(user: ManagedUser) {
    if (editingUser?.id === user.id) {
      setEditingUser(null);
      return;
    }
    setEditingUser(user);
    setEditUser({ name: user.name, email: user.email, role: user.role, password: "" });
  }

  return <UsersPresentation
    result={result}
    loading={loading}
    stale={stale}
    error={error}
    actionError={actionError}
    createError={createError}
    ownPasswordError={ownPasswordError}
    actionBusy={actionBusy}
    filters={filters}
    newUser={newUser}
    editUser={editUser}
    editingUser={editingUser}
    ownPassword={ownPassword}
    pendingAction={pendingAction}
    onReload={() => void loadUsers(filters)}
    onRetry={() => void loadUsers(filters)}
    onFilterChange={changeFilters}
    onNextPage={nextPage}
    onCreate={createManagedUser}
    onEdit={editManagedUser}
    onNewUserChange={setNewUser}
    onEditUserChange={setEditUser}
    onOwnPasswordChange={setOwnPassword}
    onOwnPasswordSubmit={submitOwnPassword}
    onSelectEdit={selectEdit}
    onRequestAction={requestAction}
    onPendingActionChange={setPendingAction}
    onCancelAction={() => { if (!actionBusy) setPendingAction(null); }}
    onConfirmAction={() => void confirmAction()}
  />;
}
