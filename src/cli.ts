#!/usr/bin/env node
import path from "node:path";
import { getRecipe, listRecipes } from "./recipes/index.js";
import { runForge } from "./forge.js";

function printUsage(): void {
  console.log(`ProjectForgeAi — forge CLI

Usage:
  forge list
  forge run --recipe <name> --output <dir> [--name <project>] [--force]

Options:
  --recipe, -r    Recipe name (e.g. minimal)
  --output, -o    Output directory
  --name, -n      Project name for template substitution (default: my-project)
  --force, -f     Allow writing to a non-empty output directory
  --help, -h      Show this help
`);
}

function parseArgs(argv: string[]): {
  command?: string;
  recipe?: string;
  output?: string;
  name?: string;
  force?: boolean;
  help?: boolean;
} {
  const result: ReturnType<typeof parseArgs> = {};
  const positional: string[] = [];

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      result.help = true;
    } else if (arg === "--force" || arg === "-f") {
      result.force = true;
    } else if (arg === "--recipe" || arg === "-r") {
      result.recipe = argv[++i];
    } else if (arg === "--output" || arg === "-o") {
      result.output = argv[++i];
    } else if (arg === "--name" || arg === "-n") {
      result.name = argv[++i];
    } else if (!arg.startsWith("-")) {
      positional.push(arg);
    }
  }

  result.command = positional[0];
  return result;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  if (args.help || !args.command) {
    printUsage();
    process.exit(args.help ? 0 : 1);
  }

  if (args.command === "list") {
    for (const r of listRecipes()) {
      console.log(`${r.id}@${r.version} — ${r.description}`);
    }
    return;
  }

  if (args.command === "run") {
    if (!args.recipe || !args.output) {
      console.error("Error: --recipe and --output are required for run.\n");
      printUsage();
      process.exit(1);
    }

    const recipe = getRecipe(args.recipe);
    if (!recipe) {
      console.error(`Error: unknown recipe "${args.recipe}". Run forge list.`);
      process.exit(1);
    }

    const outputDir = path.resolve(args.output);
    const manifest = await runForge({
      recipe,
      outputDir,
      force: args.force,
      projectName: args.name ?? "my-project",
    });

    console.log(
      `Forge complete: ${recipe.id}@${recipe.version} → ${outputDir}`
    );
    console.log(`  Project: ${manifest.projectName}`);
    console.log(`  Files:   ${manifest.files.length} (+ forge.manifest.json)`);
    return;
  }

  console.error(`Error: unknown command "${args.command}".\n`);
  printUsage();
  process.exit(1);
}

main().catch((err: unknown) => {
  const message = err instanceof Error ? err.message : String(err);
  console.error(`Error: ${message}`);
  process.exit(1);
});
