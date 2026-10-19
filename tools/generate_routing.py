#!/usr/bin/env python3
"""Render execution/profiles/default.json into execution/routing.json (step 1b.2, DEC-019).

    python tools/generate_routing.py           write execution/routing.json
    python tools/generate_routing.py --check   fail when the file is out of date
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.policy import PolicyError, load_policy  # noqa: E402
from lib.routing import ProfileError, load_profile, render_routing, routing_text  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare instead of writing")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent), help="repository root")
    args = parser.parse_args(argv)
    root = Path(args.repo)
    try:
        profile = load_profile(root / "execution" / "profiles" / "default.json")
        policy = load_policy(root / "execution" / "policy.json")
        text = routing_text(render_routing(profile, policy))
    except (ProfileError, PolicyError) as error:
        print(f"ERROR: {error}")
        return 1
    target = root / "execution" / "routing.json"
    if args.check:
        current = target.read_bytes().decode("utf-8") if target.is_file() else None
        if current != text:
            print("execution/routing.json is out of date; run: python tools/generate_routing.py")
            return 1
        print("execution/routing.json is up to date")
        return 0
    target.write_bytes(text.encode("utf-8"))  # bytes: no CRLF translation on Windows
    print(f"wrote {target.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
