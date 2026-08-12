import { build } from "esbuild";
import { unlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const outputPath = join(process.cwd(), "scripts", `.nfx-ui-contract-${process.pid}.mjs`);
try {
  const result = await build({
    absWorkingDir: process.cwd(),
    entryPoints: ["scripts/ui-contract.mjs"],
    bundle: true,
    format: "esm",
    platform: "node",
    external: ["react", "react-dom/server"],
    write: false,
  });
  await writeFile(outputPath, result.outputFiles[0].text, "utf8");
  await import(pathToFileURL(outputPath).href);
} finally {
  await unlink(outputPath).catch(() => undefined);
}
