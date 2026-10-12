---
description: Fixture agent that may commit and carries every deny
mode: primary
model: github-copilot/gpt-5.6-terra
permission:
  bash:
    "*": ask
    "git commit *": allow
    "git branch *": allow
    "git commit*--no-verify*": deny
    "git branch -d *": deny
    "git branch -D *": deny
    "git branch --delete *": deny
    "git push*": deny
    "git merge *": deny
    "git rebase *": deny
    "git reset *": deny
    "gh pr ready*": deny
    "gh pr merge*": deny
    "gh pr create*": deny
    "glab mr merge*": deny
    "glab mr create*": deny
  edit: deny
  write: deny
  task: deny
---
Fixture body.
