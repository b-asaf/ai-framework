"""Report checks per role (Phase 2, plan steps 2.1 and 2.2, section 5.3; the qa role is step 3B.1).

The artifact level of success asks one question: is there a valid report? A
reply such as "I couldn't complete the review" can stop normally and still
fail here. The shape of the report is the contract in
execution/schemas/review-report.schema.json, checked by contract.py. This
module adds the rules a schema cannot express and renders the task-message
text from the schema file, so the shape is written down once. Nothing here
knows about a runtime (plan section 5.7). Everything is a pure function except
task_message, which reads the schema file.
"""

import json
import re
from dataclasses import dataclass

from . import contract

FENCE = re.compile(r"```(?:json)?[ \t]*\n(.*?)\n```", re.S)

RULES = (
    "A REQUEST CHANGES verdict needs at least one BLOCKING finding.",
    "APPROVED and APPROVED WITH ADVISORY NOTES must have no BLOCKING finding.",
    "A finding with a line must also name its file.",
)


@dataclass(frozen=True)
class ReportCheck:
    report: dict | None
    problems: tuple

    @property
    def status(self):
        """The artifact level of the run status: success or failure."""
        return "failure" if self.problems else "success"


def _check_rules(report):
    findings = report["findings"]
    has_blocking = any(finding["severity"] == "BLOCKING" for finding in findings)
    problems = []
    if report["verdict"] == "REQUEST CHANGES" and not has_blocking:
        problems.append("verdict REQUEST CHANGES needs at least one BLOCKING finding")
    if report["verdict"] != "REQUEST CHANGES" and has_blocking:
        problems.append(f"verdict {report['verdict']} cannot have a BLOCKING finding")
    for index, finding in enumerate(findings):
        if "line" in finding and "file" not in finding:
            problems.append(f"$.findings[{index}]: a line needs a file")
    return problems


REVIEWER_INTRO = (
        "Your whole reply must be one JSON object and nothing else: no text before it, no text after it, "
        "no heading and no analysis section. An automated tool parses your whole reply as JSON, so any other text makes the review unusable. "
        "Do the review as you normally would, put your analysis in the summary and in the finding messages, "
        "and reply with only the JSON. The line in a finding is the line number in the changed file after the change, as in the +start,count part of the hunk header, not a position in the patch file. It must match this schema.\n\n"
)


QA_RULES = (
    "TESTS_WRITTEN needs at least one entry in tests_written; the other outcomes must list none.",
    "NEEDS_DEVELOPER needs at least one gap that says what the developer must decide.",
    "A test file may be listed only once.",
)
QA_INTRO = (
    "Your whole reply must be one JSON object and nothing else: no text before it, no text after it, "
    "no heading and no analysis section. An automated tool parses your whole reply as JSON, "
    "so any other text makes the report unusable. "
    "Write the missing tests as you normally would, then reply with only the JSON. "
    "List only the test files you created, with paths relative to the project root, and the number of tests in each. "
    "Do not report pass or fail counts or coverage: the tool runs the test command itself and measures the result. "
    "Do not modify production files; if the tests expose a defect in production code, report it under production_issues. "
    "If you cannot write tests without a decision from the developer, use the outcome NEEDS_DEVELOPER "
    "and say in gaps what is missing. It must match this schema.\n\n"
)


def _qa_outcome_problems(outcome, written, gaps):
    if outcome == "TESTS_WRITTEN":
        return [] if written else ["outcome TESTS_WRITTEN needs at least one entry in tests_written"]
    problems = [f"outcome {outcome} cannot list tests_written"] if written else []
    if outcome == "NEEDS_DEVELOPER" and not gaps:
        problems.append("outcome NEEDS_DEVELOPER needs at least one gap that says what is missing")
    return problems


def _check_qa_rules(report):
    files = [item["file"] for item in report["tests_written"]]
    duplicates = sorted({name for name in files if files.count(name) > 1})
    problems = _qa_outcome_problems(report["outcome"], report["tests_written"], report["gaps"])
    if duplicates:
        problems.append("tests_written lists a file twice: " + ", ".join(duplicates))
    return problems


@dataclass(frozen=True)
class RoleReport:
    """What a role's reply must be: the contract file, the task-message intro and rules, and the rule check."""

    schema: str
    intro: str
    rules: tuple
    check: object


DEFAULT_ROLE = "code-reviewer"
ROLE_REPORTS = {
    "code-reviewer": RoleReport("review-report", REVIEWER_INTRO, RULES, _check_rules),
    "qa": RoleReport("qa-report", QA_INTRO, QA_RULES, _check_qa_rules),
}


def _spec(role):
    spec = ROLE_REPORTS.get(role)
    if spec is None:
        raise contract.ContractError(
            f"no report contract for role {role!r}; known roles: {', '.join(sorted(ROLE_REPORTS))}"
        )
    return spec


def check_report(data, role=DEFAULT_ROLE):
    """Return one message per problem; an empty list means a valid report.

    Schema problems come first and stop the rules, because the rules read
    fields the schema has not vouched for yet. A missing schema raises
    ContractError.
    """
    spec = _spec(role)
    return contract.validate_contract(data, spec.schema) or spec.check(data)


def _json_text(text):
    stripped = text.strip()
    match = FENCE.fullmatch(stripped)
    return match.group(1) if match else stripped


def parse_report(text, role=DEFAULT_ROLE):
    """Read a reviewer reply. The whole reply must be one JSON object, optionally in one code fence."""
    if not isinstance(text, str):
        return ReportCheck(None, ("the reply is not text",))
    try:
        data = json.loads(_json_text(text))
    except ValueError as error:
        return ReportCheck(None, (f"the reply is not one JSON object: {error}",))
    problems = tuple(check_report(data, role))
    return ReportCheck(None if problems else data, problems)


def task_message(role=DEFAULT_ROLE):
    """The text that tells a role what to reply: the schema file itself plus the rules."""
    spec = _spec(role)
    schema = json.dumps(contract.load_schema(spec.schema), indent=2)
    rules = "\n".join(f"- {rule}" for rule in spec.rules)
    return f"{spec.intro}{schema}\n\nRules the schema cannot express:\n{rules}\n"
