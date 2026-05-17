/**
 * Self-host PDF.js worker for Next.js (avoids bundler worker URL issues).
 * Run via package.json postinstall.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

let src;
try {
  src = require.resolve("pdfjs-dist/build/pdf.worker.min.mjs");
} catch {
  src = path.join(
    path.dirname(require.resolve("react-pdf/package.json")),
    "node_modules",
    "pdfjs-dist",
    "build",
    "pdf.worker.min.mjs",
  );
}

const destDir = path.join(root, "public");
const dest = path.join(destDir, "pdf.worker.min.mjs");

if (!fs.existsSync(src)) {
  console.warn("[copy-pdf-worker] pdf.worker.min.mjs not found at", src);
  process.exit(0);
}
fs.mkdirSync(destDir, { recursive: true });
fs.copyFileSync(src, dest);
console.log("[copy-pdf-worker] copied to public/pdf.worker.min.mjs");
