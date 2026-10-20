import path from "node:path";
import { fileURLToPath } from "node:url";

export interface AppConfig {
  /** Shared secret configured on the GitHub App's webhook. Required. */
  webhookSecret: string;
  /** Label that triggers a Forge run when added to an issue. */
  triggerLabel: string;
  /** HTTP port for the webhook server. */
  port: number;
  /** URL path GitHub posts to. */
  webhookPath: string;
  /** Path to the built Forge CLI (`dist/cli.js`). */
  forgeCliPath: string;
  /** Largest request body accepted, in bytes. */
  maxBodyBytes: number;
}

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const webhookSecret = env.GITHUB_WEBHOOK_SECRET ?? "";
  if (!webhookSecret) {
    throw new Error(
      "GITHUB_WEBHOOK_SECRET is required; the server will not accept unsigned webhooks."
    );
  }
  const port = Number(env.PORT ?? "3000");
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    throw new Error(`PORT must be an integer between 0 and 65535, got ${env.PORT}`);
  }
  return {
    webhookSecret,
    triggerLabel: env.FORGE_TRIGGER_LABEL || "forge",
    port,
    webhookPath: env.WEBHOOK_PATH || "/webhook",
    forgeCliPath: env.FORGE_CLI_PATH || path.join(repoRoot, "dist", "cli.js"),
    maxBodyBytes: 1024 * 1024,
  };
}
