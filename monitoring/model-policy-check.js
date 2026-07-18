#!/usr/bin/env node
/**
 * monitoring/model-policy-check.js
 *
 * opencode-usage already answers "how many tokens, which models, by agent,
 * over 24h/7d/30d" — see monitoring/README.md. This script answers the one
 * question it can't: "did each agent actually run on the model it's SUPPOSED
 * to run on?"
 *
 * The expected model per agent is read directly from each agents/*.md file's
 * own frontmatter — not a separate policy table. If you retune an agent's
 * model in its file, this check picks it up automatically; nothing to keep
 * in sync by hand.
 *
 * Requires: opencode-usage installed (setup.py wires this — see
 * install_opencode_usage() in setup.py).
 *
 * Usage:
 *   node monitoring/model-policy-check.js                # last 7 days
 *   node monitoring/model-policy-check.js --since 24h     # last 24h (maps to --days 1)
 *   node monitoring/model-policy-check.js --since 30d
 */

const { execFileSync } = require("child_process");
const fs   = require("fs");
const path = require("path");

const REPO = path.resolve(__dirname, "..");

function parseArgs(argv) {
  const args = { since: "7d" };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--since") args.since = argv[++i];
  }
  return args;
}

// ── Policy source: each agent file's own frontmatter ────────────────────────

function loadExpectedModels() {
  const dir = path.join(REPO, "agents");
  const expected = {};
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith(".md")) continue;
    const agent = file.replace(/\.md$/, "");
    const text = fs.readFileSync(path.join(dir, file), "utf8");
    const match = text.match(/^model:\s*(\S+)\s*$/m);
    if (match) expected[agent] = match[1];
  }
  return expected;
}

// ── Actual usage: shell out to opencode-usage (it owns the DB access) ──────

function loadActualUsage(since) {
  // opencode-usage confirms 'd'/'w'/ISO for --since; there's no native 24h unit,
  // so map that one case to --days 1 for an equivalent window.
  const args = since === "24h"
    ? ["run", "--by", "agent", "--days", "1", "--json"]
    : ["run", "--by", "agent", "--since", since, "--json"];

  let raw;
  try {
    raw = execFileSync("opencode-usage", args, { encoding: "utf8" });
  } catch (err) {
    console.error("Could not run opencode-usage — is it installed?");
    console.error("  uv tool install opencode-usage   (or: pip install opencode-usage)");
    process.exit(2);
  }

  const data = JSON.parse(raw);
  // Expected shape per README: { rows: [{ label/agent, model, total, calls, cost, ... }] }
  // Normalize defensively since this is an external tool's JSON contract.
  const rows = data.rows || data;
  return rows.map((r) => ({
    agent: r.agent || r.label,
    model: r.model,
    tokens: r.total ?? r.tokens ?? 0,
    calls: r.calls ?? 0,
  })).filter((r) => r.agent && r.model);
}

// ── Cross-reference ──────────────────────────────────────────────────────────

function shortModel(m) {
  // "anthropic/claude-sonnet-4-6" -> "claude-sonnet-4-6" for compact display
  return m.includes("/") ? m.split("/").slice(1).join("/") : m;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const expected = loadExpectedModels();
  const actual = loadActualUsage(args.since);

  if (actual.length === 0) {
    console.log(`No usage recorded for the last ${args.since}.`);
    return;
  }

  const rows = actual.map((r) => {
    const exp = expected[r.agent];
    const status = !exp ? "?" : (r.model === exp || r.model.endsWith(exp) || exp.endsWith(r.model))
      ? "OK" : "MISMATCH";
    return { ...r, expected: exp || "(unknown agent)", status };
  });

  const totalTokens = rows.reduce((s, r) => s + r.tokens, 0);
  const mismatches = rows.filter((r) => r.status === "MISMATCH");

  console.log(`\nModel policy check — last ${args.since}`);
  console.log("=".repeat(60));
  console.log(`Total tokens: ${totalTokens.toLocaleString()}   Agents seen: ${new Set(rows.map(r => r.agent)).size}\n`);

  console.log("Agent".padEnd(24) + "Actual model".padEnd(22) + "Tokens".padEnd(12) + "Status");
  console.log("-".repeat(60));
  for (const r of rows.sort((a, b) => b.tokens - a.tokens)) {
    const mark = r.status === "OK" ? "OK" : r.status === "MISMATCH" ? "!! MISMATCH" : "?  unknown";
    console.log(
      r.agent.padEnd(24) +
      shortModel(r.model).padEnd(22) +
      r.tokens.toLocaleString().padEnd(12) +
      mark
    );
  }

  if (mismatches.length > 0) {
    console.log("\n" + "!".repeat(60));
    console.log(`${mismatches.length} agent(s) ran on a different model than declared:`);
    for (const m of mismatches) {
      console.log(`  - ${m.agent}: ran on ${shortModel(m.model)}, expected ${shortModel(m.expected)}`);
    }
    console.log("If this is intentional (e.g. a manual override), no action needed.");
    console.log("If not, check the model: field in agents/" + (mismatches[0].agent) + ".md and your opencode.json.");
  } else {
    console.log("\nAll agents ran on their declared model.");
  }
}

main();
