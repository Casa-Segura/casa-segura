#!/usr/bin/env node
/**
 * FE-only precursor to CS-337 ESLint registry enforcement.
 * Fails when the canonical BR-07 substring appears outside the allowlisted files.
 */
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const SUBSTRING = "Esto no es asesoría legal";
/** Paths relative to this script's cwd (frontend/) */
const ALLOWLIST = new Set([
  path.join("src", "legal", "disclaimer.ts"),
  path.join("src", "legal", "disclaimer.test.ts"),
]);

const EXTENSIONS_RE = /\.(mts|cts|tsx|ts|jsx|js)$/i;

async function walk(dir, out) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const ent of entries) {
    const full = path.join(dir, ent.name);
    if (ent.name === "node_modules" || ent.name === ".next") continue;
    if (ent.isDirectory()) await walk(full, out);
    else if (EXTENSIONS_RE.test(ent.name)) out.push(full);
  }
}

async function main() {
  const cwd = process.cwd();
  const srcRoot = path.join(cwd, "src");
  const hits = [];

  /** @type {string[]} */
  const files = [];
  await walk(srcRoot, files);

  for (const abs of files) {
    const rel = path.relative(cwd, abs);
    try {
      const text = await fs.readFile(abs, "utf8");
      if (!text.includes(SUBSTRING)) continue;

      if (!ALLOWLIST.has(rel)) {
        hits.push(rel);
      }
    } catch {
      /* skip unreadables */
    }
  }

  if (hits.length) {
    console.error(
      `[check-br07] BR-07 literal found outside disclaimer registry (${SUBSTRING}). Offenders:`,
      hits.join(", "),
    );
    console.error(
      "[check-br07] Canonical copy must come from `@/legal/disclaimer-registry` → `@/legal/disclaimer.ts`.",
    );
    process.exitCode = 1;
  }
}

await main();
