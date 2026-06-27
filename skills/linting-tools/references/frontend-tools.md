# Frontend Linting Tools

## Biome
**Detection:** `biome.json` or `@biomejs/biome` in `devDependencies`
```bash
npx biome check .          # lint + format check
npx biome check --fix .    # auto-fix safe issues
```
Replaces both ESLint and Prettier. If Biome is present, do not run ESLint or Prettier.

## ESLint
**Detection:** `.eslintrc.*`, `eslint.config.*`, or `eslint` in `devDependencies`
```bash
npx eslint .               # report violations
npx eslint . --fix         # auto-fix safe issues
```
Honour `.eslintignore` or `ignorePatterns` in config.

## Prettier
**Detection:** `.prettierrc.*`, `prettier.config.*`, or `prettier` in `devDependencies`
```bash
npx prettier --check .     # report formatting violations
npx prettier --write .     # auto-fix all formatting
```
Run before ESLint — formatting first, then linting.