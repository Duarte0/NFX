import { expect, test, type Page } from "@playwright/test";

const roles = ["administrador", "operador", "visualizador"] as const;
const protectedFeatureRoutes = [
  { path: (role: string) => `/browser-tests/dashboard.html?role=${role}`, heading: "Dashboard sintético" },
  { path: (role: string) => `/browser-tests/documents.html?role=${role}`, heading: "Documentos sintéticos" },
  { path: (role: string) => `/browser-tests/companies.html?role=${role}`, heading: "Empresas, certificados e coletas sintéticas" },
  { path: (role: string) => `/browser-tests/exports.html?role=${role}`, heading: "Exportações sintéticas" },
] as const;

const negativeFeatureRoutes = [
  (session: string) => `/browser-tests/documents.html?session=${session}`,
  (session: string) => `/browser-tests/companies.html?session=${session}`,
  (session: string) => `/browser-tests/exports.html?session=${session}`,
] as const;

async function assertRenderedSemantics(page: Page, requireMainHeading = true) {
  const result = await page.evaluate((needsHeading) => {
    const failures: string[] = [];
    const main = document.querySelector("main");
    if (!main) failures.push("document must expose one main landmark");
    if (document.querySelectorAll("main").length !== 1) failures.push("document must expose exactly one main landmark");
    if (needsHeading && !main?.querySelector("h1")) failures.push("main must expose an h1");

    for (const section of document.querySelectorAll("section[aria-labelledby]")) {
      const ids = section.getAttribute("aria-labelledby")?.split(/\s+/).filter(Boolean) ?? [];
      if (!ids.length || ids.some((id) => !document.getElementById(id))) {
        failures.push(`section has an unresolved accessible name: ${section.id || "anonymous"}`);
      }
    }

    for (const label of document.querySelectorAll("label")) {
      const target = label.htmlFor ? document.getElementById(label.htmlFor) : null;
      if (!target) failures.push(`label has no associated control: ${label.textContent?.trim() || "unnamed"}`);
    }

    for (const control of document.querySelectorAll("input, select, textarea")) {
      const id = control.getAttribute("id");
      if (!id || !Array.from(document.querySelectorAll("label")).some((label) => label.htmlFor === id)) {
        failures.push(`form control has no label: ${id || control.tagName}`);
      }
      const describedBy = control.getAttribute("aria-describedby")?.split(/\s+/).filter(Boolean) ?? [];
      if (describedBy.some((id) => !document.getElementById(id))) failures.push(`control has unresolved description: ${id}`);
    }

    for (const action of document.querySelectorAll("button, a")) {
      const name = [action.getAttribute("aria-label"), action.getAttribute("title"), action.textContent]
        .filter(Boolean).join(" ").trim();
      if (!name) failures.push(`${action.tagName.toLowerCase()} has no accessible name`);
    }

    for (const liveRegion of document.querySelectorAll('[role="alert"], [role="status"]')) {
      if (!liveRegion.textContent?.trim()) failures.push(`${liveRegion.getAttribute("role")} has no message`);
    }

    for (const dialog of document.querySelectorAll('[role="dialog"]')) {
      const labelIds = dialog.getAttribute("aria-labelledby")?.split(/\s+/).filter(Boolean) ?? [];
      if (!dialog.getAttribute("aria-label") && (!labelIds.length || labelIds.some((id) => !document.getElementById(id)))) {
        failures.push("dialog has no accessible name");
      }
      if (dialog.getAttribute("aria-modal") !== "true") failures.push("critical dialog must be modal");
    }

    return failures;
  }, requireMainHeading);
  expect(result).toEqual([]);
}

async function assertResponsiveContainment(page: Page) {
  const result = await page.evaluate(() => {
    const visible = (element: Element) => {
      const style = getComputedStyle(element);
      return style.display !== "none" && style.visibility !== "hidden";
    };
    const clipped: string[] = [];
    for (const element of document.querySelectorAll("h1, h2, h3, button, a, input, select, textarea")) {
      if (!visible(element) || element.closest(".ui-table-wrap")) continue;
      const box = element.getBoundingClientRect();
      if (box.width <= 0 || box.left < -1 || box.right > window.innerWidth + 1) {
        clipped.push(element.textContent?.trim() || element.getAttribute("aria-label") || element.tagName);
      }
    }

    const tables = Array.from(document.querySelectorAll<HTMLElement>(".ui-table-wrap")).map((wrapper) => ({
      overflowX: getComputedStyle(wrapper).overflowX,
      hasCaption: Boolean(wrapper.querySelector("table > caption")),
      hasHeaders: wrapper.querySelectorAll("thead th").length > 0,
      withinViewport: wrapper.getBoundingClientRect().left >= -1 && wrapper.getBoundingClientRect().right <= window.innerWidth + 1,
    }));
    return {
      pageOverflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
      clipped,
      tables,
    };
  });
  expect(result.pageOverflow).toBeLessThanOrEqual(1);
  expect(result.clipped).toEqual([]);
  for (const table of result.tables) {
    expect(["auto", "scroll"]).toContain(table.overflowX);
    expect(table.hasCaption).toBe(true);
    expect(table.hasHeaders).toBe(true);
    expect(table.withinViewport).toBe(true);
  }
}

test("keeps each delivered feature semantically named and horizontally contained", async ({ page }) => {
  for (const role of roles) {
    for (const route of protectedFeatureRoutes) {
      await page.goto(route.path(role));
      await expect(page.getByRole("heading", { name: route.heading })).toBeVisible();
      await assertRenderedSemantics(page);
      await assertResponsiveContainment(page);
      await expect(page.locator("body")).not.toContainText(/opaque\.|temporary_failure|permanent_failure|policy_block|partial_result|source_missing|all_items_failed|password_hash|operation_id|archive_path|scope_hash/);
    }
  }
});

test("preserves role boundaries and safe anonymous or expired-session surfaces", async ({ page }) => {
  for (const role of roles) {
    await page.goto(`/browser-tests/admin.html?role=${role}#usuarios`);
    await assertRenderedSemantics(page);
    if (role === "administrador") {
      await expect(page.getByRole("heading", { name: "Usuários", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Auditoria", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Retenção e exclusão controlada", exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole("alert")).toHaveText("Área administrativa indisponível para esta sessão.");
      await expect(page.getByText("admin@example.test")).toHaveCount(0);
    }
  }

  for (const route of negativeFeatureRoutes) {
    for (const session of ["anonymous", "expired"] as const) {
      await page.goto(route(session));
      await assertRenderedSemantics(page);
      await expect(page.getByRole("alert")).toHaveText("Acesse sua conta.");
      await expect(page.getByText(/admin@example\.test|opaque\.|password_hash|operation_id/)).toHaveCount(0);
    }
  }
});

test("keeps the composed shell keyboard-entry path and named landmarks intact", async ({ page }) => {
  for (const role of roles) {
    await page.goto(`/browser-tests/shell.html?role=${role}`);
    await expect(page.locator("#main-content")).toBeVisible();
    await assertRenderedSemantics(page, false);
    await assertResponsiveContainment(page);
    const skip = page.getByRole("link", { name: "Pular para o conteúdo principal" });
    await page.keyboard.press("Tab");
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
  }
});
