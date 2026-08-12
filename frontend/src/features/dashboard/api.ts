import { get } from "../../shared/http";
import { DashboardResponse, JobObservabilityFilter, JobObservabilityResponse } from "./types";

export function getDashboard(from?: string, to?: string): Promise<DashboardResponse> {
  const query = new URLSearchParams();
  if (from) query.set("from", from);
  if (to) query.set("to", to);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return get<DashboardResponse>(`/api/dashboard${suffix}`);
}

export function listJobObservability(
  filter: JobObservabilityFilter,
): Promise<JobObservabilityResponse> {
  const query = new URLSearchParams();
  query.set("from", filter.from);
  query.set("to", filter.to);
  query.set("filter", filter.filter);
  return get<JobObservabilityResponse>(`/api/jobs/observability?${query.toString()}`);
}
