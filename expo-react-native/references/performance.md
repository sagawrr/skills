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
  drawDistance={250}                 // px pre-rendered beyond viewport
  // for chat lists: maintainVisibleContentPosition + startRenderingFromBottom replaces inverted
  maintainVisibleContentPosition={{ minIndexForVisible: 0, startRenderingFromBottom: true }}
/>
```

- `recyclingKey` on every `expo-image` inside items — prevents stale image on fast scroll
- Item components must be stable references — never inline arrow functions in `renderItem`
- `estimatedItemSize` — deprecated in v2, remove it

---

## Hermes — Non-Obvious Constraints

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

**WeakRef for caches** — lets objects be garbage collected when no longer referenced elsewhere. `WeakRef` is available in Hermes (RN 0.70+):

```tsx
const cache = new Map<string, WeakRef<ComputedResult>>();

function getCached(key: string, compute: () => ComputedResult): ComputedResult {
  const existing = cache.get(key)?.deref();
  if (existing) return existing;
  const fresh = compute();
  cache.set(key, new WeakRef(fresh));
  return fresh;
}
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

- **`Platform.OS`** — Metro uses this for platform-specific tree-shaking at build time. `process.env.EXPO_OS` is a runtime value and does NOT trigger platform branch elimination per Expo docs.

---

## React Compiler — What to Trust It With

React Compiler (Expo SDK 54+) handles: component memoization, hook memoization, conditional memoization after early returns (impossible with manual `useMemo`). It does NOT handle: third-party library code, server rendering.

Verify it's working: in `react-profiler-fiber-tree` output, `useMemoCache` present = compiler memoizing that component. Absent = bailed out (usually a rules-of-hooks violation — fix the violation, not the memoization).

When manual `useMemo`/`useCallback` is still valid: profiler shows a component re-rendering with identical inputs and the computation is measurably expensive (> 1ms).
