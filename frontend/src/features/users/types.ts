import { User } from "../auth/types";

export type ManagedUser = User & {
  email: string;
  active: boolean;
  version: number;
};
