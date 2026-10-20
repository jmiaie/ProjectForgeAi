import { createHmac, timingSafeEqual } from "node:crypto";

/** GitHub sends `sha256=` followed by 64 lowercase hex characters. */
const SIGNATURE_PATTERN = /^sha256=([0-9a-f]{64})$/;

/**
 * Verify GitHub's `X-Hub-Signature-256` header against the raw request body.
 *
 * Returns false (never throws) for a missing, malformed or wrong signature.
 * The digest comparison uses `crypto.timingSafeEqual`, so it takes the same
 * time however many leading bytes match.
 */
export function verifySignature(
  secret: string,
  rawBody: Buffer,
  header: string | string[] | undefined
): boolean {
  if (!secret) {
    // An empty secret would make every signature trivially forgeable.
    throw new Error("Webhook secret must not be empty");
  }
  if (typeof header !== "string") return false;
  const match = SIGNATURE_PATTERN.exec(header.trim());
  if (!match) return false;

  const received = Buffer.from(match[1], "hex");
  const expected = createHmac("sha256", secret).update(rawBody).digest();
  // Both are 32 bytes here (the pattern fixes the length), which
  // timingSafeEqual requires.
  return received.length === expected.length && timingSafeEqual(received, expected);
}

/** Compute the header value GitHub would send. Used by tests and tooling. */
export function signPayload(secret: string, rawBody: Buffer | string): string {
  return `sha256=${createHmac("sha256", secret).update(rawBody).digest("hex")}`;
}
