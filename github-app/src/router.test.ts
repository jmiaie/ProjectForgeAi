import { describe, expect, it } from "vitest";
import { routeEvent } from "./router.js";

function labeled(label: string, extra: Record<string, unknown> = {}) {
  return {
    action: "labeled",
    label: { name: label },
    issue: { number: 42, body: "```json\n{}\n```" },
    repository: { full_name: "octo/repo" },
    installation: { id: 7 },
    sender: { login: "maintainer" },
    ...extra,
  };
}

describe("routeEvent", () => {
  it("enqueues issues.labeled with the trigger label", () => {
    const d = routeEvent("issues", "d-1", labeled("forge"), "forge");
    expect(d).toEqual({
      action: "enqueue",
      job: {
        deliveryId: "d-1",
        repository: "octo/repo",
        issueNumber: 42,
        issueBody: "```json\n{}\n```",
        installationId: 7,
        requestedBy: "maintainer",
      },
    });
  });

  it("uses the configured label, not a hard-coded one", () => {
    expect(routeEvent("issues", "d", labeled("forge"), "build-me").action).toBe("ignore");
    expect(routeEvent("issues", "d", labeled("build-me"), "build-me").action).toBe("enqueue");
  });

  it("ignores other labels", () => {
    const d = routeEvent("issues", "d", labeled("bug"), "forge");
    expect(d).toMatchObject({ action: "ignore", reason: expect.stringContaining("bug") });
  });

  it("ignores other issue actions, including unlabeled", () => {
    for (const action of ["opened", "edited", "unlabeled"]) {
      const d = routeEvent("issues", "d", labeled("forge", { action }), "forge");
      expect(d.action).toBe("ignore");
    }
  });

  it("ignores other events", () => {
    for (const event of ["pull_request", "issue_comment", "push", undefined]) {
      expect(routeEvent(event, "d", labeled("forge"), "forge").action).toBe("ignore");
    }
  });

  it("ignores payloads without a repository or issue number", () => {
    expect(
      routeEvent("issues", "d", labeled("forge", { repository: {} }), "forge").action
    ).toBe("ignore");
    expect(routeEvent("issues", "d", labeled("forge", { issue: {} }), "forge").action).toBe(
      "ignore"
    );
    expect(routeEvent("issues", "d", null, "forge").action).toBe("ignore");
  });

  it("treats a null issue body as empty", () => {
    const d = routeEvent("issues", "d", labeled("forge", { issue: { number: 1, body: null } }), "forge");
    expect(d.action === "enqueue" && d.job.issueBody).toBe("");
  });
});
