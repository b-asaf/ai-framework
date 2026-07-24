#!/bin/sh
# build-verify.sh
# ----------------
# Deterministic pass/fail gate for the self-correction loop (see
# skills/build-verify/SKILL.md). Runs lint -> format -> test in sequence
# using the exact commands recorded in project-overview/sub/stack.md for
# this repo, and reports pass/fail from the actual exit code — never an
# LLM's opinion of whether its own output looks right.
#
# Stops at the first failing stage (no point formatting code that doesn't
# lint, no point testing code that isn't formatted).
#
# Output is trimmed by default (last N lines of a failing stage) so a
# retry loop doesn't re-inject a full, noisy test-suite dump into the
# agent's context on every attempt. Full output is always saved to a log
# file regardless — pass --full (or read the printed log path) to get
# everything, which is what the 3rd-attempt escalation report should use.
#
# Usage:
#   hooks/build-verify.sh --lint "<cmd>" --format "<cmd>" --test "<cmd>" [--full] [--trim-lines N]
#
# Any stage can be omitted if the project doesn't have one (e.g. no
# formatter configured) — omitted stages are skipped, not failed.
#
# Example (populated from this repo's own project-overview/sub/stack.md):
#   hooks/build-verify.sh \
#     --lint   "npm run lint" \
#     --format "npm run format:check" \
#     --test   "npm test"
#
# Example, escalation report after 3 failures (full output, not trimmed):
#   hooks/build-verify.sh --lint "npm run lint" --full

set -u

LINT_CMD=""
FORMAT_CMD=""
TEST_CMD=""
FULL_OUTPUT=0
TRIM_LINES="${BUILD_VERIFY_TRIM_LINES:-40}"

while [ $# -gt 0 ]; do
  case "$1" in
    --lint)       LINT_CMD="$2";   shift 2 ;;
    --format)     FORMAT_CMD="$2"; shift 2 ;;
    --test)       TEST_CMD="$2";   shift 2 ;;
    --full)       FULL_OUTPUT=1;   shift ;;
    --trim-lines) TRIM_LINES="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
LOG_DIR="$REPO_ROOT/.git/build-verify-logs"
mkdir -p "$LOG_DIR" 2>/dev/null || { LOG_DIR="${TMPDIR:-/tmp}/build-verify-logs"; mkdir -p "$LOG_DIR" 2>/dev/null; }

run_stage() {
  stage_name="$1"
  stage_cmd="$2"
  log_file="$LOG_DIR/$(echo "$stage_name" | tr '[:upper:]' '[:lower:]').log"

  if [ -z "$stage_cmd" ]; then
    echo "== $stage_name: SKIPPED (no command configured) =="
    return 0
  fi

  echo "== $stage_name: running \`$stage_cmd\` =="
  # shellcheck disable=SC2086
  eval "$stage_cmd" >"$log_file" 2>&1
  code=$?

  if [ "$code" -eq 0 ]; then
    echo "== $stage_name: PASS =="
    return 0
  fi

  echo "== $stage_name: FAIL (exit $code) =="
  if [ "$FULL_OUTPUT" -eq 1 ]; then
    cat "$log_file"
  else
    total_lines=$(wc -l < "$log_file" | tr -d ' ')
    if [ "$total_lines" -gt "$TRIM_LINES" ]; then
      echo "-- showing last $TRIM_LINES of $total_lines lines (full log: $log_file) --"
      tail -n "$TRIM_LINES" "$log_file"
      echo "-- run with --full, or 'cat $log_file', for everything --"
    else
      cat "$log_file"
    fi
  fi
  return "$code"
}

run_stage "LINT"   "$LINT_CMD"   || exit 1
run_stage "FORMAT" "$FORMAT_CMD" || exit 2
run_stage "TEST"   "$TEST_CMD"   || exit 3

echo "== build-verify: ALL STAGES PASS =="
exit 0
