import { createElement } from "react";
import type { HTMLAttributes } from "react";
import { Badge } from "./primitives.ts";
import type { BadgeVariant } from "./primitives.ts";

export const feedbackStates = [
  "loading",
  "empty",
  "error",
  "unavailable",
  "degraded",
  "blocked",
  "success",
  "critical-action",
] as const;

export type FeedbackState = (typeof feedbackStates)[number];

const stateLabels: Record<FeedbackState, string> = {
  loading: "Carregando",
  empty: "Vazio válido",
  error: "Erro",
  unavailable: "Indisponível",
  degraded: "Degradado",
  blocked: "Bloqueado",
  success: "Sucesso",
  "critical-action": "Ação crítica",
};

const alertStates = new Set<FeedbackState>([
  "error",
  "unavailable",
  "degraded",
  "blocked",
  "critical-action",
]);

const unsafeMessagePatterns = [
  /<\/?[a-z][^>]*>/i,
  /(?:stack trace|traceback|exception|password|secret|token|certificate|object key|payload)/i,
  /(?:^|[\s"'`])(?:[a-z]:\\|\/\/|\/[^/])/i,
  /(?:\.xml|\.pdf)\b/i,
  /-----BEGIN [^-]+-----/i,
];

export function safeFeedbackMessage(message: string, state: FeedbackState): string {
  const normalized = message.trim();
  if (!normalized) return "";
  if (alertStates.has(state) && unsafeMessagePatterns.some((pattern) => pattern.test(normalized))) {
    return "Não foi possível concluir a operação.";
  }
  return normalized;
}

function badgeVariant(state: FeedbackState): BadgeVariant {
  if (state === "success") return "success";
  if (state === "error" || state === "blocked" || state === "critical-action") return "danger";
  if (state === "unavailable" || state === "degraded") return "warning";
  return "info";
}

export type FeedbackProps = Omit<HTMLAttributes<HTMLDivElement>, "children"> & {
  message: string;
  state?: FeedbackState;
  /** Compatibility bridge for existing feature consumers; prefer an explicit state. */
  error?: boolean;
};

export function Feedback({ message, state, error = false, className, ...props }: FeedbackProps) {
  const resolvedState = state ?? (error ? "error" : "success");
  const safeMessage = safeFeedbackMessage(message, resolvedState);
  if (!safeMessage) return null;
  const role = alertStates.has(resolvedState) ? "alert" : "status";

  return createElement(
    "div",
    {
      ...props,
      className: ["ui-feedback", `ui-feedback--${resolvedState}`, className].filter(Boolean).join(" "),
      role,
      "aria-live": role === "alert" ? "assertive" : "polite",
    },
    createElement(Badge, {
      variant: badgeVariant(resolvedState),
      children: stateLabels[resolvedState],
    }),
    createElement("p", null, safeMessage),
  );
}
