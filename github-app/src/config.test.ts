import { describe, expect, it } from "vitest";
import { loadConfig } from "./config.js";

describe("loadConfig", () => {
  it("refuses to start without a webhook secret", () => {
    expect(() => loadConfig({})).toThrow(/GITHUB_WEBHOOK_SECRET/);
  });

  it("defaults the trigger label to forge and lets env override it", () => {
    expect(loadConfig({ GITHUB_WEBHOOK_SECRET: "s" }).triggerLabel).toBe("forge");
    expect(
      loadConfig({ GITHUB_WEBHOOK_SECRET: "s", FORGE_TRIGGER_LABEL: "spec-ready" }).triggerLabel
    ).toBe("spec-ready");
  });

  it("points at the repo's built Forge CLI by default", () => {
    expect(loadConfig({ GITHUB_WEBHOOK_SECRET: "s" }).forgeCliPath).toMatch(/dist[\\/]cli\.js$/);
  });
});
