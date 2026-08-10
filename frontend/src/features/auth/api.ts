import { get, post } from "../../shared/http";
import { User } from "./types";

export function prepareSession(): Promise<unknown> {
  return get<unknown>("/api/auth/csrf");
}

export function getSession(): Promise<{ user: User }> {
  return get<{ user: User }>("/api/auth/session");
}

export function login(email: string, password: string): Promise<{ user: User }> {
  return post<{ user: User }>("/api/auth/login", { email, password });
}

export function logout(): Promise<unknown> {
  return post<unknown>("/api/auth/logout");
}
