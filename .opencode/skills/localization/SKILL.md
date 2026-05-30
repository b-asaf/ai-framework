---
name: localization
description: i18n detection, setup, string management, and RTL/LTR layout support for web and Android APK (Capacitor). Loaded by architect, frontend, ui, and code-reviewer when a task involves UI text, language support, or directional layout.
---

# Localization

## Default language
English (`en`) is always the default and fallback. Every string must exist in English before any other language is added.

## Step 1 — Detect existing setup
Scan for: `i18next`/`react-i18next`/`react-intl`/`lingui`/`next-intl` in `package.json`, or `i18n/`/`locales/`/`translations/` directory in `src/`. Also check `android/app/src/main/res/values*/strings.xml`.

Record findings in `project-overview` under `## Localization`.

## Step 2 — No library found?
Present the recommendation and wait for approval (subject to `third-party-policy`):
```
⚠️ No i18n library detected.
Recommended: react-i18next
Reason: widely adopted, JSON files, built-in RTL, works with Capacitor
Do you approve?
```
For setup code and file structure: read `references/setup-and-examples.md`

## Step 3 — RTL/LTR rules (always apply)
- Set `dir` on `<html>` when language changes
- Use CSS logical properties — `margin-inline-start` not `margin-left`
- Use `text-align: start` not `text-align: left`
- Mirror directional icons in RTL
- For Tailwind: use `ms-*`, `me-*`, `ps-*`, `pe-*` — not `ml-*`, `mr-*`

For code examples and the full logical properties table: read `references/setup-and-examples.md`

## Step 4 — Adding a new language
1. Create `src/i18n/locales/[lang]/common.json` (copy from `en/`)
2. Add to `supportedLngs` in init config
3. Add `android/app/src/main/res/values-[lang]/strings.xml`
4. Check RTL: `i18next.dir('[lang]')` returns `'rtl'` automatically for known RTL languages

## Code-reviewer checklist
- [ ] No hardcoded strings in JSX, `aria-label`, `placeholder`, `title`, `alt`
- [ ] No `margin-left/right`, `padding-left/right`, `text-align: left/right`, `left:/right:` positioning
- [ ] Directional icons mirror in RTL
- [ ] `dir` set on `<html>` when language changes
- [ ] New strings in `en/` locale (required) and all active locales
- [ ] Android `strings.xml` updated if string appears in native UI