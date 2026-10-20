import { describe, expect, it } from "vitest";
import { signPayload, verifySignature } from "./signature.js";

const SECRET = "test-webhook-secret";
const BODY = Buffer.from(JSON.stringify({ action: "labeled" }));

describe("verifySignature", () => {
  it("accepts GitHub's sha256 signature for the exact body", () => {
    expect(verifySignature(SECRET, BODY, signPayload(SECRET, BODY))).toBe(true);
  });

  it("matches a known GitHub test vector", () => {
    // From GitHub's "Validating webhook deliveries" docs.
    const body = Buffer.from("Hello, World!");
    const header =
      "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17";
    expect(verifySignature("It's a Secret to Everybody", body, header)).toBe(true);
  });

  it("rejects a missing header", () => {
    expect(verifySignature(SECRET, BODY, undefined)).toBe(false);
    expect(verifySignature(SECRET, BODY, "")).toBe(false);
  });

  it("rejects a repeated header", () => {
    const sig = signPayload(SECRET, BODY);
    expect(verifySignature(SECRET, BODY, [sig, sig])).toBe(false);
  });

  it("rejects a signature made with another secret", () => {
    expect(verifySignature(SECRET, BODY, signPayload("other", BODY))).toBe(false);
  });

  it("rejects a tampered body", () => {
    const sig = signPayload(SECRET, BODY);
    expect(verifySignature(SECRET, Buffer.from('{"action":"opened"}'), sig)).toBe(false);
  });

  it("rejects the legacy sha1 header format and malformed values", () => {
    const hex = signPayload(SECRET, BODY).slice("sha256=".length);
    expect(verifySignature(SECRET, BODY, `sha1=${hex}`)).toBe(false);
    expect(verifySignature(SECRET, BODY, hex)).toBe(false);
    expect(verifySignature(SECRET, BODY, `sha256=${hex.slice(0, 63)}`)).toBe(false);
    expect(verifySignature(SECRET, BODY, `sha256=${hex}00`)).toBe(false);
    expect(verifySignature(SECRET, BODY, `sha256=${"z".repeat(64)}`)).toBe(false);
  });

  it("refuses to verify with an empty secret", () => {
    expect(() => verifySignature("", BODY, signPayload("", BODY))).toThrow(/secret/);
  });
});
