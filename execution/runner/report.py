"""Reviewer report checks (Phase 2, plan steps 2.1 and 2.2, section 5.3).

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


def check_report(data):
    """Return one message per problem; an empty list means a valid report.

    Schema problems come first and stop the rules, because the rules read
    fields the schema has not vouched for yet. A missing schema raises
    ContractError.
    """
    return contract.validate_contract(data, "review-report") or _check_rules(data)


def _json_text(text):
    stripped = text.strip()
    match = FENCE.fullmatch(stripped)
    return match.group(1) if match else stripped


def parse_report(text):
    """Read a reviewer reply. The whole reply must be one JSON object, optionally in one code fence."""
    if not isinstance(text, str):
        return ReportCheck(None, ("the reply is not text",))
    try:
        data = json.loads(_json_text(text))
    except ValueError as error:
        return ReportCheck(None, (f"the reply is not one JSON object: {error}",))
    problems = tuple(check_report(data))
    return ReportCheck(None if problems else data, problems)


def task_message():
    """The text that tells a reviewer what to reply: the schema file itself plus the rules."""
    schema = json.dumps(contract.load_schema("review-report"), indent=2)
    rules = "\n".join(f"- {rule}" for rule in RULES)
    return (
        "Reply with one JSON object and nothing else: no text before or after it. "
        "It must match this schema.\n\n"
        f"{schema}\n\nRules the schema cannot express:\n{rules}\n"
    )
