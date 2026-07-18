#!/usr/bin/env node
/**
 * ci/review.js — headless code review runner.
 *
 * Runs the same review checklist as agents/code-reviewer.md, but non-interactively:
 * no branch guard, no developer confirmation prompts, no @gatekeeper (that validates
 * against a spec/HLD that only exists inside the interactive /task flow). This is
 * Stage 1 of CI integration — it prints a structured verdict to stdout and a log file.
 * You paste that into the PR/MR manually. Stage 2 (auto-post via gh/GitLab API) is a
 * ~20-line addition once you're happy with Stage 1's output quality — see the bottom
 * of this file.
 *
 * Zero npm dependencies. Requires Node 18+ (native fetch) and git on PATH.
 *
 * Usage:
 *   ANTHROPIC_API_KEY=sk-... node ci/review.js --base main --head HEAD
 *   node ci/review.js --diff path/to/change.diff        # review a diff file instead of git
 *   node ci/review.js --base main --head HEAD --dry-run # print the assembled prompt, no API call
 *   node ci/review.js --base main --head HEAD --no-fail # always exit 0, even on REQUEST CHANGES
 *
 * Env vars:
 *   ANTHROPIC_API_KEY   required (unless --dry-run)
 *   ANTHROPIC_MODEL     optional, default: claude-sonnet-5
 */

const { execFileSync } = require("child_process");
const fs   = require("fs");
const path = require("path");

const REPO = path.resolve(__dirname, "..");

// ── CLI args ─────────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const args = { base: "main", head: "HEAD", model: process.env.ANTHROPIC_MODEL || "claude-sonnet-5" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--base") args.base = argv[++i];
    else if (a === "--head") args.head = argv[++i];
    else if (a === "--diff") args.diffFile = argv[++i];
    else if (a === "--model") args.model = argv[++i];
    else if (a === "--title") args.title = argv[++i];
    else if (a === "--desc") args.desc = argv[++i];
    else if (a === "--dry-run") args.dryRun = true;
    else if (a === "--no-fail") args.noFail = true;
    else if (a === "--max-diff-chars") args.maxDiffChars = parseInt(argv[++i], 10);
    else {
      console.error(`Unknown argument: ${a}`);
      process.exit(2);
    }
  }
  return args;
}

// ── Diff collection ──────────────────────────────────────────────────────────

function getDiff(args) {
  if (args.diffFile) {
    return {
      diff: fs.readFileSync(args.diffFile, "utf8"),
      files: [], // unknown when reading a raw diff file — fine, the diff itself lists paths
    };
  }
  const diff = execFileSync(
    "git", ["diff", "--unified=3", `${args.base}...${args.head}`],
    { cwd: REPO, maxBuffer: 1024 * 1024 * 50 }
  ).toString();
  const files = execFileSync(
    "git", ["diff", "--name-only", `${args.base}...${args.head}`],
    { cwd: REPO }
  ).toString().trim().split("\n").filter(Boolean);
  return { diff, files };
}

// ── Skill / agent instruction loading ───────────────────────────────────────

function stripFrontmatter(text) {
  return text.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "").trim();
}

function loadSkill(name) {
  const p = path.join(REPO, "skills", name, "SKILL.md");
  if (!fs.existsSync(p)) {
    console.error(`  ! skill not found, skipping: ${name}`);
    return "";
  }
  return `\n\n## Skill: ${name}\n\n${stripFrontmatter(fs.readFileSync(p, "utf8"))}`;
}

// Mirrors code-reviewer.md's "Always load" list.
const ALWAYS_LOAD_SKILLS = [
  "agent-guidelines",
  "linting-tools",
  "pattern-enforcement",
  "code-standards",
  "static-code-analysis",
  "atomic-changes",
  "third-party-policy",
];

// Mirrors code-reviewer.md's "Load based on what is in the diff" — simple heuristics,
// good enough for v1. Tighten as needed once you see false positive/negative loads.
function conditionalSkills(files, diffText) {
  const skills = [];
  const ext = (f) => path.extname(f).toLowerCase();
  const hasCode = files.some((f) => [".js", ".ts", ".tsx", ".jsx", ".java", ".kt"].includes(ext(f)));
  const hasTests = files.some((f) => /\.(test|spec)\.|Test\.java$/.test(f));
  const touchesAuth = /\b(auth|password|token|jwt|permission|session)\b/i.test(diffText);
  const touchesDeps = files.some((f) => /package\.json|pom\.xml|build\.gradle|requirements\.txt/.test(f));

  if (hasCode) {
    skills.push(
      "clean-code-naming", "clean-code-functions", "clean-code-comments",
      "clean-code-classes", "clean-code-solid", "clean-code-error-handling",
      "readability-cognitive-load"
    );
  }
  if (hasTests) skills.push("clean-code-tests");
  if (touchesAuth) skills.push("clean-code-security");
  if (touchesDeps) skills.push("xray-scanning");

  return [...new Set(skills)];
}

