import { useState } from "react";
import { AuthShell, AuthenticatedContext } from "./features/auth/AuthShell";
import { AuditSection } from "./features/audit/AuditSection";
import { CollectionsSection } from "./features/collections/CollectionsSection";
import { CompaniesSection } from "./features/companies/CompaniesSection";
import { DocumentsSection } from "./features/documents/DocumentsSection";
import { DashboardSection } from "./features/dashboard/DashboardSection";
import { UsersSection } from "./features/users/UsersSection";
import { RetentionSection } from "./features/retention/RetentionSection";
import { ExportsSection } from "./features/exports/ExportsSection";

type Section = "dashboard" | "documents" | "exports" | "companies" | "collections" | "users" | "audit" | "retention";

function AuthenticatedApp({ user, signOut, notify, message }: AuthenticatedContext) {
  const [loadRequests, setLoadRequests] = useState<Record<Section, number>>({
    documents: 0,
    exports: 0,
    dashboard: 0,
    companies: 0,
    collections: 0,
    users: 0,
    audit: 0,
    retention: 0,
  });
  const canManage = user.role !== "visualizador";
  const isAdmin = user.role === "administrador";

  function requestLoad(section: Section) {
    setLoadRequests((current) => ({ ...current, [section]: current[section] + 1 }));
  }

  return (
    <main lang="pt-BR">
      <header>
        <h1>NFX INOV</h1>
        <p>{user.name} · {user.role}</p>
        <button onClick={() => void signOut()}>Sair</button>
      </header>
      <nav aria-label="Navegação principal">
        <a href="#dashboard" onClick={() => requestLoad("dashboard")}>Dashboard</a>
        <a href="#documentos" onClick={() => requestLoad("documents")}>Documentos</a>
        <a href="#exportacoes" onClick={() => requestLoad("exports")}>Exportações</a>
        {canManage && (
          <>
            <a href="#empresas" onClick={() => requestLoad("companies")}>Empresas</a>
            <a href="#certificados">Certificados</a>
          </>
        )}
        <a href="#coletas" onClick={() => requestLoad("collections")}>Coletas</a>
        {isAdmin && (
          <>
            <a href="#usuarios" onClick={() => requestLoad("users")}>Usuários</a>
            <a href="#auditoria" onClick={() => requestLoad("audit")}>Auditoria</a>
            <a href="#retencao" onClick={() => requestLoad("retention")}>Retenção</a>
          </>
        )}
      </nav>
      <p>{message} · Horários em Brasília · valores em R$.</p>
      <DashboardSection loadSignal={loadRequests.dashboard} notify={notify} />
      <DocumentsSection loadSignal={loadRequests.documents} notify={notify} />
      <ExportsSection loadSignal={loadRequests.exports} notify={notify} />
      {canManage && <CompaniesSection loadSignal={loadRequests.companies} notify={notify} />}
      <CollectionsSection canManage={canManage} loadSignal={loadRequests.collections} notify={notify} />
      {isAdmin && <UsersSection loadSignal={loadRequests.users} notify={notify} />}
      {isAdmin && <AuditSection loadSignal={loadRequests.audit} notify={notify} />}
      {isAdmin && <RetentionSection loadSignal={loadRequests.retention} notify={notify} />}
    </main>
  );
}

export default function App() {
  return <AuthShell>{(context) => <AuthenticatedApp {...context} />}</AuthShell>;
}
