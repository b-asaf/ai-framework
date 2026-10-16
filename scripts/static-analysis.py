#!/usr/bin/env python3
"""Static analysis gate: lizard (complexity) and jscpd (duplication) on the given paths.

It prints facts and the reviewer judges scope. Nothing is written into the project (F26): jscpd runs with the
console reporter only. A run that analyzed no files is reported as NOT_ANALYZED, never as a pass (F29).

Exit codes: 0 OK, PARTIAL or NOT_APPLICABLE; 1 a threshold failed; 2 usage error; 3 a tool is missing or broke.
"""
import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

CCN_LIMIT = 10
DUP_LIMIT = 10.0
MIN_LINES = 5
MIN_TOKENS = 50
LARGE_FILE_LINES = 50
CODE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".py", ".cs", ".go"}
SKIP_DIRS = {".git", "node_modules", ".jscpd-report"}
ANSI = re.compile(r"\x1b\[[0-9;]*m")
WARNING = re.compile(r".+:\d+: warning: .+")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


class Check(NamedTuple):
    verdict: str
    details: list
    reason: str = ""
    install: str = ""


def parse_lizard_warnings(text):
    return [line.strip() for line in text.splitlines() if WARNING.fullmatch(line.strip())]


def parse_jscpd_total(text):
    """Read the Total row of jscpd's console table; return None when it is not there."""
    for line in ANSI.sub("", text).splitlines():
        if "Total:" not in line:
            continue
        numbers = NUMBER.findall(line.split("Total:", 1)[1])
        if len(numbers) < 8:
            continue
        return {
            "files": int(numbers[0]),
            "lines": int(numbers[1]),
            "clones": int(numbers[3]),
            "percent": float(numbers[5]),
        }
    return None


def classify_duplication(total, largest_lines):
    if total is None:
        return "ERROR", "could not read the jscpd summary"
    if total["files"] == 0:
        if largest_lines >= LARGE_FILE_LINES:
            return "ERROR", "jscpd analyzed no files although an input file has %d lines" % largest_lines
        return "NOT_ANALYZED", "no input file reached the minimum block size (%d lines, %d tokens)" % (
            MIN_LINES,
            MIN_TOKENS,
        )
    if total["percent"] > DUP_LIMIT:
        return "FAIL", "duplication %.2f%% is above the %g%% limit" % (total["percent"], DUP_LIMIT)
    return "OK", ""


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, ANSI.sub("", proc.stdout + "\n" + proc.stderr)


def collect_files(paths):
    files, missing = [], []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            if path.suffix.lower() in CODE_SUFFIXES:
                files.append(path)
        elif path.is_dir():
            files += [
                f
                for f in sorted(path.rglob("*"))
                if f.is_file() and f.suffix.lower() in CODE_SUFFIXES and not SKIP_DIRS.intersection(f.parts)
            ]
        else:
            missing.append(raw)
    return files, missing


def line_count(path):
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def check_complexity(names):
    if importlib.util.find_spec("lizard") is None:
        return Check("ERROR", [], "lizard is not installed", "pip install lizard")
    try:
        code, text = run([sys.executable, "-m", "lizard", "--warnings_only", "--CCN", str(CCN_LIMIT), *names])
    except OSError as exc:
        return Check("ERROR", [], "could not run lizard: %s" % exc)
    warnings = parse_lizard_warnings(text)
    if warnings:
        return Check("FAIL", ["WARNING: " + w for w in warnings])
    if code != 0:
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "no output")
        return Check("ERROR", [], "lizard exited %d without a warning: %s" % (code, first))
    return Check("OK", [])


def check_duplication(names, largest_lines):
    exe = shutil.which("jscpd")
    if exe is None:
        return Check("ERROR", [], "jscpd is not installed", "npm install -g jscpd")
    try:
        _code, text = run(
            [exe, "--min-lines", str(MIN_LINES), "--min-tokens", str(MIN_TOKENS), "--reporters", "console", *names]
        )
    except OSError as exc:
        return Check("ERROR", [], "could not run jscpd: %s" % exc)
    total = parse_jscpd_total(text)
    verdict, reason = classify_duplication(total, largest_lines)
    details = []
    if total is not None:
        details = ["DUP_FILES: %d" % total["files"], "DUP_PERCENT: %.2f" % total["percent"]]
    return Check(verdict, details, reason)


def emit(status, lines, reasons, installs, code):
    print("STATUS: " + status)
    for line in lines:
        print(line)
    for reason in reasons:
        print("REASON: " + reason)
    for install in installs:
        print("INSTALL: " + install)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", help="changed files or folders")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    files, missing = collect_files(args.paths)
    if missing:
        return emit("ERROR", [], ["path not found: " + ", ".join(missing)], [], 3)
    if not files:
        return emit("NOT_APPLICABLE", ["FILES: 0"], ["no supported source files in the given paths"], [], 0)

    names = [str(f) for f in files]
    largest = max(line_count(f) for f in files)
    complexity = check_complexity(names)
    duplication = check_duplication(names, largest)
    lines = [
        "FILES: %d" % len(files),
        "COMPLEXITY: " + complexity.verdict,
        *complexity.details,
        "DUPLICATION: " + duplication.verdict,
        *duplication.details,
        "LIMITS: CCN %d, duplication %g%%, min block %d lines / %d tokens"
        % (CCN_LIMIT, DUP_LIMIT, MIN_LINES, MIN_TOKENS),
    ]
    reasons = [c.reason for c in (complexity, duplication) if c.reason]
    installs = [c.install for c in (complexity, duplication) if c.install]
    verdicts = {complexity.verdict, duplication.verdict}
    if "ERROR" in verdicts:
        status, code = "ERROR", 3
    elif "FAIL" in verdicts:
        status, code = "FAIL", 1
    elif "NOT_ANALYZED" in verdicts:
        status, code = "PARTIAL", 0
    else:
        status, code = "OK", 0
    return emit(status, lines, reasons, installs, code)


if __name__ == "__main__":
    sys.exit(main())
