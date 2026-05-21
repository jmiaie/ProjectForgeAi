import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("{{projectName}}", () => {
  it("loads server module", async () => {
    const mod = await import("./server.js");
    assert.ok(mod.default);
  });
});
