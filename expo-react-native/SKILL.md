---
name: expo-react-native
description: Battle-tested Expo and React Native code patterns for New Architecture (RN 0.76+), Reanimated 4, FlashList v2, NativeWind v4/v5. Use when writing, reviewing, or refactoring React Native component code. Covers hooks, state, animations, lists, images, and styling patterns — not build config or tooling.
---

# Expo / React Native — Code Patterns

> Verified: reactnative.dev, expo.dev, shopify.engineering, software-mansion-labs/skills, callstackincubator/agent-skills, expo/skills, nativewind.dev

## Ground Rules

1. **New Architecture is default** (RN 0.76+, Expo SDK 53+). Two silent breakage patterns to fix proactively:
   - Auto state-batching drops intermediate values — components relying on them silently break
   - View flattening makes refs null — add `collapsable={false}` to every `<View ref={...}>`
2. **React 19 in SDK 53/54** — `use()`, `useTransition`, `useOptimistic`. `ref` is now a plain prop; `forwardRef` still works but is no longer needed for new code.
3. **React Compiler (SDK 54+)** — handles most memoization automatically. Don't add `useMemo`/`useCallback` without profiler evidence that a component is bailing out.
4. **Reanimated 4 (stable, requires New Architecture)** — `scheduleOnRN` is the preferred API over `runOnJS` for calling JS from a worklet. Both work; `scheduleOnRN` is the modern form.
5. **Profile before optimizing** — measure first, fix one thing, re-measure.

---

## 1. useEffect — 3 Legitimate Uses

Valid: (1) subscribing to an external system with no `useSyncExternalStore` interface, (2) imperative native call after mount with cleanup, (3) synchronizing two external systems. Everything else has a better primitive:

| Pattern | Replace with |
|---|---|
| Data fetch | `useQuery` (TanStack Query) |
| Derive value from state/props | Compute during render |
| Side effect on user event | Put it in the event handler |
| Layout measurement | `onLayout` callback |
| Animated derived value | `useDerivedValue` worklet |
| Store subscription | `useSyncExternalStore` |
| State reset when ID changes | `key={id}` prop to remount |

```tsx
// ❌ derives state in an effect — extra render, stale frame
useEffect(() => setFiltered(items.filter(fn)), [items, fn]);

// ✅ compute during render
const filtered = items.filter(fn);

// ❌ user event side effect in an effect
useEffect(() => {
  if (submitted) analytics.track('submitted');
}, [submitted]);

// ✅ in the handler where it belongs
async function handleSubmit() {
  await submit(data);
  analytics.track('submitted');
}
```

---

## 2. State

```tsx
// Server state — TanStack Query. Never useState/Redux for server data.
const { data, isPending } = useQuery({ queryKey: ['user', id], queryFn: () => fetchUser(id) });

// Client global state — Zustand with selectors (re-renders only on subscribed slice change)
const count = useStore((s) => s.count);       // re-renders only when count changes
const increment = useStore((s) => s.increment); // stable action reference

// useShallow when selector returns object/array
const { count, name } = useStore(useShallow((s) => ({ count: s.count, name: s.name })));

// Context — stable values only (auth, theme, i18n)
// Fast-changing values in context re-render ALL consumers — use Zustand selectors instead

// React 19: use() works in conditionals; useContext does not
const user = use(AuthContext);
```

---

## 3. React 19 Hooks

```tsx
// useTransition — input stays urgent, expensive update is interruptible
const [isPending, startTransition] = useTransition();
startTransition(() => setSearchQuery(text));

// useDeferredValue — render stale value while new one is computing
const deferred = useDeferredValue(query); // pass to heavy list, not the input

// useOptimistic — instant UI while async op runs
const [likes, addOptimistic] = useOptimistic(serverLikes, (cur, inc) => cur + inc);
async function handleLike() { addOptimistic(1); await likePost(id); }

// ref is a plain prop in React 19 (forwardRef still works, just no longer needed)
function Input({ ref, ...props }: Props & { ref?: Ref<TextInput> }) {
  return <TextInput ref={ref} {...props} />;
}
```

---

## 4. Lists — FlashList v2

```tsx
import { FlashList } from '@shopify/flash-list';

<FlashList
  data={items}
  renderItem={({ item }) => <ItemRow item={item} />}
  keyExtractor={item => item.id}          // never index — breaks recycler identity
  getItemType={item => item.type}         // required for heterogeneous lists
  onEndReached={fetchNextPage}
  onEndReachedThreshold={0.5}
  // estimatedItemSize — removed in v2, do not add
/>
```

- `renderItem` must be a stable reference — no inline arrow functions
- `recyclingKey={item.id}` on every `expo-image` inside list items (prevents stale image flash)
- `ScrollView` + `.map()` is wrong for any list > 20 items

---

## 5. Animations — Reanimated 4

See `references/animations.md` for full patterns.

