# Stack

- Purpose: ai-framework, the agents, skills, commands, hooks and Python tooling that the OpenCode global config links to.
- Language: Python 3.14 using only the standard library, shell hooks, Markdown agent and skill files, JSON.
- Runtime: OpenCode 1.19.3 on Windows with Git Bash.
- Tests: python -m unittest
- Validator: python tools/validate_framework.py
- Complexity: python -m lizard -C 10 -w <files> for new code
- Base branch: main
- Conventions: pure functions with file reads at the edges, fail closed, one source of truth, LF line endings.
- Warning: the main folder is linked into the global OpenCode config, so work in a git worktree and never edit the main folder directly.
