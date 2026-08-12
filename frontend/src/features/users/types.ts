import { Role, User } from "../auth/types";

export type ManagedUser = User & {
  email: string;
  active: boolean;
  version: number;
};

export type UserListResponse = {
  users: ManagedUser[];
  next_cursor: string | null;
};

export type UserCriticalActionKind = "role" | "password-reset" | "activate" | "deactivate";

export type UserCriticalAction = {
  kind: UserCriticalActionKind;
  user: ManagedUser;
  role: Role;
  active: boolean;
  reason: string;
  password: string;
};

export type UserForm = {
  name: string;
  email: string;
  role: Role;
  password: string;
};

export type OwnPasswordForm = {
  current_password: string;
  password: string;
};
