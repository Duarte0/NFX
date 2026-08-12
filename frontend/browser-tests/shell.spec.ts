import { expect, firefox, test, type Page } from "@playwright/test";

const roles = {
  administrador: ["Dashboard", "Documentos", "Exportações", "Empresas", "Certificados", "Coletas", "Usuários", "Auditoria", "Retenção"],
  operador: ["Dashboard", "Documentos", "Exportações", "Empresas", "Certificados", "Coletas"],
  visualizador: ["Dashboard", "Documentos", "Exportações", "Coletas"],
} as const;

async function openShell(page: Page, role: keyof typeof roles, hash = "#dashboard") {
  await page.goto(`/browser-tests/shell.html?role=${role}&drilldown=synthetic-only${hash}`);
  await expect(page.locator(".app-shell")).toBeVisible();
}

test("uses the browser required by its project", async ({ page, browserName }, testInfo) => {
  const userAgent = await page.evaluate(() => navigator.userAgent);
  if (testInfo.project.name.startsWith("chrome-")) {
    expect(browserName).toBe("chromium");
    expect(userAgent).toContain("Chrome/");
  } else if (testInfo.project.name.startsWith("edge-")) {
    expect(browserName).toBe("chromium");
    expect(userAgent).toContain("Edg/");
  } else {
    expect(browserName).toBe("firefox");
    expect(userAgent).toContain("Firefox/");
  }
});

for (const [role, labels] of Object.entries(roles) as Array<[keyof typeof roles, readonly string[]]>) {
  test(`keeps ${role} navigation visible, named, and inside the viewport`, async ({ page }) => {
    await openShell(page, role);
    const links = page.locator(".app-shell__nav-link");
    await expect(links).toHaveCount(labels.length);
    await expect(links).toHaveText([...labels]);

    for (const link of await links.all()) {
      await expect(link).toBeVisible();
      const box = await link.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeGreaterThan(0);
      expect(box!.height).toBeGreaterThan(0);
    }

    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  });
}

async function assertSkipLinkKeyboardFlow(page: Page) {
  // A landing page without a fragment starts sequential focus at the document.
  // Firefox begins after a fragment target, which is a different keyboard flow.
  await openShell(page, "visualizador", "");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Pular para o conteúdo principal" });
  await expect(skip).toBeFocused();
  await expect(skip).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, 0)");
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
}

test("supports keyboard skip focus and keeps its focus indicator visible", async ({ page, browserName }) => {
  if (browserName !== "firefox") {
    await assertSkipLinkKeyboardFlow(page);
    return;
  }

  // Firefox headless defaults to tabbing only through form controls. A persistent
  // profile applies this user-selected all-controls mode at browser startup.
  const context = await firefox.launchPersistentContext("", {
    firefoxUserPrefs: { "accessibility.tabfocus": 7 },
  });
  try {
    await assertSkipLinkKeyboardFlow(await context.newPage());
  } finally {
    await context.close();
  }
});

test("updates active hash navigation and preserves the synthetic deep-link query", async ({ page }) => {
  await openShell(page, "administrador", "#documentos");
  const active = page.locator('.app-shell__nav-link[aria-current="page"]');
  await expect(active).toHaveText("Documentos");
  await page.getByRole("link", { name: "Exportações" }).click();
  await expect(page).toHaveURL(/\?role=administrador&drilldown=synthetic-only#exportacoes$/);
  await expect(active).toHaveText("Exportações");
  await expect(active).toHaveAttribute("href", "#exportacoes");
});

test("publishes all anchors with one authorized certificate destination", async ({ page }) => {
  await openShell(page, "administrador");
  for (const hash of ["dashboard", "documentos", "exportacoes", "empresas", "certificados", "coletas", "usuarios", "auditoria", "retencao"]) {
    await expect(page.locator(`a[href="#${hash}"]`)).toHaveCount(1);
  }
  await expect(page.locator("#certificados")).toHaveCount(1);
});
