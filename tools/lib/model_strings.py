"""Find concrete model ids in framework-owned files (step 1.8, DEC-016).

roles/, verification/ and execution/schemas/ must stay model-agnostic: which
model runs a role is decided in execution/profiles and checked against
execution/policy.json. The match is heuristic. It looks for id-shaped strings
(provider/model, claude-sonnet-5, gpt-5.3-codex, gemini-2.5-pro, o3-mini) and
ignores prose such as "GPT models may be used". Adjust PROVIDERS or MODEL_ID if
a new provider needs covering.
"""

import re
from pathlib import Path

CHECKED_FOLDERS = ("roles", "verification", "execution/schemas")
CHECKED_SUFFIXES = {".json", ".md", ".py", ".yaml", ".yml", ".txt", ".sh", ".toml"}
PROVIDERS = (
    "anthropic", "github-copilot", "openai", "google",
    "openrouter", "bedrock", "vertex", "mistral", "xai",
)

MODEL_ID = re.compile(
    r"(?<![\w.\-])(?:" + "|".join(PROVIDERS) + r")/[A-Za-z0-9][\w.\-]*"  # provider/model
    r"|\b(?:claude|gpt|gemini)-(?=[\w.\-]*\d)[\w.\-]+"  # claude-sonnet-5, gpt-5.3-codex
    r"|\b(?:gpt|gemini)\d[\w.\-]*"  # gpt4o, gemini2.5
    r"|\bcodex-[a-z0-9][\w.\-]*"  # codex-mini
    r"|\bo[134](?:-(?:mini|preview|pro)[\w.\-]*)?\b",  # o1, o3-mini
    re.IGNORECASE,
)


def find_model_ids(text):
    """Return (line_number, matched_text) for each concrete model id in text."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in MODEL_ID.finditer(line):
            found.append((number, match.group(0)))
    return found


def scan_folders(root, folders=CHECKED_FOLDERS):
    """Return (relative_path, line, match) for every model id under the checked folders.

    A folder that does not exist yet is skipped; the folders arrive in later phases.
    """
    results = []
    for folder in folders:
        base = Path(root) / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in CHECKED_SUFFIXES:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                for line, match in find_model_ids(text):
                    results.append((path.relative_to(root).as_posix(), line, match))
    return results
