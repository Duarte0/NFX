import { get, patch, post } from "../../shared/http";
import { Role } from "../auth/types";
import { ManagedUser, UserListResponse } from "./types";

export function listUsers(query = new URLSearchParams()): Promise<UserListResponse> {
  const params = new URLSearchParams(query);
  if (!params.has("limit")) params.set("limit", "50");
  return get<UserListResponse>(`/api/users?${params.toString()}`);
}

export function createUser(user: {
  name: string;
  email: string;
  role: string;
  password: string;
}): Promise<unknown> {
  return post<unknown>("/api/users/create", user);
}

export function updateUser(
  id: string,
  user: { name: string; email: string; version: number },
): Promise<{ user: ManagedUser }> {
  return patch<{ user: ManagedUser }>(`/api/users/${encodeURIComponent(id)}`, user);
}

export function changeUserRole(
  id: string,
  body: { role: Role; version: number; reason: string },
): Promise<{ user: ManagedUser }> {
  return post<{ user: ManagedUser }>(`/api/users/${encodeURIComponent(id)}/role`, body);
}

export function resetUserPassword(
  id: string,
  body: { password: string; version: number; reason: string },
): Promise<{ user: ManagedUser }> {
  return post<{ user: ManagedUser }>(`/api/users/${encodeURIComponent(id)}/password-reset`, body);
}

export function setUserActive(
  id: string,
  body: { active: boolean; version: number; reason?: string },
): Promise<{ user: ManagedUser }> {
  return post<{ user: ManagedUser }>(`/api/users/${encodeURIComponent(id)}/active`, body);
}

export function changeOwnPassword(body: {
  current_password: string;
  password: string;
}): Promise<{ detail: string }> {
  return post<{ detail: string }>("/api/users/password", body);
}
