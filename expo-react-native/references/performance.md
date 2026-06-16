# Performance — Deep Patterns

## Cold Start Optimization

1. **Defer heavy imports** — use dynamic `import()` for screens not on the initial route
2. **Inline requires** — Expo/Metro supports `inlineRequires: true` in `metro.config.js` (already default in new projects). Modules load on first use, not app start.
3. **Splash screen** — call `SplashScreen.preventAutoHideAsync()` before anything async; hide only after first route renders
4. **Fonts at compile time** — use Expo config plugin, not `useFonts` (eliminates one render cycle)

```js
// metro.config.js — ensure inline requires
const { getDefaultConfig } = require('expo/metro-config');
const config = getDefaultConfig(__dirname);
config.transformer.minifierConfig = { compress: { reduce_funcs: false } };
module.exports = config;
```

---

## Bundle Size

- `process.env.EXPO_OS` over `Platform.OS` — Metro tree-shakes platform branches at build time
- Avoid barrel imports (`import { X } from 'lib'`) — use direct paths (`import X from 'lib/X'`)
- `expo-image` replaces all image libraries (smaller, faster, single dep)
- Audit with `npx expo export --dump-sourcemap` + `source-map-explorer`

---

## FlashList — Advanced Tuning

```tsx
<FlashList
  data={items}
  renderItem={renderItem}
  estimatedItemSize={72}          // measure a real item via onLayout, update this
  getItemType={item => item.type} // heterogeneous list — critical for recycling
  overrideItemLayout={(layout, item) => { layout.size = item.height; }}  // variable height
  drawDistance={250}              // px beyond viewport to pre-render (default 250)
  disableAutoLayout={false}       // keep true only if you have a fixed-height list
  // Pagination
  onEndReached={fetchNextPage}
  onEndReachedThreshold={0.5}
/>
```

**Recycling rules:**
- `recyclingKey` on `expo-image` = critical — without it, old image flashes on scroll
- Do not use `index` as `keyExtractor` — prevents recycling optimization
- Avoid conditional hooks inside `renderItem` components

---

## Memory Leaks — Common Patterns

```tsx
// ❌ Listener not removed
useEffect(() => {
  AppState.addEventListener('change', handler);
  // missing return cleanup!
}, []);

// ✅
useEffect(() => {
  const sub = AppState.addEventListener('change', handler);
  return () => sub.remove();
}, []);

// ❌ Timer not cleared
useEffect(() => {
  const id = setInterval(tick, 1000);
  // missing clearInterval!
}, []);

// ✅
useEffect(() => {
  const id = setInterval(tick, 1000);
  return () => clearInterval(id);
}, []);

// ❌ Fetch on unmounted component (React 18 StrictMode catches this in dev)
useEffect(() => {
  let mounted = true;
  fetch(url).then(d => { if (mounted) setData(d); });
  return () => { mounted = false; };
}, [url]);

// ✅ React 19 + TanStack Query handles this automatically — just use useQuery
```

---

## Reanimated v3 — Worklet Rules

- All code inside `useAnimatedStyle`, `useAnimatedScrollHandler`, `useDerivedValue`, `useAnimatedReaction` runs on the UI thread — no JS objects allowed
- Never call a JS function from a worklet; only call other worklets
- Mark cross-thread functions with `'worklet'` directive
- `runOnJS(fn)(args)` to call back to JS thread from worklet

```tsx
const handler = useAnimatedScrollHandler({
  onScroll: (e) => {
    'worklet'; // implicit in Reanimated v3, explicit for clarity
    scrollY.value = e.contentOffset.y;
    if (scrollY.value > 100) runOnJS(onScrollPast100)();
  },
});
```

---

## Hermes Engine

Hermes is the default JS engine (Expo SDK 48+). Patterns that benefit:

- Destructuring and spread are fast — use freely
- `async/await` compiles efficiently on Hermes
- `WeakRef` and `FinalizationRegistry` are available — use for cache cleanup
- `BigInt` is NOT supported — use string IDs for large DB IDs

---

## EAS Build / Update Patterns

```json
// eas.json — minimal hardened config
{
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "env": { "APP_ENV": "development" }
    },
    "preview": {
      "distribution": "internal",
      "channel": "preview"
    },
    "production": {
      "autoIncrement": true,
      "channel": "production"
    }
  },
  "update": {
    "channel": "production"
  }
}
```

- Use `expo-constants` `expoConfig.extra` for runtime env vars, not `process.env` in app code
- Always set `runtimeVersion.policy: "appVersion"` to prevent incompatible JS updates
- `eas update --branch preview` for QA; `eas update --branch production` for live
