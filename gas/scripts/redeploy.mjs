#!/usr/bin/env node
/**
 * Push local GAS files and update an existing Web App deployment without changing its URL.
 * Usage:
 *   npm run redeploy -- [DEPLOYMENT_ID] [DESCRIPTION]
 * Or set GAS_DEPLOYMENT_ID in gas/.env
 */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const gasDir = path.resolve(__dirname, "..");
const envPath = path.join(gasDir, ".env");
const claspJsonPath = path.join(gasDir, ".clasp.json");

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const out = {};
  for (const rawLine of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    let val = line.slice(eq + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    out[key] = val;
  }
  return out;
}

function resolveClaspBin() {
  const localBin = path.join(
    gasDir,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "clasp.cmd" : "clasp"
  );
  return fs.existsSync(localBin) ? localBin : "clasp";
}

function runClasp(args) {
  const res = spawnSync(resolveClaspBin(), args, {
    cwd: gasDir,
    stdio: "inherit",
  });
  if (res.status !== 0) {
    process.exit(res.status ?? 1);
  }
}

if (!fs.existsSync(claspJsonPath)) {
  console.error("Error: gas/.clasp.json not found. Run `npm run setup -- <SCRIPT_ID>` first.");
  process.exit(1);
}

const fileEnv = loadEnvFile(envPath);
const cliArgs = process.argv.slice(2);
const deploymentId = (cliArgs[0] || process.env.GAS_DEPLOYMENT_ID || fileEnv.GAS_DEPLOYMENT_ID || "").trim();
const description =
  cliArgs[1] || `Auto deploy ${new Date().toISOString().replace("T", " ").slice(0, 19)}Z`;

if (!deploymentId || deploymentId === "YOUR_DEPLOYMENT_ID_HERE") {
  console.error("Error: Deployment ID is required.");
  console.error("Run `npm run deployments` to inspect IDs, then either:");
  console.error("  1) Set GAS_DEPLOYMENT_ID=... in gas/.env");
  console.error("  2) Pass it directly: npm run redeploy -- <DEPLOYMENT_ID> \"description\"");
  process.exit(1);
}

console.log("[1/2] Pushing gas/src to Apps Script...");
runClasp(["push"]);

console.log(`[2/2] Updating deployment ${deploymentId}...`);
runClasp(["deploy", "-i", deploymentId, "-d", description]);
console.log("Done. Web App URL remains unchanged.");
