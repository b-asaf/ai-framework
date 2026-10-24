"""Benchmark cases for the reviewer (Phase 2, plan step 2.3).

A case is a small project plus one diff. A bug case plants one defect that a careful
reviewer should block; a clean case has none and should be approved. The diff is built
from the before and after text of each changed file, so the line a finding should cite
is computed, never typed. The detection pattern of a bug case is deliberately narrow: it
must name what is wrong, not only the area (the word leap alone is not enough).

The cases cover a plain control (off-by-one), a subtle rule change, a defect behind a
passing test, a defect that needs a second file to see, and a security defect, plus two
clean diffs for false positives. Nothing here knows about a model or a runtime.
"""

import difflib
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROLE = "code-reviewer"
STACK_TEXT = (
    "# Stack\n\n"
    "- Purpose: benchmark case, no real application.\n"
    "- Language: TypeScript and Java.\n"
    "- Tests: node --test\n"
    "- Base branch: main\n"
)


@dataclass(frozen=True)
class Bug:
    file: str
    marker: str
    pattern: str
    example: str


@dataclass(frozen=True)
class Case:
    id: str
    kind: str
    summary: str
    changes: dict
    context: dict
    bug: Bug | None = None


TOTAL_BEFORE = """export function sumPrices(items: { price: number }[]): number {
  let total = 0;
  for (let i = 0; i < items.length; i++) {
    total += items[i].price;
  }
  return total;
}
"""
TOTAL_AFTER = """export function sumPrices(items: { price: number }[]): number {
  let total = 0;
  for (let i = 0; i <= items.length; i++) {
    total += items[i].price;
  }
  return total;
}
"""

CALENDAR_BEFORE = """export function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

export function daysInYear(year: number): number {
  return isLeapYear(year) ? 366 : 365;
}
"""
CALENDAR_AFTER = """export function isLeapYear(year: number): boolean {
  return year % 4 === 0 && year % 100 !== 0;
}

export function daysInYear(year: number): number {
  return isLeapYear(year) ? 366 : 365;
}
"""

RETRY_BEFORE = """export async function retry<T>(fn: () => Promise<T>, attempts: number): Promise<T> {
  let lastError: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}
"""
RETRY_AFTER = """export async function retry<T>(fn: () => Promise<T>, attempts: number): Promise<T> {
  let lastError: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
    }
  }
  console.warn("retry gave up", lastError);
  return undefined as T;
}
"""
RETRY_TEST = """import { test } from "node:test";
import assert from "node:assert/strict";
import { retry } from "./retry";

test("returns the value when the first call succeeds", async () => {
  assert.equal(await retry(async () => 42, 3), 42);
});
"""

USER_REPOSITORY = """package app;

import java.util.HashMap;
import java.util.Map;

public class UserRepository {
    private final Map<String, User> byEmail = new HashMap<>();

    public void save(User user) {
        byEmail.put(user.getEmail(), user);
    }

    /** Returns the user, or null when no user has this email. */
    public User findByEmail(String email) {
        return byEmail.get(email);
    }
}
"""
USER = """package app;

public class User {
    private final String email;
    private final String name;

    public User(String email, String name) {
        this.email = email;
        this.name = name;
    }

    public String getEmail() { return email; }

    public String getName() { return name; }
}
"""
GREETING_BEFORE = """package app;

public class GreetingService {
    public String greet() {
        return "Hello";
    }
}
"""
GREETING_AFTER = """package app;

public class GreetingService {
    private final UserRepository users;

    public GreetingService(UserRepository users) {
        this.users = users;
    }

    public String greet(String email) {
        return "Hello, " + users.findByEmail(email).getName();
    }
}
"""

