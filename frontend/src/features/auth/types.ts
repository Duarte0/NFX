export type Role = "administrador" | "operador" | "visualizador";

export type User = {
  id: string;
  name: string;
  role: Role;
};
