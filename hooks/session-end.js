#!/usr/bin/env node
/**
 * session-end.js — Recall-style Stop hook for Claude Code
 *
 * Fires on the Claude Code "Stop" lifecycle event (session ends).
 * Reads the session transcript, produces a compact summary,
 * and appends it to docs/session-summary.md.
 *
 * Wired via ~/.claude/hooks/ by setup.py.
 * No API calls. No model tokens. Pure local file I/O.
 *
 * Hook event: Stop
 */

const fs   = require("fs");
const path = require("path");

// ── Read hook input from stdin ───────────────────────────────────────────────

let input = "";
process.stdin.resume();
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => { input += chunk; });
process.stdin.on("end", () => {
  try {
    run(JSON.parse(input));
  } catch {
    // Never crash the hook — silently exit
    process.exit(0);
  }
});

function run(event) {
  const cwd         = event.cwd || process.cwd();
  const summaryFile = path.join(cwd, "docs", "session-summary.md");
  const messages    = event.messages || [];

  if (messages.length === 0) {
    process.exit(0);
  }

  // ── Extract key facts from the session ──────────────────────────────────

  const date    = new Date().toISOString().split("T")[0];
  const changed = extractChangedFiles(messages);
  const pending = extractPending(messages);
  const summary = buildSummary(messages);

  // ── Build the entry ──────────────────────────────────────────────────────

  const entry = [
    ``,
    `## Session — ${date}`,
    ``,
    `### What changed`,
    changed.length ? changed.map(f => `- ${f}`).join("\n") : "- (no file changes detected)",
    ``,
    `### Summary`,
    summary,
    ``,
    pending ? `### Pending\n${pending}` : null,
  ].filter(l => l !== null).join("\n");

  // ── Append to docs/session-summary.md ───────────────────────────────────

  const docsDir = path.join(cwd, "docs");
  if (!fs.existsSync(docsDir)) {
    fs.mkdirSync(docsDir, { recursive: true });
  }

  const header = `# Session Summary\n> Load this at the start of a new session to restore context.\n`;
  if (!fs.existsSync(summaryFile)) {
    fs.writeFileSync(summaryFile, header, "utf8");
  }

  fs.appendFileSync(summaryFile, entry + "\n", "utf8");
  process.exit(0);
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function extractChangedFiles(messages) {
  const files = new Set();
  const pattern = /(?:wrote|created|updated|modified|edited)\s+[`"]?([^\s`"]+\.[a-zA-Z]+)[`"]?/gi;
  for (const msg of messages) {
    const text = typeof msg.content === "string" ? msg.content
      : Array.isArray(msg.content) ? msg.content.map(b => b.text || "").join(" ")
      : "";
    let m;
    while ((m = pattern.exec(text)) !== null) {
      const f = m[1];
      if (!f.includes("node_modules") && !f.startsWith(".git")) {
        files.add(f);
      }
    }
  }
  return [...files].slice(0, 8);
}

function extractPending(messages) {
  // Look for explicit "next steps" or "remaining" language in the last assistant message
  const last = [...messages].reverse().find(m => m.role === "assistant");
  if (!last) return null;
  const text = typeof last.content === "string" ? last.content
    : Array.isArray(last.content) ? last.content.map(b => b.text || "").join(" ")
    : "";
  const match = text.match(/(?:next steps?|remaining|still need to|todo)[:\s]+([^\n.]{10,120})/i);
  return match ? match[1].trim() : null;
}

function buildSummary(messages) {
  // Take the last assistant response and trim it to ~200 chars
  const last = [...messages].reverse().find(m => m.role === "assistant");
  if (!last) return "(session ended without assistant response)";
  const text = typeof last.content === "string" ? last.content
    : Array.isArray(last.content) ? last.content.map(b => b.text || "").join(" ")
    : "";
  const clean = text.replace(/\s+/g, " ").trim();
  return clean.length > 200 ? clean.slice(0, 197) + "..." : clean;
}
