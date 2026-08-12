import { expect, test } from "@playwright/test";

for (const role of ["administrador", "operador", "visualizador"] as const) {
  test(`apresenta consulta, estados e ações de documentos para ${role}`, async ({ page }) => {
    await page.goto(`/browser-tests/documents.html?role=${role}`);
    await expect(page.getByRole("heading", { name: "Documentos sintéticos" })).toBeVisible();
    await expect(page.getByText("Documentos disponíveis")).toBeVisible();
    await expect(page.getByText("total informado pelo servidor: 3")).toBeVisible();
    await expect(page.getByText("Período retornado pelo servidor: 2026-08-01 até 2026-09-01 · fronteira [from,to)")).toBeVisible();
    await expect(page.getByLabel("Resultados dos documentos").getByRole("button", { name: "Baixar XML" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Baixar PDF" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Regenerar PDF" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  });
}

test("mantém o cursor opaco, os filtros e o teclado na próxima página", async ({ page }) => {
  await page.goto("/browser-tests/documents.html?role=visualizador");
  const next = page.getByRole("button", { name: "Próxima página" });
  await next.focus();
  await expect(next).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("cursor-preserved")).toHaveText("A próxima página mantém os filtros ativos.");
  await expect(page.getByText("Cursor opaco devolvido pelo servidor preservado.")).toBeVisible();
  await expect(page.getByText("opaque.synthetic.cursor")).toHaveCount(0);
});

test("preserva o fluxo seguro para sessão anônima ou expirada", async ({ page }) => {
  for (const session of ["anonymous", "expired"]) {
    await page.goto(`/browser-tests/documents.html?session=${session}`);
    await expect(page.getByRole("alert")).toHaveText("Acesse sua conta.");
    await expect(page.getByText("Resultados dos documentos")).toHaveCount(0);
  }
});
