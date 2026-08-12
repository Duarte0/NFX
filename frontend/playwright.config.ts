import { defineConfig } from "@playwright/test";

const viewports = [1024, 1280, 1440] as const;

const browsers = [
  {
    name: "chrome",
    use: {
      browserName: "chromium" as const,
      channel: "chrome",
    },
  },
  {
    name: "firefox",
    use: {
      browserName: "firefox" as const,
    },
  },
  {
    name: "edge",
    use: {
      browserName: "chromium" as const,
      channel: "msedge",
    },
  },
] as const;

export default defineConfig({
  testDir: "./browser-tests",

  // Evita múltiplos browsers pesados concorrendo e estourando a RAM.
  fullyParallel: false,
  workers: 1,

  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [["list"]],

  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },

  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173/browser-tests/shell.html",
    reuseExistingServer: !process.env.CI,
  },

  projects: browsers.flatMap((browser) =>
    viewports.map((width) => ({
      name: `${browser.name}-${width}`,
      use: {
        ...browser.use,
        viewport: {
          width,
          height: 900,
        },
      },
    })),
  ),
});
