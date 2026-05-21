import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { afterEach, describe, expect, it } from "vitest";
import { publishForgeOutput } from "./publish.js";

const dirs: string[] = [];

async function tempDir(): Promise<string> {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "forge-publish-"));
  dirs.push(d);
  return d;
}

afterEach(async () => {
  await Promise.all(dirs.splice(0).map((d) => fs.rm(d, { recursive: true, force: true })));
});

describe("publishForgeOutput", () => {
  it("initializes git and commits forged output", async () => {
    const outputDir = await tempDir();
    await fs.writeFile(
      path.join(outputDir, "forge.manifest.json"),
      JSON.stringify({
        projectName: "demo-app",
        recipeId: "minimal",
        recipeVersion: "1.0.0",
      }) + "\n"
    );
    await fs.writeFile(path.join(outputDir, "README.md"), "# demo\n");

    const result = await publishForgeOutput({
      outputDir,
      branch: "forge/demo-app",
      draft: true,
    });

    expect(result.committed).toBe(true);
    expect(result.branch).toBe("forge/demo-app");
    const log = execFileSync("git", ["log", "-1", "--oneline"], {
      cwd: outputDir,
      encoding: "utf8",
    });
    expect(log).toContain("forge:");
  });
});
