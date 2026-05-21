import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../.."
);

export interface RecipeDefinition {
  id: string;
  version: string;
  description: string;
  templateDir: string;
}

const recipes: Record<string, RecipeDefinition> = {
  minimal: {
    id: "minimal",
    version: "1.0.0",
    description: "Minimal Node.js project with README and CI stub",
    templateDir: path.join(repoRoot, "templates", "minimal"),
  },
  "express-api": {
    id: "express-api",
    version: "1.0.0",
    description: "Express HTTP API with health route and CI",
    templateDir: path.join(repoRoot, "templates", "express-api"),
  },
};

export function listRecipes(): RecipeDefinition[] {
  return Object.values(recipes);
}

export function getRecipe(name: string): RecipeDefinition | undefined {
  return recipes[name];
}
