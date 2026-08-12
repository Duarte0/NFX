import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Button, DataTable, Field, Panel, Badge } from "../src/shared/ui/primitives";
import { Feedback, feedbackStates } from "../src/shared/ui/Feedback";

const css = readFileSync(resolve(process.cwd(), "src/shared/ui/tokens.css"), "utf8");
const primitiveSource = readFileSync(resolve(process.cwd(), "src/shared/ui/primitives.ts"), "utf8");
const feedbackSource = readFileSync(resolve(process.cwd(), "src/shared/ui/Feedback.ts"), "utf8");

function cssVariables(source) {
  return Object.fromEntries(
    [...source.matchAll(/^\s*(--[\w-]+):\s*([^;]+);/gm)].map((match) => [match[1], match[2].trim()]),
  );
}

const variables = cssVariables(css);
const expectedTokens = {
  "--color-brand-700": "#6b1e3b",
  "--color-brand-800": "#4e132b",
  "--color-brand-050": "#f9f1f4",
  "--color-ink": "#1f2937",
  "--color-muted": "#4b5563",
  "--color-line": "#d1d5db",
  "--color-canvas": "#f5f5f5",
  "--color-surface": "#ffffff",
  "--color-white": "#ffffff",
  "--color-success": "#166534",
  "--color-success-surface": "#f0fdf4",
  "--color-warning": "#92400e",
  "--color-warning-surface": "#fffbeb",
  "--color-danger": "#b91c1c",
  "--color-danger-surface": "#fef2f2",
  "--color-info": "#1d4ed8",
  "--color-info-surface": "#eff6ff",
  "--color-focus": "#1d4ed8",
};

for (const [name, value] of Object.entries(expectedTokens)) {
  assert.equal(variables[name]?.toLowerCase(), value, `${name} must remain a documented token`);
}

function relativeLuminance(hex) {
  const channels = [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset + 1, offset + 3), 16) / 255);
  const linear = channels.map((channel) =>
    channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrast(foreground, background) {
  const light = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const dark = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (light + 0.05) / (dark + 0.05);
}

const contrastPairs = [
  ["--color-ink", "--color-surface", 4.5],
  ["--color-muted", "--color-surface", 4.5],
  ["--color-white", "--color-brand-700", 4.5],
  ["--color-white", "--color-brand-800", 4.5],
  ["--color-brand-800", "--color-brand-050", 4.5],
  ["--color-success", "--color-success-surface", 4.5],
  ["--color-warning", "--color-warning-surface", 4.5],
  ["--color-danger", "--color-danger-surface", 4.5],
  ["--color-info", "--color-info-surface", 4.5],
  ["--color-focus", "--color-surface", 3],
];

for (const [foreground, background, minimum] of contrastPairs) {
  const ratio = contrast(variables[foreground], variables[background]);
  assert.ok(ratio >= minimum, `${foreground} on ${background} has contrast ${ratio.toFixed(2)}`);
}

assert.match(css, /:where\(button, input, select, textarea, a, \[tabindex\]\):focus-visible/);
assert.match(css, /border: var\(--border-width\) solid var\(--color-ink\)/);
assert.doesNotMatch(primitiveSource, /#[0-9a-f]{3,8}/i);
assert.doesNotMatch(feedbackSource, /fetch\(|localStorage|sessionStorage|document\.cookie/);

const blockedButton = renderToStaticMarkup(
  React.createElement(Button, { blocked: true, variant: "danger", children: "Excluir" }),
);
const primaryButton = renderToStaticMarkup(React.createElement(Button, { children: "Salvar" }));
const secondaryButton = renderToStaticMarkup(
  React.createElement(Button, { variant: "secondary", children: "Cancelar" }),
);
assert.match(blockedButton, /<button[^>]*disabled=""/);
assert.match(blockedButton, /aria-disabled="true"/);
assert.match(blockedButton, /ui-button--danger/);
assert.match(primaryButton, /ui-button--primary/);
assert.match(secondaryButton, /ui-button--secondary/);

const field = renderToStaticMarkup(
  React.createElement(Field, {
    id: "sample-field",
    label: "Campo",
    hint: "Ajuda sintética",
    error: "Valor inválido",
    children: React.createElement("input", { type: "text" }),
  }),
);
assert.match(field, /<label[^>]*for="sample-field"/);
assert.match(field, /id="sample-field"/);
assert.match(field, /aria-describedby="sample-field-hint sample-field-error"/);
assert.match(field, /aria-invalid="true"/);

const panel = renderToStaticMarkup(
  React.createElement(Panel, { id: "sample-panel", title: "Painel sintético", children: "Conteúdo" }),
);
const table = renderToStaticMarkup(
  React.createElement(DataTable, {
    caption: "Tabela sintética",
    children: React.createElement("tbody", null, React.createElement("tr", null, React.createElement("td", null, "Valor"))),
  }),
);
const badge = renderToStaticMarkup(React.createElement(Badge, { variant: "success", children: "Concluído" }));
assert.match(panel, /<section[^>]*aria-labelledby="sample-panel-title"/);
assert.match(panel, /<h3[^>]*id="sample-panel-title"[^>]*>Painel sintético<\/h3>/);
assert.match(table, /<caption>Tabela sintética<\/caption>/);
assert.match(table, /class="ui-table"/);
assert.match(badge, /role="status"/);

for (const state of feedbackStates) {
  const rendered = renderToStaticMarkup(
    React.createElement(Feedback, { state, message: `Mensagem ${state}` }),
  );
  assert.match(rendered, new RegExp(`ui-feedback--${state}`));
  assert.match(rendered, state === "error" || state === "blocked" || state === "critical-action" || state === "unavailable" || state === "degraded" ? /role="alert"/ : /role="status"/);
  assert.match(rendered, new RegExp(`Mensagem ${state}`));
}

const unsafe = renderToStaticMarkup(
  React.createElement(Feedback, { state: "error", message: "Error: password=synthetic <xml> /internal/file.xml" }),
);
assert.doesNotMatch(unsafe, /password=synthetic|<xml>|internal\/file\.xml/);
assert.match(unsafe, /Não foi possível concluir a operação\./);

console.log(`UI contract verified: ${feedbackStates.length} feedback states, ${contrastPairs.length} contrast pairs, semantic primitives, focus and blocked action behavior.`);
