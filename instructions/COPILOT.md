# COPILOT.md
> GitHub Copilot (IntelliJ / JetBrains) specific instructions.
> All rules from SHARED.md apply. This file adds Copilot-specific behaviour only.

---

## Scope

Copilot does not have the same agentic loop as Claude Code or OpenCode.
Apply the shared rules as inline-completion and chat guidance:

- Always propose a plan in chat before suggesting multi-file edits
- Never suggest a `git commit`, `git push`, or destructive git command in
  any completion or chat response
- When suggesting a dependency change, flag it explicitly and wait for
  the developer to confirm before generating the implementation that uses it

## Completion behaviour

- Match the existing code style exactly — do not auto-apply formatting changes
- Suggest only what the current cursor context requires (surgical changes rule)
- If the completion would touch more than the immediate function/method,
  surface it as a chat suggestion instead so the developer can review scope

## Chat behaviour

- Treat every chat session as a single-task session (one concern per conversation)
- If the developer's request is ambiguous, ask one clarifying question before
  generating any code
- After generating code, summarise what was changed and flag anything that
  should be reviewed or tested
