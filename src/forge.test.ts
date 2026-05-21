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
    expect(manifest.files).toContain("package.json");

    const readme = await fs.readFile(
      path.join(outputDir, "README.md"),
      "utf8"
    );
    expect(readme).toContain("demo-app");

    const pkg = JSON.parse(
      await fs.readFile(path.join(outputDir, "package.json"), "utf8")
    );
    expect(pkg.name).toBe("demo-app");

    const manifestOnDisk = JSON.parse(
      await fs.readFile(path.join(outputDir, "forge.manifest.json"), "utf8")
    );
    expect(manifestOnDisk.recipeId).toBe("minimal");
  });

  it("refuses non-empty output without force", async () => {
    const recipe = getRecipe("minimal")!;
    const outputDir = await makeTempDir();
    await fs.writeFile(path.join(outputDir, "existing.txt"), "x");

    await expect(
      runForge({ recipe, outputDir, projectName: "x" })
    ).rejects.toThrow(/not empty/);
  });

  it("allows non-empty output with force", async () => {
    const recipe = getRecipe("minimal")!;
    const outputDir = await makeTempDir();
    await fs.writeFile(path.join(outputDir, "existing.txt"), "x");

    await runForge({ recipe, outputDir, force: true, projectName: "forced" });
    const readme = await fs.readFile(
      path.join(outputDir, "README.md"),
      "utf8"
    );
    expect(readme).toContain("forced");
  });
});
