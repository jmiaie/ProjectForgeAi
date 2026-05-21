import { describe, expect, it } from "vitest";
import { planFromSpec, validateSpec } from "./planner.js";

describe("planner", () => {
  it("validates a good spec", async () => {
    const spec = await validateSpec({
      projectName: "my-api",
      recipe: "express-api",
      port: 4000,
    });
    expect(spec.projectName).toBe("my-api");
  });

  it("rejects invalid project name", async () => {
    await expect(
      validateSpec({ projectName: "Bad_Name", recipe: "minimal" })
    ).rejects.toThrow(/validation failed/i);
  });

  it("plans template variables", () => {
    const planned = planFromSpec({
      projectName: "demo",
      recipe: "express-api",
      description: "test",
      port: 8080,
    });
    expect(planned.vars.projectName).toBe("demo");
    expect(planned.vars.port).toBe("8080");
    expect(planned.recipe).toBe("express-api");
  });
});
