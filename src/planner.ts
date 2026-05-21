import fs from "node:fs/promises";
import path from "node:path";
import { default as Ajv } from "ajv";
import type { ErrorObject, ValidateFunction } from "ajv";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  ".."
);

export interface ForgeSpec {
  projectName: string;
  recipe: string;
  description?: string;
  port?: number;
}

export interface PlannedForge {
  spec: ForgeSpec;
  recipe: string;
  vars: Record<string, string>;
}

let validateFn: ValidateFunction | null = null;

async function getValidator(): Promise<ValidateFunction> {
  if (validateFn) return validateFn;
  const schemaPath = path.join(repoRoot, "schemas", "forge-spec.schema.json");
  const schema = JSON.parse(await fs.readFile(schemaPath, "utf8"));
  const ajv = new (Ajv as unknown as new (opts?: object) => {
    compile: (s: object) => ValidateFunction;
  })({ allErrors: true, strict: false });
  validateFn = ajv.compile(schema);
  return validateFn;
}

export async function loadSpecFile(specPath: string): Promise<unknown> {
  const raw = await fs.readFile(path.resolve(specPath), "utf8");
  return JSON.parse(raw) as unknown;
}

export async function validateSpec(data: unknown): Promise<ForgeSpec> {
  const validate = await getValidator();
  if (!validate(data)) {
    const detail = (validate.errors ?? [])
      .map((e: ErrorObject) => `${e.instancePath || "/"} ${e.message}`)
      .join("; ");
    throw new Error(`Spec validation failed: ${detail}`);
  }
  return data as ForgeSpec;
}

export function planFromSpec(spec: ForgeSpec): PlannedForge {
  const port = spec.port ?? (spec.recipe === "express-api" ? 3000 : 0);
  return {
    spec,
    recipe: spec.recipe,
    vars: {
      projectName: spec.projectName,
      description: spec.description ?? "",
      port: String(port),
      year: String(new Date().getFullYear()),
    },
  };
}

export async function planFromSpecFile(specPath: string): Promise<PlannedForge> {
  const data = await loadSpecFile(specPath);
  const spec = await validateSpec(data);
  return planFromSpec(spec);
}
