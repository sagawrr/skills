# Performance — Code-Level Patterns

> Measure → fix one thing → re-measure → validate. Never optimize speculatively.

---

## FlashList v2 — Advanced

```tsx
<FlashList
  data={items}
  renderItem={renderItem}
  keyExtractor={item => item.id}     // never index — breaks recycler identity
  getItemType={item => item.type}    // required for heterogeneous lists; enables per-type recycler pools
  drawDistance={250}                 // px pre-rendered beyond viewport (default 250)
  inverted                           // for chat lists
  maintainVisibleContentPosition={{ minIndexForVisible: 0 }}  // keeps scroll position stable in chat
/>
```

- `recyclingKey` on every `expo-image` inside items — prevents stale image on fast scroll
- Item components must be stable references — never inline arrow functions in `renderItem`
- `estimatedItemSize` — deprecated in v2, remove it

---

## Hermes — Non-Obvious Constraints

- **`BigInt` is not supported** — use string IDs for large numeric IDs from APIs
- **`Intl` formatters must be hoisted** outside components — allocated on every render otherwise

```tsx
// ❌ new Intl.NumberFormat on every render
function Price({ n }) {
  return <Text>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)}</Text>;
}

// ✅ created once at module scope
const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
function Price({ n }) { return <Text>{fmt.format(n)}</Text>; }
```

---

## Memory — Non-Obvious Patterns

**WeakRef for caches** — lets objects be garbage collected when no longer referenced elsewhere:

```tsx
const cache = new Map<string, WeakRef<ComputedResult>>();
const registry = new FinalizationRegistry((key: string) => cache.delete(key));

function getCached(key: string, compute: () => ComputedResult): ComputedResult {
  const existing = cache.get(key)?.deref();
  if (existing) return existing;
  const fresh = compute();
  cache.set(key, new WeakRef(fresh));
  registry.register(fresh, key);
  return fresh;
}
```

(`WeakRef` + `FinalizationRegistry` are available in Hermes.)

**Subscriptions must clean up:**

```tsx
useEffect(() => {
  const sub = AppState.addEventListener('change', handler);
  return () => sub.remove();   // missing this = leak on unmount
}, []);
```

---

## Bundle — Code-Level Wins

- **Barrel imports** pull the entire library even with tree-shaking. Use direct paths:
  ```tsx
  // ❌ pulls everything from the lib
  import { formatDate, parseDate } from 'date-fns';
  // ✅
  import formatDate from 'date-fns/formatDate';
  import parseDate from 'date-fns/parseDate';
  ```

- **`process.env.EXPO_OS`** — Metro tree-shakes the dead platform's code at build time. `Platform.OS` is a runtime value; no tree-shaking possible.

  ```tsx
  // ❌ both branches shipped in bundle
  const isIOS = Platform.OS === 'ios';

  // ✅ dead branch eliminated at build time
  const isIOS = process.env.EXPO_OS === 'ios';
  ```

---

## React Compiler — What to Trust It With

React Compiler (Expo SDK 54+) handles: component memoization, hook memoization, conditional memoization after early returns (impossible with manual `useMemo`). It does NOT handle: third-party library code, server rendering.

Verify it's working: in `react-profiler-fiber-tree` output, `useMemoCache` present = compiler memoizing that component. Absent = bailed out (usually a rules-of-hooks violation — fix the violation, not the memoization).

When manual `useMemo`/`useCallback` is still valid: profiler shows a component re-rendering with identical inputs and the computation is measurably expensive (> 1ms).
