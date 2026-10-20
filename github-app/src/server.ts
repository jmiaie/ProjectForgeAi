import http, { type IncomingMessage, type ServerResponse } from "node:http";
import type { AppConfig } from "./config.js";
import { routeEvent, type ForgeJob } from "./router.js";
import { verifySignature } from "./signature.js";

export interface Enqueuer {
  enqueue(job: ForgeJob): void;
}

class BodyTooLargeError extends Error {}

function readBody(req: IncomingMessage, limit: number): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > limit) {
        reject(new BodyTooLargeError());
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function send(res: ServerResponse, status: number, body: Record<string, unknown>): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

/**
 * Build the request handler. Order matters: the signature is checked on the
 * raw bytes before the body is parsed or routed, so an unsigned or forged
 * request never reaches JSON.parse or the queue.
 */
export function createWebhookHandler(config: AppConfig, queue: Enqueuer) {
  return async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const url = (req.url ?? "").split("?")[0];
    if (url !== config.webhookPath) {
      send(res, 404, { error: "not found" });
      return;
    }
    if (req.method !== "POST") {
      res.setHeader("allow", "POST");
      send(res, 405, { error: "method not allowed" });
      return;
    }

    let raw: Buffer;
    try {
      raw = await readBody(req, config.maxBodyBytes);
    } catch (err) {
      if (err instanceof BodyTooLargeError) {
        send(res, 413, { error: "payload too large" });
      } else {
        send(res, 400, { error: "could not read body" });
      }
      return;
    }

    if (!verifySignature(config.webhookSecret, raw, req.headers["x-hub-signature-256"])) {
      send(res, 401, { error: "invalid or missing X-Hub-Signature-256" });
      return;
    }

    let payload: unknown;
    try {
      payload = JSON.parse(raw.toString("utf8"));
    } catch {
      send(res, 400, { error: "body is not JSON" });
      return;
    }

    const event = req.headers["x-github-event"];
    const deliveryHeader = req.headers["x-github-delivery"];
    const deliveryId = typeof deliveryHeader === "string" ? deliveryHeader : "unknown";
    if (event === "ping") {
      send(res, 200, { ok: true, pong: true });
      return;
    }

    const decision = routeEvent(
      typeof event === "string" ? event : undefined,
      deliveryId,
      payload,
      config.triggerLabel
    );
    if (decision.action === "enqueue") {
      queue.enqueue(decision.job);
      send(res, 202, { queued: true, delivery: deliveryId });
    } else {
      send(res, 200, { queued: false, reason: decision.reason });
    }
  };
}

export function createServer(config: AppConfig, queue: Enqueuer): http.Server {
  const handler = createWebhookHandler(config, queue);
  return http.createServer((req, res) => {
    handler(req, res).catch((err: unknown) => {
      console.error("webhook handler error:", err);
      if (!res.headersSent) send(res, 500, { error: "internal error" });
    });
  });
}
