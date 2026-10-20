import { execFileSync, type ExecFileSyncOptions } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { NotImplementedError } from "./errors.js";
import type { ForgeJob } from "./router.js";

const MAX_SPEC_CHARS = 10_000;
const SPEC_BLOCK = /```json[ \t]*\r?\n([\s\S]*?)\r?\n```/;

export type ExecFile = (
  file: string,
  args: readonly string[],
  options: ExecFileSyncOptions
) => string | Buffer;

export interface DraftPullRequest {
  job: ForgeJob;
  outputDir: string;
  branch: string;
}

export interface RunnerOptions {
  forgeCliPath: string;
  /** Injected for tests; defaults to `child_process.execFileSync`. */
  execFile?: ExecFile;
  /** Parent directory for per-job temp dirs. */
  workRoot?: string;
  /** Injected for tests; defaults to the not-yet-built GitHub PR step. */
  openPullRequest?: (pr: DraftPullRequest) => Promise<string>;
  timeoutMs?: number;
}

export interface RunnerResult {
  branch: string;
  prUrl: string;
}

/**
 * Pull the Forge spec out of an issue body: the first fenced ```json block.
 * Schema validation is left to the Forge CLI (`forge run --spec` validates
 * against schemas/forge-spec.schema.json before writing anything).
 */
export function extractSpec(issueBody: string): Record<string, unknown> {
  const match = SPEC_BLOCK.exec(issueBody);
  if (!match) {
    throw new Error("Issue body has no ```json spec block");
  }
  const text = match[1];
  if (text.length > MAX_SPEC_CHARS) {
    throw new Error(`Spec block is longer than ${MAX_SPEC_CHARS} characters`);
  }
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch (err) {
    throw new Error(`Spec block is not valid JSON: ${(err as Error).message}`);
  }
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Spec must be a JSON object");
  }
  return data as Record<string, unknown>;
}

/**
 * Open a draft PR on GitHub with the forged output.
 *
 * Not built yet: it needs an installation access token (App JWT -> token
 * exchange), a decision on where generated files land in the target repo,
 * and the review step from ADR-001. Tracked in docs/ROADMAP.md, "Next:
 * GitHub App draft PR (N2)".
 */
export async function openDraftPullRequest(pr: DraftPullRequest): Promise<string> {
  throw new NotImplementedError(
    `Opening a draft PR for ${pr.job.repository}#${pr.job.issueNumber} on branch ` +
      `${pr.branch} is not implemented. See docs/ROADMAP.md, Next N2 (GitHub App draft PR).`
  );
}

/** Environment for the CLI child: the webhook secret is never passed down. */
function childEnv(): NodeJS.ProcessEnv {
  const env = { ...process.env };
  delete env.GITHUB_WEBHOOK_SECRET;
  delete env.GITHUB_APP_PRIVATE_KEY;
  return env;
}

/**
 * Run one Forge job: spec -> `forge run` -> `forge publish` (local commit, no
 * push) -> draft PR.
 *
 * The CLI is invoked exactly as src/publish.ts invokes git: `execFileSync`
 * with an argument array and no shell, so nothing from the issue is ever
 * interpreted by a shell. Every path is built under a fresh `mkdtemp`
 * directory; nothing from the issue is used to build a path.
 */
export async function runForgeJob(
  job: ForgeJob,
  options: RunnerOptions
): Promise<RunnerResult> {
  const execFile = options.execFile ?? execFileSync;
  const openPullRequest = options.openPullRequest ?? openDraftPullRequest;
  const spec = extractSpec(job.issueBody);

  const workDir = await fs.mkdtemp(path.join(options.workRoot ?? os.tmpdir(), "forge-app-"));
  try {
    const specPath = path.join(workDir, "spec.json");
    const outputDir = path.join(workDir, "out");
    // issueNumber is a number from the payload, so the branch name is safe.
    const branch = `forge/issue-${job.issueNumber}`;
    await fs.writeFile(specPath, JSON.stringify(spec, null, 2) + "\n", "utf8");

    const execOptions: ExecFileSyncOptions = {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
      timeout: options.timeoutMs ?? 120_000,
      env: childEnv(),
    };
    execFile(
      process.execPath,
      [options.forgeCliPath, "run", "--spec", specPath, "--output", outputDir],
      execOptions
    );
    execFile(
      process.execPath,
      [options.forgeCliPath, "publish", "--output", outputDir, "--branch", branch],
      execOptions
    );

    const prUrl = await openPullRequest({ job, outputDir, branch });
    return { branch, prUrl };
  } finally {
    await fs.rm(workDir, { recursive: true, force: true });
  }
}
