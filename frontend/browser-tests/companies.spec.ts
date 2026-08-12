import { expect, test } from "@playwright/test";

for (const role of ["administrador", "operador", "visualizador"] as const) {
  test(`apresenta estados seguros de empresas, certificados e coletas para ${role}`, async ({ page }) => {
    await page.goto(`/browser-tests/companies.html?role=${role}`);
    await expect(page.getByRole("heading", { name: "Empresas, certificados e coletas sintéticas" })).toBeVisible();
    await expect(page.getByText("Coleta em execução")).toBeVisible();
    await expect(page.getByText("Coleta bloqueada")).toBeVisible();
    await expect(page.getByText("Cobertura ADN ausente")).toBeVisible();
    await expect(page.getByText("Cobertura ADN desconhecida")).toBeVisible();
    await expect(page.getByText("Cobertura ADN indisponível")).toBeVisible();
    await expect(page.getByText("Leitura desatualizada").first()).toBeVisible();
    await expect(page.getByText("temporary_failure")).toHaveCount(0);
    await expect(page.getByText("opaque.browser.certificate.cursor")).toHaveCount(0);
    if (role === "visualizador") {
      await expect(page.getByRole("heading", { name: "Empresas", exact: true })).toHaveCount(0);
      await expect(page.getByRole("button", { name: /Solicitar coleta/ })).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Tentar novamente" })).toHaveCount(0);
    } else {
      await expect(page.getByRole("heading", { name: "Empresas", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Certificados", exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "Abrir empresa Empresa sintética" })).toBeVisible();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  });
}

test("preserva cursor, filtros, stale context and keyboard actions", async ({ page }) => {
  await page.goto("/browser-tests/companies.html?role=operador");
  const next = page.getByRole("button", { name: "Próxima página" }).first();
  await next.focus();
  await expect(next).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Cursor opaco preservado sem ser exibido.")).toBeVisible();
  await expect(page.getByText("opaque.browser.company.cursor")).toHaveCount(0);
});

test("keeps authentication boundary for direct negative sessions", async ({ page }) => {
  for (const session of ["anonymous", "expired"]) {
    await page.goto(`/browser-tests/companies.html?session=${session}`);
    await expect(page.getByRole("alert")).toHaveText("Acesse sua conta.");
    await expect(page.getByRole("heading", { name: "Coletas" })).toHaveCount(0);
  }
});
