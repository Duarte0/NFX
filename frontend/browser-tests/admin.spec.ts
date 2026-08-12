import { expect, test } from "@playwright/test";

for (const role of ["administrador", "operador", "visualizador"] as const) {
  test(`aplica o limite administrativo para ${role}`, async ({ page }) => {
    await page.goto(`/browser-tests/admin.html?role=${role}#usuarios`);
    if (role === "administrador") {
      await expect(page.getByRole("heading", { name: "Administração sintética", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Usuários", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Auditoria", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Retenção e exclusão controlada", exact: true })).toBeVisible();
      await expect(page.getByText("Falha de integridade")).toBeVisible();
      await expect(page.getByText("Recuperação necessária")).toBeVisible();
      await expect(page.getByText("opaque.browser.retention.cursor")).toHaveCount(0);
    } else {
      await expect(page.getByRole("alert")).toHaveText("Área administrativa indisponível para esta sessão.");
      await expect(page.getByRole("heading", { name: "Usuários", exact: true })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Auditoria", exact: true })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Retenção e exclusão controlada", exact: true })).toHaveCount(0);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  });
}

for (const session of ["anonymous", "expired"] as const) {
  test(`recusa sessão ${session} sem dados administrativos`, async ({ page }) => {
    await page.goto(`/browser-tests/admin.html?role=administrador&session=${session}#auditoria`);
    await expect(page.getByRole("alert")).toHaveText("Área administrativa indisponível para esta sessão.");
    await expect(page.getByText("admin@example.test")).toHaveCount(0);
  });
}

test("exige confirmação cancelável e preserva foco no diálogo de usuário", async ({ page }) => {
  await page.goto("/browser-tests/admin.html?role=administrador&state=confirm#usuarios");
  const confirm = page.getByRole("button", { name: "Confirmar ação" });
  await expect(confirm).toBeDisabled();
  const reason = page.getByLabel("Motivo");
  await reason.fill("Motivo sintético");
  await expect(confirm).toBeEnabled();
  await page.getByRole("button", { name: "Cancelar" }).click();
  await expect(page.getByRole("button", { name: "Confirmar ação" })).toHaveCount(0);
});

test("blocks stale retention preview and exposes recovery action", async ({ page }) => {
  await page.goto("/browser-tests/admin.html?role=administrador&state=preview-stale#retencao");
  await expect(page.getByText("Esta prévia ficou desatualizada")).toBeVisible();
  await expect(page.getByRole("button", { name: "Preparar solicitação de exclusão" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Solicitar recuperação" })).toBeVisible();
});

test("opens explicit retention confirmation and supports keyboard focus", async ({ page }) => {
  await page.goto("/browser-tests/admin.html?role=administrador&state=delete-confirm#retencao");
  const confirm = page.getByRole("button", { name: "Confirmar solicitação" });
  await expect(confirm).toBeEnabled();
  await page.getByLabel("Motivo bounded").focus();
  await expect(page.getByLabel("Motivo bounded")).toBeFocused();
  await page.getByRole("button", { name: "Cancelar" }).last().click();
  await expect(page.getByRole("button", { name: "Confirmar solicitação" })).toHaveCount(0);
});

test("names critical dialogs, focuses them, and returns focus after Escape", async ({ page }) => {
  await page.goto("/browser-tests/admin.html?role=administrador#usuarios");
  const deactivate = page.getByRole("button", { name: "Desativar" });
  await deactivate.focus();
  await deactivate.click();
  const userDialog = page.getByRole("dialog", { name: "Desativar usuário" });
  await expect(userDialog).toBeVisible();
  await expect(userDialog).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(userDialog).toHaveCount(0);
  await expect(deactivate).toBeFocused();

  await page.goto("/browser-tests/admin.html?role=administrador#retencao");
  const prepareDeletion = page.getByRole("button", { name: "Preparar solicitação de exclusão" });
  await prepareDeletion.focus();
  await prepareDeletion.click();
  const deletionDialog = page.getByRole("dialog", { name: "Confirmar exclusão controlada" });
  await expect(deletionDialog).toBeVisible();
  await expect(deletionDialog).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(deletionDialog).toHaveCount(0);
  await expect(prepareDeletion).toBeFocused();
});
