import { FormEvent, ReactNode, useEffect, useState } from "react";
import { getSession, login, logout, prepareSession } from "./api";
import { User } from "./types";

export type AuthenticatedContext = {
  user: User;
  message: string;
  signOut: () => Promise<void>;
  notify: (message: string) => void;
};

type AuthShellProps = {
  children: (context: AuthenticatedContext) => ReactNode;
};

export function AuthShell({ children }: AuthShellProps) {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    void prepareSession()
      .then(() => getSession())
      .then((payload) => setUser(payload.user))
      .catch(() => setUser(null));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = await login(email, password);
      setPassword("");
      setMessage("");
      setUser(payload.user);
    } catch {
      setMessage(
        "Não foi possível iniciar a sessão. Verifique suas credenciais.",
      );
    }
  }

  async function signOut() {
    try {
      await logout();
    } catch {
      // The local session is cleared even if the server is unavailable.
    }
    setUser(null);
    setMessage("Sessão encerrada.");
  }

  if (!user) {
    return (
      <main lang="pt-BR">
        <h1>NFX INOV</h1>
        <p>{message || "Acesse sua conta."}</p>
        <form onSubmit={submit}>
          <label>
            E-mail
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Senha
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button type="submit">Entrar</button>
        </form>
      </main>
    );
  }

  return <>{children({ user, message, signOut, notify: setMessage })}</>;
}
