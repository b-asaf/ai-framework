#!/usr/bin/env python3
"""Gap 1 regression test: does a granted `task` permission actually result
in a real Task() delegation, every time, across multiple independent runs?

Automates the manual procedure DEC-014 specified: run `/review` headlessly,
and for every `permission=task ... action=allow` line in the debug log,
confirm a real subagent session was actually created afterward — not just
that the permission check passed. Per DEC-014's own standard (learned from
Findings D and F both failing on a single clean-looking run), one pass is
not evidence; this runs N times and reports per-run and aggregate results.

USAGE:
    python test_gap1_delegation.py --repo D:\\path\\to\\real-repo --runs 5

Requires: `opencode` on PATH, run from a machine with the framework
installed (agents/, opencode.json, etc. — this only invokes opencode, it
doesn't reimplement any framework logic).

KNOWN LIMITATION — READ BEFORE TRUSTING THE OUTPUT:
The exact format of opencode's --log-level DEBUG output is NOT something
I have direct access to. The patterns below (PERMISSION_ALLOW_PATTERN,
SESSION_PATTERN, AGENT_PATTERN) are built from the specific fragments
quoted in DEC-011/012/013 (e.g. "permission=task pattern=code-reviewer
action=allow", "agent=build mode=primary") — they are a best-effort
reconstruction, not a verified spec. Run this once, then check the
"Unmatched lines containing 'permission' or 'agent='" section it prints
at the end — if real log lines don't look like what these patterns
expect, send me a real (redacted if needed) log excerpt and I'll correct
the patterns against real data instead of guessing again.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# --- Best-effort patterns; see KNOWN LIMITATION above ---
PERMISSION_ALLOW_PATTERN = re.compile(
    r"permission=task\s+pattern=(?P<target>\S+)\s+action=allow"
)
# Matches lines like "agent=code-reviewer" or "agent=build mode=primary" —
# used both to detect the initial agent and any subagent that starts later.
AGENT_PATTERN = re.compile(r"\bagent=(?P<agent>[\w-]+)")
# Matches a session identifier field, under either likely field name.
SESSION_PATTERN = re.compile(r"\b(?:session|sessionID|session_id)=(?P<session>\S+)")


@dataclass
class DelegationCheck:
    target: str
    line_number: int
    delegation_confirmed: bool
    evidence_line: str | None = None


@dataclass
class RunResult:
    run_index: int
    log_path: Path
    exit_code: int
    duration_seconds: float
    checks: list[DelegationCheck] = field(default_factory=list)
    distinct_sessions_seen: int = 0
    unmatched_notable_lines: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.delegation_confirmed for c in self.checks)


def run_once(repo: Path, run_index: int, out_dir: Path) -> RunResult:
    """Invoke `opencode run --command review` headlessly and capture output.

    Uses explicit binary file handles rather than shell redirection —
    shell/PowerShell redirection has already proven unreliable for
    byte-exact output in this repo's history (see the CHANGELOG entry on
    the CRLF investigation), so this avoids that class of bug entirely by
    letting Python own the file writes directly.

    Prints a heartbeat every 15s while waiting. A live foreground run
    showed opencode's own output does not reliably flush to a redirected
    file the way it does to a real terminal — the output files can sit at
    0 bytes for the entire duration of an otherwise-successful run. The
    heartbeat exists so "no visible output" never gets mistaken for "hung"
    again; judge liveness by this, not by file size.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"review-{timestamp}-run{run_index}.json"
    log_path = out_dir / f"review-{timestamp}-run{run_index}.txt"

    opencode_cmd = ["opencode", "run", "--command", "review", "--print-logs", "--log-level", "DEBUG"]
    if sys.platform == "win32":
        # subprocess with a plain arg list bypasses the shell-level PATHEXT
        # resolution that lets you type "opencode" interactively without an
        # extension — opencode is very likely a .cmd shim (typical for
        # npm-installed global CLIs on Windows), and CreateProcess can't
        # launch a .cmd directly without going through cmd.exe. Routing
        # through "cmd /c" resolves .cmd/.bat/.exe the same way an
        # interactive prompt would.
        opencode_cmd = ["cmd", "/c"] + opencode_cmd

    start = time.monotonic()
    with open(json_path, "wb") as stdout_f, open(log_path, "wb") as stderr_f:
        process = subprocess.Popen(
            opencode_cmd,
            cwd=repo,
            stdout=stdout_f,
            stderr=stderr_f,
        )
        heartbeat_interval = 15
        while process.poll() is None:
            time.sleep(heartbeat_interval)
            elapsed = time.monotonic() - start
            out_size = json_path.stat().st_size if json_path.exists() else 0
            log_size = log_path.stat().st_size if log_path.exists() else 0
            print(f"  [run {run_index}] still running — {elapsed:.0f}s elapsed, output files: {out_size}+{log_size} bytes")
        exit_code = process.returncode
    duration = time.monotonic() - start

    # --print-logs may send debug output to either stream depending on
    # opencode's own behavior — read both back and analyze combined.
    combined_text = (
        json_path.read_text(encoding="utf-8", errors="ignore")
        + "\n"
        + log_path.read_text(encoding="utf-8", errors="ignore")
    )

    return analyze_log(combined_text, run_index, log_path, exit_code, duration)


