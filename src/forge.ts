import fs from "node:fs/promises";
import path from "node:path";
import type { RecipeDefinition } from "./recipes/index.js";

export interface ForgeOptions {
  recipe: RecipeDefinition;
  outputDir: string;
  force?: boolean;
  projectName?: string;
}

export interface ForgeManifest {
  recipeId: string;
  recipeVersion: string;
  createdAt: string;
  projectName: string;
  files: string[];
}

const VAR_PATTERN = /\{\{(\w+)\}\}/g;

async function pathExists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function isDirectoryEmpty(dir: string): Promise<boolean> {
  const entries = await fs.readdir(dir);
  return entries.length === 0;
}

function substituteVars(content: string, vars: Record<string, string>): string {
  return content.replace(VAR_PATTERN, (_, key: string) => vars[key] ?? "");
}

async function collectTemplateFiles(
  templateDir: string,
  base = ""
): Promise<string[]> {
  const entries = await fs.readdir(path.join(templateDir, base), {
    withFileTypes: true,
  });
  const files: string[] = [];
  for (const entry of entries) {
    const rel = base ? `${base}/${entry.name}` : entry.name;
    if (entry.name === "recipe.json") continue;
    if (entry.isDirectory()) {
      files.push(...(await collectTemplateFiles(templateDir, rel)));
    } else {
      files.push(rel);
    }
  }
  return files;
}

export async function runForge(options: ForgeOptions): Promise<ForgeManifest> {
  const { recipe, outputDir, force = false, projectName = "my-project" } =
    options;

  if (!(await pathExists(recipe.templateDir))) {
    throw new Error(`Template directory not found: ${recipe.templateDir}`);
  }

  if (await pathExists(outputDir)) {
    if (!(await isDirectoryEmpty(outputDir))) {
      if (!force) {
        throw new Error(
          `Output directory is not empty: ${outputDir}. Use --force to overwrite.`
        );
      }
    }
  } else {
    await fs.mkdir(outputDir, { recursive: true });
  }

  const vars: Record<string, string> = {
    projectName,
    year: String(new Date().getFullYear()),
  };

  const relativeFiles = await collectTemplateFiles(recipe.templateDir);
  const writtenFiles: string[] = [];

  for (const rel of relativeFiles) {
    const src = path.join(recipe.templateDir, rel);
    const dest = path.join(outputDir, rel);
    await fs.mkdir(path.dirname(dest), { recursive: true });

    const raw = await fs.readFile(src, "utf8");
    const isText = !rel.endsWith(".png") && !rel.endsWith(".ico");
    const content = isText ? substituteVars(raw, vars) : raw;
    if (isText) {
      await fs.writeFile(dest, content, "utf8");
    } else {
      await fs.writeFile(dest, await fs.readFile(src));
    }
    writtenFiles.push(rel);
  }

  const manifest: ForgeManifest = {
    recipeId: recipe.id,
    recipeVersion: recipe.version,
    createdAt: new Date().toISOString(),
    projectName,
    files: writtenFiles.sort(),
  };

  await fs.writeFile(
    path.join(outputDir, "forge.manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n",
    "utf8"
  );

  return manifest;
}
