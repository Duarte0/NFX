import { createRoot } from "react-dom/client";
import { AuthenticatedApp } from "../src/App";
import { User } from "../src/features/auth/types";
import "../src/shared/ui/tokens.css";

const role = new URLSearchParams(window.location.search).get("role");
const users: Record<string, User> = {
  administrador: { id: "browser-admin", name: "Administrador sintético", email: "admin@example.test", role: "administrador" },
  operador: { id: "browser-operator", name: "Operador sintético", email: "operator@example.test", role: "operador" },
  visualizador: { id: "browser-viewer", name: "Visualizador sintético", email: "viewer@example.test", role: "visualizador" },
};

const user = users[role ?? ""] ?? users.administrador;

// This fixture mounts the production shell with synthetic identity only. Feature effects see a
// failed local fetch instead of reaching any application or fiscal service.
window.fetch = async () => {
  throw new Error("Browser fixture does not permit network requests");
};

createRoot(document.getElementById("root")!).render(
  <AuthenticatedApp user={user} signOut={async () => undefined} notify={() => undefined} message="" />,
);
