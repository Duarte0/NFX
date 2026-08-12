import { useEffect, useState } from "react";
import { AuthShell, AuthenticatedContext } from "./features/auth/AuthShell";
import { User } from "./features/auth/types";
import { AuditSection } from "./features/audit/AuditSection";
import { CollectionsSection } from "./features/collections/CollectionsSection";
import { CompaniesSection } from "./features/companies/CompaniesSection";
import { DocumentsSection } from "./features/documents/DocumentsSection";
import { DashboardSection } from "./features/dashboard/DashboardSection";
import { UsersSection } from "./features/users/UsersSection";
import { RetentionSection } from "./features/retention/RetentionSection";
import { ExportsSection } from "./features/exports/ExportsSection";
import { Button } from "./shared/ui/primitives";

export type Section = "dashboard" | "documents" | "exports" | "companies" | "collections" | "users" | "audit" | "retention";
export type NavigationKey = Section | "certificates";

export type NavigationItem = {
  key: NavigationKey;
  href: `#${string}`;
  label: string;
  loadSection?: Section;
  roles: readonly User["role"][];
};

const authenticatedRoles: readonly User["role"][] = ["administrador", "operador", "visualizador"];
const managementRoles: readonly User["role"][] = ["administrador", "operador"];
const administratorRoles: readonly User["role"][] = ["administrador"];

const navigationModel: readonly NavigationItem[] = [
  { key: "dashboard", href: "#dashboard", label: "Dashboard", loadSection: "dashboard", roles: authenticatedRoles },
  { key: "documents", href: "#documentos", label: "Documentos", loadSection: "documents", roles: authenticatedRoles },
  { key: "exports", href: "#exportacoes", label: "Exportações", loadSection: "exports", roles: authenticatedRoles },
  { key: "companies", href: "#empresas", label: "Empresas", loadSection: "companies", roles: managementRoles },
  { key: "certificates", href: "#certificados", label: "Certificados", roles: managementRoles },
  { key: "collections", href: "#coletas", label: "Coletas", loadSection: "collections", roles: authenticatedRoles },
  { key: "users", href: "#usuarios", label: "Usuários", loadSection: "users", roles: administratorRoles },
  { key: "audit", href: "#auditoria", label: "Auditoria", loadSection: "audit", roles: administratorRoles },
  { key: "retention", href: "#retencao", label: "Retenção", loadSection: "retention", roles: administratorRoles },
];

export function navigationItemsForRole(role: User["role"]): NavigationItem[] {
  return navigationModel.filter((item) => item.roles.includes(role));
}

function hashFromEnvironment(): string {
  return typeof window === "undefined" ? "" : window.location.hash;
}

export function navigationKeyFromHash(hash: string): NavigationKey | null {
  return navigationModel.find((item) => item.href === hash)?.key ?? null;
}

export function AuthenticatedApp({ user, signOut, notify, message }: AuthenticatedContext) {
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
  const [activeKey, setActiveKey] = useState<NavigationKey | null>(() => navigationKeyFromHash(hashFromEnvironment()));
  const canManage = user.role !== "visualizador";
  const isAdmin = user.role === "administrador";
  const navigationItems = navigationItemsForRole(user.role);

  function requestLoad(section: Section) {
    setLoadRequests((current) => ({ ...current, [section]: current[section] + 1 }));
  }

  useEffect(() => {
    const syncActiveNavigation = () => setActiveKey(navigationKeyFromHash(hashFromEnvironment()));
    window.addEventListener("hashchange", syncActiveNavigation);
    return () => window.removeEventListener("hashchange", syncActiveNavigation);
  }, []);

  function selectNavigation(item: NavigationItem) {
    setActiveKey(item.key);
    if (item.loadSection) requestLoad(item.loadSection);
  }

  return (
    <div lang="pt-BR" className="app-shell">
      <a className="app-shell__skip" href="#main-content">Pular para o conteúdo principal</a>
      <header className="app-shell__header">
        <div className="app-shell__brand">
          <p className="app-shell__eyebrow">Gestão fiscal</p>
          <h1>NFX INOV</h1>
        </div>
        <div className="app-shell__identity" aria-label="Identidade da sessão">
          <p>{user.name}</p>
          <p>Papel: {user.role}</p>
        </div>
        <p className="app-shell__context">Horário: Brasília · Valores: R$</p>
        <Button variant="secondary" onClick={() => void signOut()}>Sair</Button>
      </header>
      <aside className="app-shell__sidebar" aria-label="Barra lateral">
        <nav className="app-shell__nav" aria-label="Navegação principal">
          <ul>
            {navigationItems.map((item) => (
              <li key={item.key}>
                <a
                  className={`app-shell__nav-link${activeKey === item.key ? " app-shell__nav-link--active" : ""}`}
                  href={item.href}
                  aria-current={activeKey === item.key ? "page" : undefined}
                  onClick={() => selectNavigation(item)}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <main id="main-content" className="app-shell__main" tabIndex={-1}>
        {message && <p className="app-shell__notification" role="status" aria-live="polite">{message}</p>}
        <DashboardSection loadSignal={loadRequests.dashboard} notify={notify} />
        <DocumentsSection loadSignal={loadRequests.documents} notify={notify} />
        <ExportsSection loadSignal={loadRequests.exports} notify={notify} />
        {canManage && <CompaniesSection loadSignal={loadRequests.companies} notify={notify} />}
        <CollectionsSection canManage={canManage} loadSignal={loadRequests.collections} notify={notify} />
        {isAdmin && <UsersSection loadSignal={loadRequests.users} notify={notify} />}
        {isAdmin && <AuditSection loadSignal={loadRequests.audit} notify={notify} />}
        {isAdmin && <RetentionSection loadSignal={loadRequests.retention} notify={notify} />}
      </main>
    </div>
  );
}

export default function App() {
  return <AuthShell>{(context) => <AuthenticatedApp {...context} />}</AuthShell>;
}
