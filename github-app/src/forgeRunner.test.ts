import { existsSync } from "node:fs";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";
import { NotImplementedError } from "./errors.js";
import { extractSpec, runForgeJob, type ExecFile } from "./forgeRunner.js";
import type { ForgeJob } from "./router.js";

const SPEC_BODY = [
  "Please forge this:",
  "",
  "```json",
  '{ "projectName": "issue-app", "recipe": "minimal" }',
  "```",
].join("\n");

const job = (body = SPEC_BODY): ForgeJob => ({
  deliveryId: "d-1",
  repository: "octo/repo",
  issueNumber: 12,
  issueBody: body,
});

const roots: string[] = [];
async function workRoot(): Promise<string> {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "forge-app-test-"));
  roots.push(d);
  return d;
}
afterEach(async () => {
  await Promise.all(roots.splice(0).map((d) => fs.rm(d, { recursive: true, force: true })));
});

describe("extractSpec", () => {
  it("reads the first fenced json block", () => {
    expect(extractSpec(SPEC_BODY)).toEqual({ projectName: "issue-app", recipe: "minimal" });
  });

  it("rejects bodies without a block, bad JSON, and non-objects", () => {
    expect(() => extractSpec("no spec here")).toThrow(/no ```json/);
    expect(() => extractSpec("```json\n{nope}\n```")).toThrow(/not valid JSON/);
    expect(() => extractSpec("```json\n[1]\n```")).toThrow(/JSON object/);
    expect(() => extractSpec(`\`\`\`json\n"${"a".repeat(10_001)}"\n\`\`\``)).toThrow(/longer/);
  });
});

describe("runForgeJob", () => {
  it("invokes the CLI with execFile argument arrays and no shell", async () => {
    const calls: { file: string; args: readonly string[]; shell: unknown }[] = [];
    const fakeExec: ExecFile = (file, args, options) => {
      calls.push({ file, args, shell: options.shell });
      return "";
    };
    const root = await workRoot();
    const result = await runForgeJob(job(), {
      forgeCliPath: "/repo/dist/cli.js",
      execFile: fakeExec,
      workRoot: root,
      openPullRequest: async () => "https://example.invalid/pr/1",
    });

    expect(result).toEqual({ branch: "forge/issue-12", prUrl: "https://example.invalid/pr/1" });
    expect(calls).toHaveLength(2);
    expect(calls.every((c) => c.file === process.execPath && c.shell === false)).toBe(true);
    const [run, publish] = calls.map((c) => c.args);
    expect(run.slice(0, 3)).toEqual(["/repo/dist/cli.js", "run", "--spec"]);
    expect(run[4]).toBe("--output");
    expect(publish).toEqual(["/repo/dist/cli.js", "publish", "--output", run[5], "--branch", "forge/issue-12"]);
    // Every path the CLI sees lives under the per-job temp dir.
    for (const p of [run[3], run[5]]) {
      expect(path.resolve(p).startsWith(path.resolve(root) + path.sep)).toBe(true);
    }
    // Temp dir is cleaned up.
    expect(await fs.readdir(root)).toEqual([]);
  });

  it("does not run the CLI when the issue has no spec", async () => {
    let called = false;
    await expect(
      runForgeJob(job("no spec"), {
        forgeCliPath: "/x",
        execFile: () => {
          called = true;
          return "";
        },
        workRoot: await workRoot(),
      })
    ).rejects.toThrow(/no ```json/);
    expect(called).toBe(false);
  });

  const cli = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "..",
    "dist",
    "cli.js"
  );

  it.skipIf(!existsSync(cli))(
    "runs the real built CLI, then stops at the not-yet-built PR step",
    async () => {
      let forgedManifest: unknown;
      await expect(
        runForgeJob(job(), {
          forgeCliPath: cli,
          workRoot: await workRoot(),
          openPullRequest: async (pr) => {
            forgedManifest = JSON.parse(
              await fs.readFile(path.join(pr.outputDir, "forge.manifest.json"), "utf8")
            );
            const { openDraftPullRequest } = await import("./forgeRunner.js");
            return openDraftPullRequest(pr);
          },
        })
      ).rejects.toBeInstanceOf(NotImplementedError);
      expect(forgedManifest).toMatchObject({ projectName: "issue-app", recipeId: "minimal" });
    },
    60_000
  );

  it("rejects specs the CLI's schema rejects", async () => {
    if (!existsSync(cli)) return;
    await expect(
      runForgeJob(job('```json\n{ "projectName": "../../etc", "recipe": "minimal" }\n```'), {
        forgeCliPath: cli,
        workRoot: await workRoot(),
      })
    ).rejects.toThrow();
  });
});
