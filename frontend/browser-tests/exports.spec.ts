import { expect, test } from "@playwright/test";

for (const role of ["administrador", "operador", "visualizador"] as const) {
  test(`apresenta estados duráveis e ações seguras para ${role}`, async ({ page }) => {
    await page.goto(`/browser-tests/exports.html?role=${role}`);
    await expect(page.getByRole("heading", { name: "Exportações sintéticas" })).toBeVisible();
    for (const label of ["Pendente", "Processando", "Concluída", "Disponível para download", "Parcial", "Falhou", "Expirada", "Excluída"]) {
      await expect(page.getByText(label, { exact: true })).toBeVisible();
    }
    await expect(page.getByText("O servidor produziu apenas parte do escopo autorizado.")).toBeVisible();
    await expect(page.getByText("A exportação expirou; os documentos de origem permanecem no acervo.")).toBeVisible();
    await expect(page.getByText("partial_result")).toHaveCount(0);
    await expect(page.getByText("source_missing")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Baixar ZIP" })).toHaveCount(1);
    await expect(page.getByText("Download não autorizado pelo servidor para este estado.")).toHaveCount(7);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  });
}

test("guarda ações repetidas, retém leitura stale e conserva foco de teclado", async ({ page }) => {
  await page.goto("/browser-tests/exports.html?role=visualizador");
  const request = page.getByRole("button", { name: "Solicitar exportação" });
  await request.focus();
  await expect(request).toBeFocused();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Solicitação enviada uma vez; o estado será confirmado pelo servidor.")).toBeVisible();
  await expect(page.getByTestId("request-count")).toHaveText("Solicitações sintéticas: 1");

  await page.getByRole("button", { name: "Atualizar exportações" }).click();
  await expect(page.getByText("Leitura desatualizada")).toBeVisible();
  await expect(page.getByText("A última leitura segura permanece visível enquanto a atualização é revalidada.")).toBeVisible();
  await expect(page.getByText("A atualização das exportações está indisponível.")).toBeVisible();
  await page.getByRole("button", { name: "Tentar novamente" }).click();
  await expect(page.getByText("A atualização das exportações está indisponível.")).toHaveCount(0);
});

test("preserva seleção mais nova e não habilita download parcial", async ({ page }) => {
  await page.goto("/browser-tests/exports.html?role=visualizador");
  const pending = page.getByRole("row").filter({ hasText: "Pendente" }).getByRole("button", { name: "Detalhes" });
  const failed = page.getByRole("row").filter({ hasText: "Falhou" }).getByRole("button", { name: "Detalhes" });
  await pending.click();
  await failed.click();
  await expect(page.getByRole("heading", { name: "Detalhe da exportação" })).toBeVisible();
  await expect(page.getByText("Falhou", { exact: true }).last()).toBeVisible();
  await expect(page.getByRole("row").filter({ hasText: "Parcial" }).getByRole("button", { name: "Baixar ZIP" })).toHaveCount(0);
});

test("mantém o fluxo seguro para sessão anônima ou expirada", async ({ page }) => {
  for (const session of ["anonymous", "expired"]) {
    await page.goto(`/browser-tests/exports.html?session=${session}`);
    await expect(page.getByRole("alert")).toHaveText("Acesse sua conta.");
    await expect(page.getByText("Exportações solicitadas")).toHaveCount(0);
  }
});
