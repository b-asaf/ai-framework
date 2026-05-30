---
name: capacitor-bridge
description: Capacitor plugin architecture, web/Android parity rules, and build commands. Loaded by architect, frontend, and code-reviewer when the project uses Capacitor.
---

# Capacitor Bridge

## Stack overview
React (web) → Capacitor JS interface → Native Kotlin/Java plugin → Android APIs.
The web path uses web fallbacks — it never touches native code.

## Project structure
```
[XXX]-fe/
├── src/plugins/          # JS plugin interfaces + web fallbacks
├── android/.../java/     # Kotlin/Java native implementations
└── capacitor.config.ts
```

## Every plugin has three parts
1. **JS interface** (`src/plugins/[Name].ts`) — `registerPlugin()` + TypeScript types
2. **Web fallback** (`src/plugins/[Name]Web.ts`) — must always exist, even if it throws a user-facing error
3. **Native implementation** (`android/.../[Name].kt`) — only when React physically cannot do it

For code examples of all three parts: read `references/code-examples.md`

## Web/Android parity rules
- Every feature works in both browser and APK
- Every native plugin method has a web fallback
- APK-only features must be documented in `docs/architecture.md`
- Silent failure in browser is never acceptable

## Before writing native code
Check community plugins first: `@capacitor/*` and `@capacitor-community/*` packages.
Load `platform-guard` skill — it enforces the React-first decision checklist.

## Build commands
Run `npm run build && npx cap sync android` before testing on device.
For all build command details: read `references/code-examples.md`

## Code-reviewer checklist
- [ ] Web fallback exists for every native plugin method
- [ ] Plugin JS interface is typed — no `any`
- [ ] Native plugin registered in `MainActivity`
- [ ] `PluginCall.resolve()` and `PluginCall.reject()` both handled
- [ ] APK-only features documented in `docs/architecture.md`
- [ ] `npm run build && npx cap sync android` included in PR instructions