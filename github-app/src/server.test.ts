import type { AddressInfo } from "node:net";
import type http from "node:http";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { AppConfig } from "./config.js";
import type { ForgeJob } from "./router.js";
import { createServer } from "./server.js";
import { signPayload } from "./signature.js";

const config: AppConfig = {
  webhookSecret: "server-test-secret",
  triggerLabel: "forge",
  port: 0,
  webhookPath: "/webhook",
  forgeCliPath: "/unused",
  maxBodyBytes: 4096,
};

const LABELED = JSON.stringify({
  action: "labeled",
  label: { name: "forge" },
  issue: { number: 5, body: "spec" },
  repository: { full_name: "octo/repo" },
});

let server: http.Server;
let base: string;
let jobs: ForgeJob[];

beforeEach(async () => {
  jobs = [];
  server = createServer(config, { enqueue: (job) => jobs.push(job) });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

afterEach(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

function post(body: string, headers: Record<string, string> = {}, path = "/webhook") {
  return fetch(`${base}${path}`, {
    method: "POST",
    body,
    headers: { "content-type": "application/json", ...headers },
  });
}

function signed(body: string, event = "issues"): Record<string, string> {
  return {
    "x-hub-signature-256": signPayload(config.webhookSecret, body),
    "x-github-event": event,
    "x-github-delivery": "delivery-1",
  };
}

describe("webhook server", () => {
  it("rejects an unsigned request with 401 and enqueues nothing", async () => {
    const res = await post(LABELED, { "x-github-event": "issues" });
    expect(res.status).toBe(401);
    expect(jobs).toHaveLength(0);
  });

  it("rejects a wrongly signed request with 401", async () => {
    const res = await post(LABELED, {
      ...signed(LABELED),
      "x-hub-signature-256": signPayload("wrong-secret", LABELED),
    });
    expect(res.status).toBe(401);
    expect(jobs).toHaveLength(0);
  });

  it("rejects a body changed after signing", async () => {
    const res = await post(LABELED.replace("octo/repo", "evil/repo"), signed(LABELED));
    expect(res.status).toBe(401);
    expect(jobs).toHaveLength(0);
  });

  it("checks the signature before parsing JSON", async () => {
    const res = await post("not json", { "x-github-event": "issues" });
    expect(res.status).toBe(401);
  });

  it("enqueues a signed issues.labeled delivery and returns 202", async () => {
    const res = await post(LABELED, signed(LABELED));
    expect(res.status).toBe(202);
    expect(jobs).toEqual([
      expect.objectContaining({ deliveryId: "delivery-1", repository: "octo/repo", issueNumber: 5 }),
    ]);
  });

  it("acknowledges but ignores other signed events", async () => {
    const body = JSON.stringify({ action: "opened" });
    const res = await post(body, signed(body, "pull_request"));
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ queued: false });
    expect(jobs).toHaveLength(0);
  });

  it("answers GitHub's ping", async () => {
    const body = JSON.stringify({ zen: "hi" });
    const res = await post(body, signed(body, "ping"));
    expect(res.status).toBe(200);
  });

  it("returns 400 for a signed non-JSON body", async () => {
    const res = await post("nope", signed("nope"));
    expect(res.status).toBe(400);
  });

  it("returns 413 for a body over the limit", async () => {
    const big = "x".repeat(config.maxBodyBytes + 1);
    const res = await post(big, signed(big)).catch(() => null);
    // The server may close the socket after replying; either way nothing is queued.
    if (res) expect(res.status).toBe(413);
    expect(jobs).toHaveLength(0);
  });

  it("only serves POST on the webhook path", async () => {
    expect((await fetch(`${base}/webhook`)).status).toBe(405);
    expect((await post(LABELED, signed(LABELED), "/other")).status).toBe(404);
  });
});
