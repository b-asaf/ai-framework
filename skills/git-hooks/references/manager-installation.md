# Hook Manager Installation Guides

## Husky
```bash
npx husky install
npx husky add .husky/pre-commit 'bash .husky/scripts/check-branch.sh'
npx husky add .husky/commit-msg 'bash .husky/scripts/check-commit-msg.sh "$1"'
npx husky add .husky/pre-push 'bash .husky/scripts/check-push.sh'
```
Add to `package.json`: `"prepare": "husky install"`

## Lefthook
Add to `lefthook.yml`:
```yaml
pre-commit:
  commands:
    check-branch:
      run: bash .lefthook/scripts/pre-commit
commit-msg:
  commands:
    check-message:
      run: bash .lefthook/scripts/commit-msg {1}
pre-push:
  commands:
    check-push:
      run: bash .lefthook/scripts/pre-push
```
Run: `lefthook install`

## Plain scripts (fallback)
If ai-framework's `setup.py` has been run on this machine, hooks are wired
automatically the moment a repo is created — git's `init.templateDir`
copies them in on `git init`/`git clone`. Nothing to do; skip straight to
Verification below.

If they're missing (repo predates `setup.py`, or it hasn't been run on
this machine yet), re-apply manually from the ai-framework checkout:
```bash
bash <path-to-ai-framework>/hooks/install-hooks.sh
```
Hook scripts live in `hooks/` at the ai-framework repo root — this skill
folder doesn't carry its own copy.

> ⚠️ Plain `.git/hooks/` scripts are not committed to the repo, and
> `init.templateDir` only applies at `git init`/`git clone` time.
> Add to README: run `python setup.py` from the ai-framework checkout
> (once per machine), or `bash <ai-framework>/hooks/install-hooks.sh`
> as a one-off fallback for a repo that already exists.

## Verification
```bash
ls -la .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push
git checkout -b test/hook-check
git commit --allow-empty -m "bad message"    # should fail
git commit --allow-empty -m "chore: test"    # should pass
git branch -D test/hook-check
```