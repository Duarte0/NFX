import { FormEvent, useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { ApiError } from "../../shared/http";
import { createUser, listUsers } from "./api";
import { ManagedUser } from "./types";

type UsersSectionProps = { loadSignal: number; notify: (message: string) => void };

export function UsersSection({ loadSignal, notify }: UsersSectionProps) {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [newUser, setNewUser] = useState({
    name: "",
    email: "",
    role: "visualizador",
    password: "",
  });
  const [error, setError] = useState("");

  const loadUsers = useCallback(async () => {
    try {
      setError("");
      setUsers((await listUsers()).users);
    } catch {
      setError("Não foi possível consultar usuários.");
      notify("Não foi possível consultar usuários.");
    }
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0) void loadUsers();
  }, [loadSignal, loadUsers]);

  async function createManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createUser(newUser);
      setNewUser({ name: "", email: "", role: "visualizador", password: "" });
      await loadUsers();
    } catch (error: unknown) {
      notify(error instanceof ApiError ? error.detail : "Não foi possível criar o usuário.");
    }
  }

  return (
    <section id="usuarios">
      <h2>Usuários</h2>
      <button onClick={() => void loadUsers()}>Atualizar usuários</button>
      <Feedback message={error} state="error" />
      <form onSubmit={createManagedUser}>
        <label>
          Nome
          <input
            value={newUser.name}
            onChange={(event) => setNewUser({ ...newUser, name: event.target.value })}
            required
          />
        </label>
        <label>
          E-mail
          <input
            type="email"
            value={newUser.email}
            onChange={(event) => setNewUser({ ...newUser, email: event.target.value })}
            required
          />
        </label>
        <label>
          Papel
          <select
            value={newUser.role}
            onChange={(event) => setNewUser({ ...newUser, role: event.target.value })}
          >
            <option value="administrador">Administrador</option>
            <option value="operador">Operador</option>
            <option value="visualizador">Visualizador</option>
          </select>
        </label>
        <label>
          Senha inicial
          <input
            type="password"
            value={newUser.password}
            onChange={(event) => setNewUser({ ...newUser, password: event.target.value })}
            required
          />
        </label>
        <button type="submit">Criar usuário</button>
      </form>
      <table>
        <thead>
          <tr><th>Nome</th><th>E-mail</th><th>Papel</th><th>Estado</th></tr>
        </thead>
        <tbody>
          {users.map((item) => (
            <tr key={item.id}>
              <td>{item.name}</td><td>{item.email}</td><td>{item.role}</td>
              <td>{item.active ? "Ativo" : "Desativado"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
