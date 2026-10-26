"""Resolve a role to the model it is requested to run on (Phase 2, plan step 2.1).

The profile maps a role to a model and the policy says whether that model may
run. This module joins the two and refuses anything the policy does not allow.
It reuses check_experimental from tools/lib/policy.py instead of repeating the
rule. Everything fails closed (DEC-015): a missing or malformed profile or
policy, a role without a profile entry, an unknown model and an experimental
model without an evaluation all raise ResolveError. The independence rule needs
the producer's model as well, so it is not checked here.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from lib.policy import PolicyError, check_experimental, load_policy  # noqa: E402
from lib.routing import ProfileError, load_profile, profile_models  # noqa: E402

PROFILE_NAME = re.compile(r"[A-Za-z0-9_-]+")


class ResolveError(Exception):
    """The role cannot be resolved to a model the policy allows."""


@dataclass(frozen=True)
class Resolved:
    role: str
    profile: str
    model: str
    family: str
    status: str
    effort: str | None = None


def resolve_role(role, profile, policy, repo_root, profile_name="default"):
    """Pure core: return Resolved for the role, or raise ResolveError."""
    models = profile_models(profile)
    if role not in models:
        raise ResolveError(
            f"role '{role}' has no entry in profile '{profile_name}'; it would run on its caller's model (F34)"
        )
    model = models[role]
    problems = check_experimental({role: model}, policy, repo_root)
    if problems:
        raise ResolveError(f"role '{role}': " + "; ".join(message for _, message in problems))
    entry = policy["models"][model]
    effort = profile["agents"][role].get("effort")
    return Resolved(
        role=role, profile=profile_name, model=model, family=entry["family"].lower(), status=entry["status"], effort=effort
    )


def resolve(role, repo_root, profile_name="default"):
    """Load execution/profiles/<profile_name>.json and execution/policy.json under repo_root, then resolve."""
    if not PROFILE_NAME.fullmatch(profile_name):
        raise ResolveError(f"profile name {profile_name!r} may only use letters, digits, '-' and '_'")
    root = Path(repo_root)
    try:
        profile = load_profile(root / "execution" / "profiles" / f"{profile_name}.json")
        policy = load_policy(root / "execution" / "policy.json")
    except (ProfileError, PolicyError) as error:
        raise ResolveError(str(error)) from error
    return resolve_role(role, profile, policy, root, profile_name)
