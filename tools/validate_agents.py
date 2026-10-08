"""Compatibility wrapper (step 1.7): the validator now lives in validate_framework.py.

Kept so existing commands such as `python tools/validate_agents.py` keep working.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_framework import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
