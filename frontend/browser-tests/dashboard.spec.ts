import { expect, test, type Page } from "@playwright/test";

async function openDashboard(page: Page, role: "administrador" | "operador" | "visualizador") {
  await page.goto(`/browser-tests/dashboard.html?role=${role}`);
  await expect(page.getByRole("heading", { name: "Dashboard sintético" })).toBeVisible();
}

test("groups cards and preserves the server period and drill-down URLs", async ({ page }) => {
  await openDashboard(page, "administrador");
  await expect(page.locator(".dashboard-group")).toHaveCount(3);
  await expect(page.getByText("Indicadores fiscais e operacionais")).toBeVisible();
  await expect(page.getByText("Coletas e processamento")).toBeVisible();
  const period = page.locator(".dashboard-period");
  await expect(period.getByText("Período atual")).toBeVisible();
  await expect(period.getByText("Comparativo anterior")).toBeVisible();
  await expect(period.getByText("Fronteira: [from,to)")).toBeVisible();
  await expect(page.locator('a[href="?from=2026-08-01&to=2026-09-01&filter=pending#dashboard"]')).toHaveCount(1);
  await expect(page.getByText("Zero real no período").first()).toBeVisible();
  await expect(page.getByText("Desatualizada").first()).toBeVisible();
});

test("keeps operational health Admin-only and prevents horizontal overflow", async ({ page }) => {
  await openDashboard(page, "administrador");
  await expect(page.getByRole("heading", { name: "Saúde operacional" })).toBeVisible();
  await expect(page.getByText("Banco de dados")).toBeVisible();
  await expect(page.getByText("Backup", { exact: true }).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);

  await openDashboard(page, "operador");
  await expect(page.getByRole("heading", { name: "Saúde operacional" })).toHaveCount(0);
  await expect(page.getByText("Somente Administrador")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
});

test("keeps card links keyboard reachable", async ({ page }) => {
  await openDashboard(page, "visualizador");
  const link = page.locator('a[href="?from=2026-08-01&to=2026-09-01&filter=pending#dashboard"]');
  await link.focus();
  await expect(link).toBeFocused();
  await expect(link).toHaveAttribute("aria-label", "Abrir lista correspondente a Processamento pendente");
});