def analyze_log(text: str, run_index: int, log_path: Path, exit_code: int, duration: float) -> RunResult:
    lines = text.splitlines()
    run = RunResult(run_index=run_index, log_path=log_path, exit_code=exit_code, duration_seconds=duration)

    sessions_seen: set[str] = set()
    for line in lines:
        for match in SESSION_PATTERN.finditer(line):
            sessions_seen.add(match.group("session"))
    run.distinct_sessions_seen = len(sessions_seen)

    for i, line in enumerate(lines):
        allow_match = PERMISSION_ALLOW_PATTERN.search(line)
        if not allow_match:
            continue
        target = allow_match.group("target")

        # Look forward for evidence this target actually started running —
        # either its name appearing in a later agent= field, or a new
        # session identifier appearing after this line that wasn't present
        # before it.
        confirmed = False
        evidence = None
        sessions_before = {
            m.group("session")
            for prior_line in lines[:i]
            for m in SESSION_PATTERN.finditer(prior_line)
        }
        for later_line in lines[i + 1 :]:
            agent_match = AGENT_PATTERN.search(later_line)
            if agent_match and agent_match.group("agent") == target:
                confirmed = True
                evidence = later_line.strip()
                break
            session_match = SESSION_PATTERN.search(later_line)
            if session_match and session_match.group("session") not in sessions_before:
                confirmed = True
                evidence = later_line.strip()
                break

        run.checks.append(
            DelegationCheck(target=target, line_number=i + 1, delegation_confirmed=confirmed, evidence_line=evidence)
        )

    # Surface lines that look relevant but didn't match either pattern —
    # this is what tells you the patterns need correcting against real data.
    for line in lines:
        if ("permission" in line or "agent=" in line) and not PERMISSION_ALLOW_PATTERN.search(line):
            if AGENT_PATTERN.search(line) is None and "permission" in line:
                run.unmatched_notable_lines.append(line.strip())

    return run


def print_report(runs: list[RunResult]) -> None:
    print(f"\n{'=' * 70}\nGAP 1 DELEGATION CHECK — {len(runs)} run(s)\n{'=' * 70}\n")

    for run in runs:
        status = "PASS" if run.passed else "FAIL"
        print(f"Run {run.run_index}: {status}  (exit={run.exit_code}, {run.duration_seconds:.1f}s, log={run.log_path.name})")
        if not run.checks:
            print("  No 'permission=task ... action=allow' lines found — either no delegation")
            print("  was attempted this run, or PERMISSION_ALLOW_PATTERN doesn't match the real")
            print("  log format. Check unmatched lines below before trusting a clean PASS.")
        for check in run.checks:
            mark = "✅" if check.delegation_confirmed else "❌"
            print(f"  {mark} target={check.target} (line {check.line_number})", end="")
            if check.delegation_confirmed:
                print(f" — confirmed via: {check.evidence_line[:100]}")
            else:
                print(" — NO evidence of actual delegation found afterward (Gap 1 reproduced)")
        if run.unmatched_notable_lines:
            print(f"  ⚠ {len(run.unmatched_notable_lines)} unmatched line(s) mentioning 'permission' — pattern may need correcting:")
            for line in run.unmatched_notable_lines[:3]:
                print(f"      {line[:120]}")
        print()

    total_checks = sum(len(r.checks) for r in runs)
    total_confirmed = sum(sum(1 for c in r.checks if c.delegation_confirmed) for r in runs)
    all_passed = all(r.passed for r in runs)

    print(f"{'=' * 70}")
    print(f"AGGREGATE: {total_confirmed}/{total_checks} delegation(s) confirmed across {len(runs)} run(s)")
    print(f"Gap 1 status: {'HOLDING (all runs clean)' if all_passed else 'REPRODUCED — at least one silent non-delegation found'}")
    print(f"{'=' * 70}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Path to the repo under review (e.g. real repo)")
    parser.add_argument("--runs", type=int, default=5, help="Number of independent runs (default 5, per DEC-014)")
    parser.add_argument("--out-dir", type=Path, default=Path.cwd(), help="Where to write review-*.json/.txt files")
    args = parser.parse_args()

    if not args.repo.exists():
        print(f"error: --repo path does not exist: {args.repo}", file=sys.stderr)
        return 2

    runs = []
    for i in range(1, args.runs + 1):
        print(f"Starting run {i}/{args.runs}...")
        runs.append(run_once(args.repo, i, args.out_dir))

    print_report(runs)
    return 0 if all(r.passed for r in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())