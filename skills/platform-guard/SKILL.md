---
name: platform-guard
description: Decision framework for React-vs-native choices in a Capacitor project. Enforces the React-first rule. Loaded by architect before any implementation decision, and by code-reviewer to catch unjustified native code.
---

# Platform Guard

## The rule

**React first. Native only when React physically cannot do it.**

Native Kotlin/Java code is written only when there is no technically viable React or web API alternative. "Nicer on native" or "easier in Kotlin" are not valid justifications.

---

## Architect — decision checklist

Run this checklist before approving any native implementation. Every question must be answered and recorded in the HLD.

### Step 1 — Can a web API do it?

Check whether the Web Platform already provides what's needed:

| Capability | Web API |
|---|---|
| Camera | `getUserMedia()`, `<input type="file" accept="image/*" capture>` |
| Geolocation | `navigator.geolocation` |
| Notifications | Web Push API, Notification API |
| Storage | `localStorage`, `IndexedDB`, `Cache API` |
| Clipboard | `navigator.clipboard` |
| Device orientation | `DeviceOrientationEvent` |
| Vibration | `navigator.vibrate()` |
| Network status | `navigator.onLine`, Network Information API |
| Bluetooth | Web Bluetooth API (limited browser support) |
| NFC | Web NFC API (limited support) |

If a web API covers the requirement → **use it. No native code needed.**

### Step 2 — Does a Capacitor community plugin exist?

Search before writing:
- Official: `@capacitor/*` packages
- Community: `@capacitor-community/*` packages
- Reference: https://capacitorjs.com/docs/plugins

If a maintained plugin exists → **use it (subject to `third-party-policy` approval). No custom native code needed.**

### Step 3 — Is the limitation real or assumed?

Before writing native code, verify the limitation is real:

```
❓ Platform guard question:
"What specifically does React / the web API fail to do here?"

Acceptable answers:
- "The web API does not exist in the Android WebView Capacitor uses"
- "The web API exists but requires HTTPS and we deploy locally"
- "The permission model requires native integration"
- "We need background execution which WebViews cannot provide"

Not acceptable answers:
- "It's easier to do in Kotlin"
- "The web API feels slower"
- "I'm more familiar with the native approach"
```

### Step 4 — Is the web fallback defined?

Before any native code is written, define what happens when the feature runs in a browser:

| Option | When to use |
|---|---|
| Full web implementation | Web API can partially do it |
| Degraded experience | Web API does a subset of what native does |
| Clear user-facing error | Feature is physically impossible in browser |
| Feature hidden in browser | APK-only feature, hidden via platform detection |

A web fallback must always be defined — even if it's "this feature is not available in the browser" with a helpful message.

### Step 5 — Document the decision

Every justified native implementation must be recorded in two places:

**In the HLD:**
```
## Native implementation justification
Feature: [feature name]
Web API checked: [what was checked and why it doesn't work]
Community plugin checked: [what was searched and why it doesn't apply]
Limitation confirmed: [specific technical reason native is required]
Web fallback: [what happens in the browser]
```

**In `docs/architecture.md`** under a `## Platform-specific features` section:
```markdown
| Feature | React (web) | Native (Android) | Justification |
|---|---|---|---|
| Background sync | ❌ not supported | ✅ WorkManager | Web workers cannot run when app is backgrounded |
```

---

## Code-reviewer — platform guard checks

When reviewing any PR that contains Kotlin or Java:

- [ ] HLD contains a completed native implementation justification
- [ ] Web API was explicitly checked (documented in HLD)
- [ ] Community plugins were explicitly checked (documented in HLD)
- [ ] The limitation is specific and technical — not a preference
- [ ] A web fallback is implemented (even if it's a user-facing error)
- [ ] `docs/architecture.md` platform-specific features table is updated
- [ ] No native code exists for something a community plugin handles

> Any native code without a recorded justification is a **blocker**. The architect must produce the justification before the PR can proceed.

---

## Platform detection in React

When the web fallback behavior differs from native, use Capacitor's platform detection:

```typescript
import { Capacitor } from '@capacitor/core';

const isNative = Capacitor.isNativePlatform();   // true in APK, false in browser
const platform = Capacitor.getPlatform();          // 'android' | 'ios' | 'web'

// Example: show different UI per platform
if (Capacitor.isNativePlatform()) {
  // use native camera plugin
} else {
  // use file input fallback
}
```

Do not use `navigator.userAgent` sniffing for platform detection — always use `Capacitor.isNativePlatform()` or `Capacitor.getPlatform()`.

---

## Allowed native-only patterns

These are pre-approved as justified native implementations — no additional checklist required:

| Pattern | Reason |
|---|---|
| Background services (WorkManager, JobScheduler) | WebViews cannot run background tasks |
| Push notification handling (FCM integration) | Requires native Firebase SDK setup |
| Deep link / intent handling | Android intent system is native |
| App lifecycle events (onResume, onPause) | Needed for native resource management |
| Keystore / secure credential storage | Android Keystore is native-only |
| Bluetooth Low Energy (if Web Bluetooth insufficient) | Limited WebView support |
| NFC reading/writing (if Web NFC insufficient) | Limited WebView support |