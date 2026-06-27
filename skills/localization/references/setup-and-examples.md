# Localization Setup & Code Reference

## Recommended library: react-i18next

Install (subject to `third-party-policy` approval):
```bash
npm install react-i18next i18next i18next-browser-languagedetector
```

## File structure
```
src/i18n/
├── index.ts              # i18next initialisation
└── locales/
    ├── en/
    │   ├── common.json   # shared strings
    │   └── [feature].json
    └── he/
        ├── common.json
        └── [feature].json
```

## i18next initialisation
```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    defaultNS: 'common',
    supportedLngs: ['en', 'he'],
    resources: { en: { common: enCommon }, he: { common: heCommon } },
    interpolation: { escapeValue: false },
    detection: { order: ['localStorage', 'navigator'], caches: ['localStorage'] },
  });
```
Import in `main.tsx` before the app renders: `import './i18n';`

## HTML direction sync
```typescript
i18n.on('languageChanged', (lng) => {
  document.documentElement.setAttribute('dir', i18n.dir(lng));
  document.documentElement.setAttribute('lang', lng);
});
```

## CSS logical properties reference
| ❌ Avoid | ✅ Use |
|---|---|
| `margin-left` | `margin-inline-start` |
| `margin-right` | `margin-inline-end` |
| `padding-left` | `padding-inline-start` |
| `padding-right` | `padding-inline-end` |
| `text-align: left` | `text-align: start` |
| `left: 0` | `inset-inline-start: 0` |

## Android strings.xml structure
```
android/app/src/main/res/
├── values/strings.xml          # English (default)
├── values-he/strings.xml       # Hebrew
└── values-ar/strings.xml       # Arabic
```
Sync comment pattern:
```xml
<!-- i18n key: common.save_button -->
<string name="save_button">Save</string>
```

## Using translations in React
```typescript
const { t } = useTranslation('common');
return <button>{t('save_button')}</button>;
```

## Directional icon mirroring
```tsx
<ChevronIcon class="rtl:scale-x-[-1]" />
// or:
style={{ transform: i18n.dir() === 'rtl' ? 'scaleX(-1)' : 'none' }}
```