function buildSystemPrompt(files, diffText) {
  const agentBody = stripFrontmatter(
    fs.readFileSync(path.join(REPO, "agents", "code-reviewer.md"), "utf8")
  );

  let prompt = agentBody;
  prompt += "\n\n# Loaded skills\n";
  console.error("Loading skills:");
  for (const s of ALWAYS_LOAD_SKILLS) {
    console.error(`  - ${s} (always)`);
    prompt += loadSkill(s);
  }
  for (const s of conditionalSkills(files, diffText)) {
    console.error(`  - ${s} (conditional)`);
    prompt += loadSkill(s);
  }

  prompt +=
    "\n\n# Headless CI context\n" +
    "You are running headlessly in CI, not in an interactive agent session. There is " +
    "no developer to ask questions of and no spec/HLD from an earlier orchestrator " +
    "step — this diff may have come from anywhere. Treat the 'Change matches the " +
    "agreed spec and chosen HLD' and any other checklist item that assumes a prior " +
    "orchestrator step as N/A and say so explicitly; do not fail the review on it. " +
    "Everything else in your checklist (pattern compliance, clean code, SOLID, " +
    "security, atomicity-as-a-general-principle, tests) applies normally.";

  return prompt;
}

// ── Anthropic API call ───────────────────────────────────────────────────────

async function callClaude(model, systemPrompt, userMessage) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("ANTHROPIC_API_KEY is not set.");
    process.exit(2);
  }
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model,
      max_tokens: 4096,
      system: systemPrompt,
      messages: [{ role: "user", content: userMessage }],
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Anthropic API error ${res.status}: ${body}`);
  }
  const data = await res.json();
  return data.content.filter((b) => b.type === "text").map((b) => b.text).join("\n");
}

// ── Verdict parsing (for CI exit code) ──────────────────────────────────────

function extractVerdict(reportText) {
  if (/REQUEST CHANGES/i.test(reportText)) return "REQUEST_CHANGES";
  if (/APPROVED WITH ADVISORY NOTES/i.test(reportText)) return "APPROVED_WITH_NOTES";
  if (/\bAPPROVED\b/i.test(reportText)) return "APPROVED";
  return "UNKNOWN";
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { diff, files } = getDiff(args);

  if (!diff.trim()) {
    console.log("No changes to review.");
    process.exit(0);
  }

  const maxChars = args.maxDiffChars || 200_000; // ~50K tokens, generous for most PRs
  let diffForPrompt = diff;
  if (diff.length > maxChars) {
    console.error(
      `! Diff is ${diff.length} chars, truncating to ${maxChars}. ` +
      `Large PR — consider reviewing in smaller pieces, same principle as atomic-changes.`
    );
    diffForPrompt = diff.slice(0, maxChars) + "\n\n[...diff truncated...]";
  }

  const systemPrompt = buildSystemPrompt(files, diff);
  const userMessage =
    `# PR under review\n` +
    (args.title ? `Title: ${args.title}\n` : "") +
    (args.desc ? `Description: ${args.desc}\n` : "") +
    `\nChanged files:\n${files.map((f) => `- ${f}`).join("\n") || "(unknown — reading from raw diff file)"}\n\n` +
    `\`\`\`diff\n${diffForPrompt}\n\`\`\``;

  if (args.dryRun) {
    console.log("── SYSTEM PROMPT ──\n" + systemPrompt);
    console.log("\n── USER MESSAGE ──\n" + userMessage);
    process.exit(0);
  }

  console.error(`\nCalling ${args.model}...`);
  const report = await callClaude(args.model, systemPrompt, userMessage);

  console.log(report);

  const reportsDir = path.join(REPO, "ci", "reports");
  fs.mkdirSync(reportsDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const logPath = path.join(reportsDir, `review-${stamp}.md`);
  fs.writeFileSync(logPath, report, "utf8");
  console.error(`\nSaved: ${logPath}`);

  const verdict = extractVerdict(report);
  console.error(`Verdict: ${verdict}`);

  if (verdict === "REQUEST_CHANGES" && !args.noFail) {
    process.exit(1);
  }
  process.exit(0);
}

main().catch((err) => {
  console.error(err.stack || err.message);
  process.exit(2);
});

/**
 * ── Stage 2 (later): auto-post instead of hand-pasting ──────────────────────
 *
 * GitHub:
 *   const { execFileSync } = require("child_process");
 *   execFileSync("gh", ["pr", "comment", String(prNumber), "--body-file", logPath]);
 *
 * GitLab:
 *   await fetch(
 *     `${GITLAB_URL}/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/notes`,
 *     {
 *       method: "POST",
 *       headers: { "PRIVATE-TOKEN": GITLAB_TOKEN, "content-type": "application/json" },
 *       body: JSON.stringify({ body: report }),
 *     }
 *   );
 *
 * Both need the actual PR/MR number, which your CI system's webhook payload
 * already provides as an env var (e.g. $CI_MERGE_REQUEST_IID on GitLab,
 * $GITHUB_REF / the pull_request event payload on GitHub Actions) — thread
 * that through instead of --base/--head once you're ready.
 */
