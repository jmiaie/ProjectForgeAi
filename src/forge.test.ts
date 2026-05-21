import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { runForge } from "./forge.js";
import { getRecipe } from "./recipes/index.js";

const tempDirs: string[] = [];

async function makeTempDir(): Promise<string> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "forge-test-"));
  tempDirs.push(dir);
  return dir;
}

afterEach(async () => {
  await Promise.all(
    tempDirs.splice(0).map((d) => fs.rm(d, { recursive: true, force: true }))
  );
});

describe("runForge", () => {
  it("materializes minimal recipe with manifest", async () => {
    const recipe = getRecipe("minimal");
    expect(recipe).toBeDefined();

    const outputDir = await makeTempDir();
    const manifest = await runForge({
      recipe: recipe!,
      outputDir,
      projectName: "demo-app",
    });

    expect(manifest.recipeId).toBe("minimal");
    expect(manifest.projectName).toBe("demo-app");
    expect(manifest.files).toContain("README.md");

    const readme = await fs.readFile(
      path.join(outputDir, "README.md"),
      "utf8"
    );
    expect(readme).toContain("demo-app");
  });

  it("materializes express-api with spec vars", async () => {
    const recipe = getRecipe("express-api")!;
    const outputDir = await makeTempDir();
    await runForge({
      recipe,
      outputDir,
      projectName: "orders-api",
      vars: {
        projectName: "orders-api",
        description: "Orders service",
        port: "4000",
        year: "2026",
      },
    });

    const server = await fs.readFile(
      path.join(outputDir, "src/server.js"),
      "utf8"
    );
    expect(server).toContain("4000");
    expect(server).toContain("orders-api");
  });

  it("refuses non-empty output without force", async () => {
    const recipe = getRecipe("minimal")!;
    const outputDir = await makeTempDir();
    await fs.writeFile(path.join(outputDir, "existing.txt"), "x");

    await expect(
      runForge({ recipe, outputDir, projectName: "x" })
    ).rejects.toThrow(/not empty/);
  });
});
