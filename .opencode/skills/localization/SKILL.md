---
name: localization
description: i18n detection, setup, string management, and RTL/LTR layout support for web and Android APK (Capacitor). Loaded by architect, frontend, ui, and code-reviewer when a task involves UI text, language support, or directional layout.
---

# Localization

## Default language
English (`en`) is always the default and fallback. Every string must exist in English before any other language is added.

## Step 1 — Detect existing setup
Scan for: `i18next`/`react-i18next`/`react-intl`/`lingui`/`next-intl` in `package.json`, or `i18n/`/`locales/`/`translations/` directory in `src/`. Also check `android/app/src/main/res/values*/strings.xml`.

Record findings in `project-overview/sub/localization.md`.

## Step 2 — No library found?
Present the recommendation and wait for approval (subject to `third-party-policy`):
```
⚠️ No i18n library detected.
Recommended: react-i18next
Reason: widely adopted, JSON files, built-in RTL, works with Capacitor
Do you approve?
```
For setup code and file structure: read `references/setup-and-examples.md`

## Step 3 — Adding a new language
1. Create `src/i18n/locales/[lang]/common.json` (copy from `en/`)
2. Add to `supportedLngs` in init config
3. Add `android/app/src/main/res/values-[lang]/strings.xml`
4. Check RTL: `i18next.dir('[lang]')` returns `'rtl'` automatically for known RTL languages

---

## CSS and layout

This section applies to **every UI file** in a project with more than one language.
Load this section whenever a task touches layout, spacing, positioning, or typography.

### The core rule — logical properties, always

Never write physical directional CSS properties in a multi-language project.
Physical properties are hardwired to LTR. Logical properties let the browser flip
them automatically based on the `dir` attribute — no JavaScript, no class toggling.

**Always replace:**

| ❌ Physical (never use) | ✅ Logical (always use) |
|---|---|
| `margin-left` | `margin-inline-start` |
| `margin-right` | `margin-inline-end` |
| `padding-left` | `padding-inline-start` |
| `padding-right` | `padding-inline-end` |
| `border-left` | `border-inline-start` |
| `border-right` | `border-inline-end` |
| `left: Xpx` (positioning) | `inset-inline-start: Xpx` |
| `right: Xpx` (positioning) | `inset-inline-end: Xpx` |
| `text-align: left` | `text-align: start` |
| `text-align: right` | `text-align: end` |
| `float: left` | `float: inline-start` |
| `float: right` | `float: inline-end` |

**Tailwind equivalents:**

| ❌ Physical | ✅ Logical |
|---|---|
| `ml-*` / `mr-*` | `ms-*` / `me-*` |
| `pl-*` / `pr-*` | `ps-*` / `pe-*` |
| `left-*` / `right-*` (positioning) | `start-*` / `end-*` |
| `text-left` / `text-right` | `text-start` / `text-end` |
| `float-left` / `float-right` | `float-start` / `float-end` |
| `rounded-l-*` / `rounded-r-*` | `rounded-s-*` / `rounded-e-*` |
| `border-l-*` / `border-r-*` | `border-s-*` / `border-e-*` |

Physical properties are acceptable **only** when the layout is intentionally
direction-neutral: centering with `margin-inline: auto`, vertical spacing,
`top`/`bottom`, `width`/`height`. None of those have directional equivalents.

### Setting direction

Direction must be set at the `<html>` element — not on individual components.
Setting `dir` on a child element creates a subtree override, which breaks automatic
logical property resolution for everything outside that subtree.

```tsx
// ✅ Correct — set on <html>
document.documentElement.setAttribute('dir', i18next.dir(language));
document.documentElement.setAttribute('lang', language);

// ❌ Wrong — set on a container div
<div dir="rtl"> ... </div>  // only applies to its own subtree
```

In a Next.js / SSR context, set `dir` and `lang` in the root layout:
```tsx
// app/layout.tsx
export default function RootLayout({ children, params: { lang } }) {
  return (
    <html lang={lang} dir={getDirection(lang)}>
      {children}
    </html>
  );
}
```

### Directional icons and assets

Icons that communicate direction (arrows, chevrons, back buttons, forward progress
indicators) must mirror in RTL. Non-directional icons (close ×, plus +, checkmark ✓,
star ★) never mirror.

**CSS mirror — for inline SVG or `<img>` icons:**
```css
[dir="rtl"] .icon-directional {
  transform: scaleX(-1);
}
```

**React pattern:**
```tsx
const { i18n } = useTranslation();
const isRTL = i18n.dir() === 'rtl';

<ChevronIcon style={{ transform: isRTL ? 'scaleX(-1)' : 'none' }} />
```

**Tailwind pattern:**
```tsx
<ChevronRightIcon className="rtl:scale-x-[-1]" />
```

When providing separate RTL assets (illustrations, diagrams, branded images with text):
name them `asset-name-rtl.svg` and select at the component level based on direction.

### Typography per locale

Some scripts require adjustments beyond direction — size, line height, and font stack.

**Font stack by script:**
```css
/* Arabic / Hebrew — need fonts with good diacritic and vowel mark support */
:lang(ar), :lang(he) {
  font-family: 'Noto Sans Arabic', 'Noto Sans Hebrew', system-ui, sans-serif;
}

/* CJK — Chinese, Japanese, Korean need larger line-height */
:lang(zh), :lang(ja), :lang(ko) {
  font-family: 'Noto Sans CJK', system-ui, sans-serif;
  line-height: 1.7; /* CJK is visually denser at standard line-height */
}
```

**Text expansion budget:**
Translated strings are typically 20–30% longer than English in European languages,
and shorter in CJK. Design all containers to accommodate ±40% text length variation
without breaking layout. Never use fixed-width containers for UI text unless the
string is a code or identifier.

### How to test RTL layout

1. Add `dir="rtl"` to `<html>` in browser DevTools — without changing the language.
   This tests layout independently of translation content.
2. Scan for any element that breaks, overflows, or shows reversed intent.
3. Verify all spacing is mirrored (left margin ↔ right margin).
4. Verify directional icons have mirrored; non-directional icons have not.
5. Verify paragraph text aligns to the right.
6. Remove `dir="rtl"` and confirm LTR layout is unchanged.

---

## Code-reviewer checklist

- [ ] No hardcoded strings in JSX, `aria-label`, `placeholder`, `title`, `alt`
- [ ] No physical CSS: `margin-left/right`, `padding-left/right`,
      `text-align: left/right`, `left:/right:` positioning, `float: left/right`
- [ ] No physical Tailwind: `ml-*`, `mr-*`, `pl-*`, `pr-*`, `text-left`, `text-right`
- [ ] `dir` and `lang` set on `<html>` — not on a container element
- [ ] Directional icons use `scaleX(-1)` or `rtl:scale-x-[-1]`; non-directional icons unchanged
- [ ] UI containers accommodate text length variation — no fixed-width text containers
- [ ] New strings exist in `en/` locale and all active locales
- [ ] Android `strings.xml` updated if string appears in native UI
- [ ] Font stacks defined for non-Latin scripts if those locales are active
