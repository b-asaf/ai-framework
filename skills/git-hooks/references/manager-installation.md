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
```bash
bash scripts/hooks/install-hooks.sh
```
Hook scripts are in `scripts/git-hooks/` in this skill folder.

> ⚠️ Plain `.git/hooks/` scripts are not committed to the repo.
> Every developer must run the installer after cloning.
> Add to README: `bash scripts/hooks/install-hooks.sh`

## Verification
```bash
ls -la .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push
git checkout -b test/hook-check
git commit --allow-empty -m "bad message"    # should fail
git commit --allow-empty -m "chore: test"    # should pass
git branch -D test/hook-check
```