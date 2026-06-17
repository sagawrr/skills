# Performance — Deep Patterns

> Verified: Callstack "Ultimate Guide to React Native Optimization", expo/skills, Shopify

**Measure → Fix one thing → Re-measure → Validate.** Never optimize speculatively.

React Compiler config is in SKILL.md Ground Rule 4. Reanimated 4 patterns are in `references/animations.md`. NativeWind performance is in `references/nativewind.md`.

---

## Cold Start / TTI

### Android: Disable JS bundle compression (biggest Android TTI win)

Enables Hermes to `mmap` the bundle directly instead of loading it into memory.

```groovy
// android/app/build.gradle — do NOT set compress: true
android { bundleConfig { ... } }
```

In practice: check your existing config doesn't force compression. The Expo default is already correct; only apply if TTI measurements show slowness.

### Fonts at build time — config plugin, not `useFonts`

`useFonts` = runtime load = extra render cycle. Config plugin = compile-time = zero runtime cost.

```json
// app.json
{ "expo": { "plugins": [["expo-font", { "fonts": ["./assets/fonts/MyFont.ttf"] }]] } }
```

### Splash screen — hide only after critical data is ready

```tsx
import * as SplashScreen from 'expo-splash-screen';
SplashScreen.preventAutoHideAsync(); // call before anything async

// In root layout, after fonts + critical data:
SplashScreen.hideAsync();
```

---

## Bundle Size

```bash
# Analyze
npx expo export --dump-sourcemap
npx source-map-explorer output.js --no-border-checks
```

**Priority fixes:**

1. **Barrel imports** — critical. `import { X } from 'some-lib'` pulls the entire library. Use `import X from 'some-lib/X'`.

2. **`process.env.EXPO_OS`** — Metro tree-shakes the dead platform's code at build time. `Platform.OS` is a runtime value — no tree-shaking possible.

3. **R8 (Android)** — native code shrinking:
```groovy
// android/app/build.gradle
buildTypes {
  release { minifyEnabled true }
}
```

4. **Tree shaking** — enabled by default in Expo SDK 52+ via Metro. Verify unused exports are eliminated with the bundle analyzer.

---

## FlashList v2 Advanced

```tsx
<FlashList
  data={items}
  renderItem={renderItem}
  keyExtractor={item => item.id}  // never use index — breaks recycler identity
  getItemType={item => item.type} // per-type recycler pools — required for heterogeneous lists
  drawDistance={250}              // px to pre-render beyond viewport
  // Inverted lists (chat)
  inverted
  maintainVisibleContentPosition={{ minIndexForVisible: 0 }}
/>
```

- `recyclingKey` on every `expo-image` inside items — prevents stale image on scroll
- Item components must be stable references — no inline arrow functions in `renderItem`

---

## Hermes Engine — What's Non-Obvious

- `BigInt` is **not supported** — use string IDs for large numeric API IDs
- `WeakRef` + `FinalizationRegistry` are available — use for cache implementations that don't prevent GC
- `Intl` formatters are built-in — **hoist creation outside components**, never inside render:

```tsx
// ❌ new Intl.NumberFormat on every render
function Price({ n }) { return <Text>{new Intl.NumberFormat('en-US', {...}).format(n)}</Text>; }

// ✅ created once at module level
const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
function Price({ n }) { return <Text>{fmt.format(n)}</Text>; }
```

---

## EAS Config

```json
// eas.json — minimal hardened config
{
  "build": {
    "development": { "developmentClient": true, "distribution": "internal" },
    "preview":     { "distribution": "internal", "channel": "preview" },
    "production":  { "autoIncrement": true, "channel": "production" }
  }
}
```

```json
// app.json — prevent incompatible OTA pushes
{ "expo": { "runtimeVersion": { "policy": "appVersion" } } }
```

- JS-only changes → `eas update --branch production` (no rebuild needed)
- Native changes (new native dep, config plugin change) → full `eas build`
- Delete `sdkVersion` from `app.json` — let Expo manage it

