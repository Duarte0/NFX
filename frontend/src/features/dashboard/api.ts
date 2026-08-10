import { get } from "../../shared/http";
import { DashboardResponse } from "./types";

export function getDashboard(from?: string, to?: string): Promise<DashboardResponse> {
  const query = new URLSearchParams();
  if (from) query.set("from", from);
  if (to) query.set("to", to);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return get<DashboardResponse>(`/api/dashboard${suffix}`);
}
