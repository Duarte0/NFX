import { cloneElement, createElement } from "react";
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  ReactElement,
  ReactNode,
} from "react";

function classes(...values: Array<string | false | null | undefined>): string | undefined {
  const result = values.filter(Boolean).join(" ");
  return result || undefined;
}

export type ButtonVariant = "primary" | "secondary" | "danger";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  blocked?: boolean;
};

export function Button({
  variant = "primary",
  blocked = false,
  disabled = false,
  className,
  type = "button",
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || blocked;
  return createElement(
    "button",
    {
      ...props,
      type,
      className: classes("ui-button", `ui-button--${variant}`, className),
      disabled: isDisabled,
      "aria-disabled": blocked || undefined,
      "data-blocked": blocked || undefined,
    },
    children,
  );
}

type FieldControlProps = {
  id?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
};

type FieldControl = ReactElement<FieldControlProps>;

export type FieldProps = {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: FieldControl;
};

export function Field({ id, label, hint, error, required = false, children }: FieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const control = cloneElement(children, {
    id,
    "aria-describedby": describedBy,
    "aria-invalid": error ? true : undefined,
  });

  return createElement(
    "div",
    { className: "ui-field" },
    createElement(
      "label",
      { className: "ui-field__label", htmlFor: id },
      label,
      required ? " *" : null,
    ),
    control,
    hint ? createElement("p", { className: "ui-field__hint", id: hintId }, hint) : null,
    error ? createElement("p", { className: "ui-field__error", id: errorId }, error) : null,
  );
}

export type PanelProps = Omit<HTMLAttributes<HTMLElement>, "title"> & {
  as?: "article" | "aside" | "div" | "section";
  title?: ReactNode;
};

export function Panel({ as = "section", title, children, className, ...props }: PanelProps) {
  const titleId = props.id && title ? `${props.id}-title` : undefined;
  return createElement(
    as,
    {
      ...props,
      className: classes("ui-panel", className),
      "aria-labelledby": props["aria-labelledby"] ?? titleId,
    },
    title
      ? createElement("h3", { className: "ui-panel__title", id: titleId }, title)
      : null,
    children,
  );
}

export type DataTableProps = Omit<HTMLAttributes<HTMLTableElement>, "children" | "title"> & {
  caption: string;
  children: ReactNode;
};

export function DataTable({ caption, children, className, ...props }: DataTableProps) {
  return createElement(
    "div",
    { className: "ui-table-wrap" },
    createElement(
      "table",
      { ...props, className: classes("ui-table", className) },
      createElement("caption", null, caption),
      children,
    ),
  );
}

export type BadgeVariant = "brand" | "neutral" | "success" | "warning" | "danger" | "info";

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
  children: ReactNode;
};

export function Badge({ variant = "neutral", className, children, ...props }: BadgeProps) {
  return createElement(
    "span",
    {
      ...props,
      className: classes("ui-badge", `ui-badge--${variant}`, className),
      role: props.role ?? "status",
    },
    children,
  );
}