DB = """export interface Db {
  query(sql: string, params?: unknown[]): Promise<{ rows: unknown[] }>;
}
"""
STORE_BEFORE = """import { Db } from "./db";

export async function findUser(db: Db, id: number) {
  return db.query("SELECT id, name FROM users WHERE id = $1", [id]);
}
"""
STORE_AFTER = """import { Db } from "./db";

export async function findUser(db: Db, id: number) {
  return db.query("SELECT id, name FROM users WHERE id = $1", [id]);
}

export async function findUserByName(db: Db, name: string) {
  return db.query("SELECT id, name FROM users WHERE name = '" + name + "'");
}
"""

FORMAT_BEFORE = """export function fmt(amount: number): string {
  return `$${amount.toFixed(2)}`;
}
"""
FORMAT_AFTER = """export function formatPrice(amount: number): string {
  return `$${amount.toFixed(2)}`;
}
"""
RECEIPT_BEFORE = """import { fmt } from "./format";

export function receiptLine(name: string, amount: number): string {
  return `${name}: ${fmt(amount)}`;
}
"""
RECEIPT_AFTER = """import { formatPrice } from "./format";

export function receiptLine(name: string, amount: number): string {
  return `${name}: ${formatPrice(amount)}`;
}
"""
RECEIPT_TEST = """import { test } from "node:test";
import assert from "node:assert/strict";
import { receiptLine } from "./receipt";

test("formats a receipt line", () => {
  assert.equal(receiptLine("Tea", 3), "Tea: $3.00");
});
"""

CLAMP_BEFORE = """export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
"""
CLAMP_AFTER = """export function clamp(value: number, min: number, max: number): number {
  if (min > max) {
    throw new RangeError("min must not be greater than max");
  }
  return Math.min(Math.max(value, min), max);
}
"""
CLAMP_TEST = """import { test } from "node:test";
import assert from "node:assert/strict";
import { clamp } from "./clamp";

test("keeps a value inside the range", () => {
  assert.equal(clamp(5, 0, 10), 5);
  assert.equal(clamp(-1, 0, 10), 0);
  assert.equal(clamp(11, 0, 10), 10);
});

test("rejects an inverted range", () => {
  assert.throws(() => clamp(1, 5, 0), RangeError);
});
"""

CASES = (
    Case(
        id="off-by-one-loop",
        kind="bug",
        summary="a loop bound changed from < to <=, so the last pass reads past the array",
        changes={"src/total.ts": (TOTAL_BEFORE, TOTAL_AFTER)},
        context={},
        bug=Bug(
            file="src/total.ts",
            marker="i <= items.length",
            pattern=r"off[- ]by[- ]one|out[- ]of[- ]bounds|items\[items\.length\]|undefined|<=",
            example="Loop bound is off-by-one: i <= items.length reads items[items.length], which is undefined.",
        ),
    ),
    Case(
        id="leap-year-century",
        kind="bug",
        summary="a simplified leap year rule drops the 400 year exception",
        changes={"src/calendar.ts": (CALENDAR_BEFORE, CALENDAR_AFTER)},
        context={},
        bug=Bug(
            file="src/calendar.ts",
            marker="year % 100 !== 0;",
            pattern=r"\b400\b|century|centuries|\b2000\b",
            example="Century years divisible by 400, such as 2000, are no longer treated as leap years.",
        ),
    ),
    Case(
        id="retry-swallows-error",
        kind="bug",
        summary="after the last failed attempt retry returns undefined instead of throwing; the new test only covers success",
        changes={"src/retry.ts": (RETRY_BEFORE, RETRY_AFTER), "src/retry.test.ts": (None, RETRY_TEST)},
        context={},
        bug=Bug(
            file="src/retry.ts",
            marker="return undefined as T;",
            pattern=r"undefined|swallow|silent|never throws|does not throw|no longer throws|rethrow|exhaust",
            example="When every attempt fails the function returns undefined and swallows the last error instead of throwing it.",
        ),
    ),
    Case(
        id="null-from-repository",
        kind="bug",
        summary="a service dereferences the result of a repository method that returns null when nothing is found",
        changes={"src/main/java/app/GreetingService.java": (GREETING_BEFORE, GREETING_AFTER)},
        context={"src/main/java/app/UserRepository.java": USER_REPOSITORY, "src/main/java/app/User.java": USER},
        bug=Bug(
            file="src/main/java/app/GreetingService.java",
            marker="users.findByEmail(email).getName()",
            pattern=r"null|NullPointer|not found|no user|absent|unknown (user|email)",
            example="findByEmail returns null for an unknown email, so getName() throws a NullPointerException.",
        ),
    ),
    Case(
        id="sql-string-concat",
        kind="bug",
        summary="a new query builds SQL by concatenating a user supplied name",
        changes={"src/userStore.ts": (STORE_BEFORE, STORE_AFTER)},
        context={"src/db.ts": DB},
        bug=Bug(
            file="src/userStore.ts",
            marker="WHERE name = '",
            pattern=r"injection|parameteri[sz]ed|prepared statement|bind (variable|parameter)|concatenat|unsanitized|escap",
            example="The name is concatenated into the SQL string, which allows SQL injection; use a parameterized query.",
        ),
    ),
    Case(
        id="clean-rename-helper",
        kind="clean",
        summary="a helper is renamed and its only caller is updated",
        changes={"src/format.ts": (FORMAT_BEFORE, FORMAT_AFTER), "src/receipt.ts": (RECEIPT_BEFORE, RECEIPT_AFTER)},
        context={"src/receipt.test.ts": RECEIPT_TEST},
    ),
    Case(
        id="clean-guard-with-test",
        kind="clean",
        summary="an input check is added to a helper, with tests for both paths",
        changes={"src/clamp.ts": (CLAMP_BEFORE, CLAMP_AFTER), "src/clamp.test.ts": (None, CLAMP_TEST)},
        context={},
    ),
)
CASE_IDS = tuple(case.id for case in CASES)


