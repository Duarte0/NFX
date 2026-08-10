import { get, post } from "../../shared/http";
import { ManagedUser } from "./types";

export function listUsers(): Promise<{ users: ManagedUser[] }> {
  return get<{ users: ManagedUser[] }>("/api/users");
}

export function createUser(user: {
  name: string;
  email: string;
  role: string;
  password: string;
}): Promise<unknown> {
  return post<unknown>("/api/users/create", user);
}
