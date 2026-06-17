# Performance — Deep Patterns

> Verified: Callstack "Ultimate Guide to React Native Optimization", Shopify FlashList v2 blog, expo/skills

## Optimization Loop (always follow this order)

**Measure → Fix one thing → Re-measure → Validate**

Do not report performance issues based on component tree depth or count alone — use real measurements. Do not suggest `useMemo`/`useCallback` changes without profiler evidence.

---

## Cold Start / TTI

1. **Android: disable JS bundle compression** — allows Hermes to mmap the bundle directly (biggest TTI win on Android)

```js
// metro.config.js
const config = getDefaultConfig(__dirname);
config.transformer.enableBabelRCLookup = false;
// In android/app/build.gradle:
// bundleCommand: "bundle --minify true"
// Do NOT set compress: true — this disables mmap
```

2. **Inline requires** — already default in Expo projects via Metro. Modules load on first use, not app start. Verify in `metro.config.js`:

```js
config.transformer.getTransformOptions = async () => ({
  transform: { inlineRequires: true },
});
```

3. **Splash screen** — call `SplashScreen.preventAutoHideAsync()` before any async work; hide only after critical data is ready

```tsx
import * as SplashScreen from 'expo-splash-screen';

SplashScreen.preventAutoHideAsync();

export default function App() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    Promise.all([loadFonts(), prefetchCriticalData()])
      .finally(() => { setReady(true); SplashScreen.hideAsync(); });
  }, []);
  if (!ready) return null;
  return <RootNavigator />;
}
```

4. **Preload common screens** before navigating — native navigation (`react-native-screens`) is required

5. **Fonts at build time** — use Expo config plugin, not `useFonts` hook. Eliminates a render cycle and a network round-trip.

---

## Bundle Size

```bash
# Analyze JS bundle
npx react-native bundle \
  --entry-file index.js --bundle-output out.js \
  --platform ios --sourcemap-output out.map \
  --dev false --minify true
npx source-map-explorer out.js --no-border-checks

# Expo managed workflow
npx expo export --dump-sourcemap
```

**Fixes in priority order:**

1. **Barrel imports** — critical. Replace `import { X } from 'some-lib'` with `import X from 'some-lib/X'`. Barrel files pull in the entire library even when tree-shaking is enabled.

2. **Tree shaking** — enabled by default in Expo SDK 52+ (`experimentalImportSupport: true` in Metro). Verify unused exports are removed.

3. **`process.env.EXPO_OS`** — Metro tree-shakes the other platform's code at build time. `Platform.OS` is a runtime value — no tree-shaking.

4. **R8 (Android)** — enables native code shrinking. In `android/app/build.gradle`:
```groovy
buildTypes {
  release {
    minifyEnabled true
    proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
  }
}
```

5. **Remove Intl polyfills** only after confirming Hermes covers the API you need. Check Hermes changelog before removing.

---

## FlashList v2 Advanced Tuning

```tsx
<FlashList
  data={items}
  renderItem={({ item }) => <ItemRow item={item} />}
  keyExtractor={item => item.id}
  // v2: estimatedItemSize DEPRECATED — do not add it
  getItemType={item => item.type}   // heterogeneous list — critical for recycler pool separation
  drawDistance={250}                // px to pre-render beyond viewport (default 250)
  onEndReached={fetchNextPage}
  onEndReachedThreshold={0.5}
  ListFooterComponent={isFetching ? <Spinner /> : null}
  // For inverted lists (chat)
  inverted
  maintainVisibleContentPosition={{ minIndexForVisible: 0 }}
/>
```

**Recycling checklist:**
- `recyclingKey` on every `expo-image` inside list items — prevents stale image flash
- Never use `index` as `keyExtractor` — breaks recycling identity
- No conditional hooks inside `renderItem` components
- Item component should be a stable reference — hoist outside the parent, or wrap with `React.memo` only if compiler confirms bail-out

---

## Memory Leaks

### Pattern 1: Listener not cleaned up

```tsx
useEffect(() => {
  const sub = AppState.addEventListener('change', handler);
  return () => sub.remove(); // ✅ always return cleanup
}, []);
```

### Pattern 2: Timer not cleared

```tsx
useEffect(() => {
  const id = setInterval(tick, 1000);
  return () => clearInterval(id);
}, []);
```

### Pattern 3: AbortController for fetch

```tsx
// With useQuery — this is handled automatically
// Manual fetch:
useEffect(() => {
  const controller = new AbortController();
  fetch(url, { signal: controller.signal }).then(setData).catch(() => {});
  return () => controller.abort();
}, [url]);
```

### Pattern 4: WeakRef for caches (Hermes supports it)

```tsx
// Cache that doesn't prevent garbage collection
const cache = new Map<string, WeakRef<ExpensiveObject>>();
const registry = new FinalizationRegistry((key: string) => cache.delete(key));

function getCached(key: string) {
  const ref = cache.get(key);
  const obj = ref?.deref();
  if (obj) return obj;
  const fresh = createExpensive(key);
  cache.set(key, new WeakRef(fresh));
  registry.register(fresh, key);
  return fresh;
}
```

---

## Hermes Engine Notes

Hermes is the JS engine on all Expo projects (SDK 48+). What this means in practice:

- `async/await` compiles efficiently — prefer over `.then()` chains
- `WeakRef` + `FinalizationRegistry` are available (use for caches)
- `BigInt` is **NOT supported** — use string IDs for large numeric IDs from APIs
- Destructuring and spread are fast — no need to avoid them for perf
- `Intl.DateTimeFormat`, `Intl.NumberFormat` are built-in — hoist creation outside render

```tsx
// ❌ create Intl formatter inside render — allocated on every render
function Price({ amount }: { amount: number }) {
  const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  return <Text>{fmt.format(amount)}</Text>;
}

// ✅ hoist outside component — created once
const priceFormatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
function Price({ amount }: { amount: number }) {
  return <Text>{priceFormatter.format(amount)}</Text>;
}
```

---

## EAS Build / Update Config

```json
// eas.json
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
  }
}
```

```json
// app.json — runtime version (prevents incompatible OTA updates)
{
  "expo": {
    "runtimeVersion": { "policy": "appVersion" },
    "updates": { "enabled": true, "fallbackToCacheTimeout": 0 }
  }
}
```

- JS-only changes → `eas update --branch production` (no rebuild)
- Native changes → full `eas build` required
- `sdkVersion` in `app.json` → delete it, let Expo manage automatically
- **RSC + EAS Update**: incompatible as of SDK 53. Do not use RSC in production with OTA updates.

---

## React Compiler — SDK 54+

```json
// app.json — enable (SDK 54+, no Babel config needed)
{
  "expo": {
    "experiments": { "reactCompiler": true }
  }
}
```

**What it does:**
- Automatic build-time memoization of components and hooks
- Conditional memoization after early returns (impossible with `useMemo`)
- Runs on app code only — not `node_modules`
- Disabled during server rendering

**What it does NOT do:**
- Does not let you blindly remove all `useMemo`/`useCallback` — verify with profiler
- Does not optimize third-party library code
- Does not replace architecture decisions (context splitting, state minimization)

**Verify compiler is working:**
```bash
# In Metro output or react-profiler-fiber-tree output
# Look for: useMemoCache — present = compiler is memoizing this component
# Absent = compiler bailed out — may need to fix rules of hooks violations
```
