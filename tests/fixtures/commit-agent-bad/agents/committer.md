---
description: Fixture agent that may commit but is missing most denies
mode: primary
model: github-copilot/gpt-5.6-terra
permission:
  bash:
    "*": ask
    "git commit *": allow
    "git branch *": allow
    "git push*": deny
  edit: deny
  write: deny
  task: deny
---
Fixture body.