def get_case(case_id):
    for case in CASES:
        if case.id == case_id:
            return case
    raise ValueError(f"unknown case '{case_id}'; known cases: {', '.join(CASE_IDS)}")


def make_diff(changes):
    """A git style diff of every change. A file whose before text is None is new."""
    parts = []
    for path in sorted(changes):
        before, after = changes[path]
        old = [] if before is None else before.splitlines(keepends=True)
        new = after.splitlines(keepends=True)
        parts.append(f"diff --git a/{path} b/{path}\n")
        if before is None:
            parts.append("new file mode 100644\n")
        fromfile = "/dev/null" if before is None else f"a/{path}"
        parts += difflib.unified_diff(old, new, fromfile=fromfile, tofile=f"b/{path}")
    return "".join(parts)


def file_line(text, marker):
    """1-based number of the first line of the text that contains the marker."""
    for number, line in enumerate(text.splitlines(), start=1):
        if marker in line:
            return number
    raise ValueError(f"no line contains {marker!r}")


def patch_line(diff, marker):
    """1-based number, in the diff text, of the first added line that contains the marker."""
    for number, line in enumerate(diff.splitlines(), start=1):
        if line.startswith("+") and not line.startswith("+++") and marker in line:
            return number
    raise ValueError(f"no added line contains {marker!r}")


def bug_lines(case):
    """(line in the changed file, line in the patch file) of the planted bug."""
    after = case.changes[case.bug.file][1]
    return file_line(after, case.bug.marker), patch_line(make_diff(case.changes), case.bug.marker)


def target_files(case):
    """Every file of the project after the change, with the files the first-run gate needs."""
    files = dict(case.context)
    files.update({path: after for path, (_, after) in case.changes.items()})
    files["docs/project-overview/stack.md"] = STACK_TEXT
    files[".ai-framework.json"] = "{}\n"
    return files


def build_target(case, directory):
    """Write the project after the change into directory, as a git repository without commits."""
    root = Path(directory)
    for path, text in target_files(case).items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    try:
        subprocess.run(["git", "init", "-q"], cwd=str(root), capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return root


def write_diff(case, path):
    path = Path(path)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(make_diff(case.changes))
    return path
