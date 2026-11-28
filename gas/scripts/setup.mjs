#!/usr/bin/env node
/**
 * Link an existing Google Apps Script project to gas/.clasp.json and optionally pull its code.
 * Usage:
 *   npm run setup -- <SCRIPT_ID>
 *   npm run setup -- <SCRIPT_ID> --pull
 */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const gasDir = path.resolve(__dirname, "..");
const claspJsonPath = path.join(gasDir, ".clasp.json");
const srcDir = path.join(gasDir, "src");

function resolveClaspBin() {
  const localBin = path.join(
    gasDir,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "clasp.cmd" : "clasp"
  );
  return fs.existsSync(localBin) ? localBin : "clasp";
}

const args = process.argv.slice(2);
const shouldPull = args.includes("--pull");
const scriptId = args.find((a) => !a.startsWith("-"))?.trim();

if (!scriptId) {
  console.error("Usage: npm run setup -- <SCRIPT_ID> [--pull]");
  console.error("Hint: Find your Script ID in GAS Editor -> Project Settings (歯車アイコン) -> スクリプト ID");
  process.exit(1);
}

if (!/^[A-Za-z0-9_-]{20,}$/.test(scriptId)) {
  console.error(`Invalid scriptId format: "${scriptId}"`);
  process.exit(1);
}

fs.mkdirSync(srcDir, { recursive: true });

const config = {
  scriptId,
  rootDir: "./src",
};
fs.writeFileSync(claspJsonPath, JSON.stringify(config, null, 2) + "\n", "utf8");
console.log(`Wrote ${claspJsonPath} (rootDir: ./src)`);

if (shouldPull) {
  const claspBin = resolveClaspBin();
  console.log("Running clasp pull...");
  const res = spawnSync(claspBin, ["pull"], {
    cwd: gasDir,
    stdio: "inherit",
  });
  process.exit(res.status ?? 1);
} else {
  console.log("Next step: run `npm run pull` to fetch your existing GAS files into gas/src/");
}