```tsx
// Only animate GPU-composited properties
const style = useAnimatedStyle(() => ({
  transform: [{ translateX: withSpring(x.value) }],
  opacity: withTiming(visible.value ? 1 : 0),
  // ❌ never: width, height, top, left, margin, padding — triggers layout every frame
}));

// Scroll position — shared value, never useState
const scrollY = useSharedValue(0);
const handler = useAnimatedScrollHandler(e => { scrollY.value = e.contentOffset.y; });

// Calling JS from a worklet — scheduleOnRN is the modern form (Reanimated 4.1+)
import { scheduleOnRN } from 'react-native-worklets'; // or from 'react-native-reanimated'
onScroll: (e) => {
  scrollY.value = e.contentOffset.y;
  if (e.contentOffset.y > 100) scheduleOnRN(onHeaderVisible);
}

// CSS transitions — Reanimated 4 + New Architecture only
<Animated.View style={{ transition: { opacity: { duration: 300 } }, opacity: isVisible ? 1 : 0 }} />
```

---

## 6. Images

```tsx
import { Image } from 'expo-image';

<Image
  source={{ uri }}
  placeholder={{ blurhash }}
  contentFit="cover"
  transition={200}
  recyclingKey={item.id}   // required inside FlashList — prevents stale image on fast scroll
/>
```

---

## 7. Library Choices

| Use | Not |
|-----|-----|
| `expo-audio` | `expo-av` (audio) |
| `expo-video` | `expo-av` (video) |
| `expo-image` | `react-native` Image, FastImage |
| `expo-image source="sf:name"` | `expo-symbols`, `@expo/vector-icons` |
| `react-native-safe-area-context` | `SafeAreaView` from `react-native` |
| `process.env.EXPO_OS` | `Platform.OS` (not tree-shakeable) |
| `React.use(Context)` | `useContext(Context)` |
| `useWindowDimensions()` | `Dimensions.get()` |
| `expo-secure-store` | AsyncStorage for secrets |
| `Pressable` | `TouchableOpacity`, `TouchableHighlight` |
| `FlashList` | `FlatList` (on New Architecture) |

---

## 8. Expo Router v4 — Code Conventions

```
app/
  _layout.tsx          root layout — providers only
  (tabs)/_layout.tsx   NativeTabs
  (modal)/sheet.tsx    presentation: formSheet
```

- Route files only in `app/` — never co-locate components, hooks, or types there
- `_layout.tsx` required in every route group
- kebab-case filenames: `user-profile.tsx`

```tsx
// Prefetch on Link
<Link href="/detail" prefetch>View</Link>

// NativeTabs — zero JS re-renders on tab switch
import { NativeTabs } from 'expo-router/unstable-native-tabs';

// Native sheet — prefer over third-party bottom sheet libs
<Stack.Screen options={{
  presentation: 'formSheet',
  sheetAllowedDetents: [0.5, 1.0],
  sheetGrabberVisible: true,
}} />
```

---

## 9. Styling

```tsx
// New Architecture: boxShadow replaces legacy shadow* props (which are ignored)
<View style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }} />

// ScrollView padding — contentContainerStyle only (avoids clipping)
<ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>

// Safe area without a wrapper
<ScrollView contentInsetAdjustmentBehavior="automatic" />

// Apple HIG-compliant corners
<View style={{ borderRadius: 12, borderCurve: 'continuous' }} />

// Tabular numbers for counters/prices
<Text style={{ fontVariant: ['tabular-nums'] }}>{price}</Text>

// Selectable text for data users may copy
<Text selectable>{address}</Text>
```

For NativeWind: `references/nativewind.md`.

---

## 10. Hard Stops

| ❌ Anti-pattern | ✅ Fix |
|---|---|
| `collapsable` missing on ref'd View | `<View ref={r} collapsable={false}>` |
| `useEffect` to derive state | Compute during render |
| `useEffect` for event side effect | Move to event handler |
| `useState` for scroll position | `useSharedValue` |
| Animating layout props | `transform` + `opacity` only |
| `onSuccess` in `useQuery` (TanStack Query v5) | `useMutation.onSuccess` or `useEffect` on `data` |
| `estimatedItemSize` on FlashList v2 | Remove — deprecated |
| `FlatList` on New Architecture | `FlashList` v2 |
| Inline arrow function as `renderItem` | Stable component reference |
| `expo-av` | `expo-audio` / `expo-video` |
| `SafeAreaView` from `react-native` | `react-native-safe-area-context` |
| `shadow*` props / `elevation` | `boxShadow` CSS prop |
| `Platform.OS` in conditionals | `process.env.EXPO_OS` |
| `useMemo`/`useCallback` without profiler evidence | Remove — React Compiler handles it |
| `{count && <Text>}` where count can be 0 | `{count > 0 && <Text>}` |
| `forwardRef` on new components | Plain `ref` prop |

---

## References

- `references/animations.md` — Reanimated 4: scheduleOnRN, CSS transitions, gestures, layout animations, 120fps
- `references/state-and-effects.md` — TanStack Query patterns, Zustand (slices, selectors, persist, context injection), context rules
- `references/performance.md` — FlashList tuning, Intl hoisting, WeakRef caching, memory patterns
- `references/nativewind.md` — NativeWind v4/v5 className patterns, dark mode, CSS vars, gotchas
