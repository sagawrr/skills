---
name: expo-react-native
description: Battle-tested Expo and React Native patterns for New Architecture (RN 0.76+), Expo SDK 53–56, Reanimated 4, FlashList v2, NativeWind v4. Use when building, reviewing, or refactoring any Expo or React Native codebase. Covers code patterns, state, animations, performance, and styling — not device interaction or profiling (see argent-react-native-* skills).
---

# Expo / React Native — Hardened Patterns

> Verified: reactnative.dev, expo.dev/changelog, shopify.engineering, software-mansion-labs/skills, callstackincubator/agent-skills, expo/skills, nativewind.dev

## Ground Rules

1. **New Architecture is default** — RN 0.76+, Expo SDK 53+. Enabling it does not auto-improve perf; apps need refactoring to use concurrent features and synchronous layout.
2. **React 19 in SDK 53/54** — `use()`, `useTransition`, `useOptimistic`. No more `forwardRef` in function components. `React.use(Context)` replaces `useContext`.
3. **React Compiler: SDK 54+** — `"experiments": { "reactCompiler": true }` in `app.json`, no Babel config. App code only (not node_modules). Does NOT auto-remove all `useMemo`/`useCallback` — verify bail-outs with profiler (`useMemoCache` absent = bailed out).
4. **Reanimated 4: `runOnJS` is removed** — use `scheduleOnRN(fn, ...args)` from `react-native-worklets`. Install `react-native-worklets` (required peer dep, SDK 54+).
5. **Measure before optimizing** — profile first, fix one thing, re-measure. Never suggest `useMemo`/`useCallback` changes without profiler evidence.

---

## 1. useEffect — Know When Not To Use It

`useEffect` has 3 legitimate uses: (1) imperative subscriptions with no `useSyncExternalStore` interface, (2) triggering imperative native code after mount with cleanup, (3) synchronizing two external systems. Everything else has a better primitive.

| Pattern | Replace with |
|---|---|
| Data fetch on mount | `useQuery` (TanStack Query) |
| Derived state from props/state | Compute during render — no hook |
| Side effect on event | Put it in the event handler |
| Layout measurement | `onLayout` callback — no flicker |
| Promise + Suspense | `use(promise)` — promise must be created outside render |
| Store subscription | `useSyncExternalStore` |
| Animated value derivation | `useDerivedValue` worklet |
| State reset when ID changes | `key={id}` prop to remount |

```tsx
// ✅ use() — promise must be stable (created outside render, not inline)
function Profile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise);
  return <Text>{user.name}</Text>;
}
// Wrap with <Suspense fallback={<Skeleton />}> + <ErrorBoundary>
```

```tsx
// ✅ onLayout — synchronous, no flicker frame
<View onLayout={e => setSize(e.nativeEvent.layout)} />
```

---

## 2. State

- **Server state** → TanStack Query. Never in Redux or `useState`.
- **Client global state** → Zustand or Jotai. See `references/state-and-effects.md` for patterns.
- **Context** — only for stable values (auth, theme). Fast-changing values in context re-render all consumers. Route fast-changing values to Zustand or `useSharedValue`.

```tsx
// React 19 — use() works in conditionals; useContext does not
const user = use(AuthContext);
```

---

## 3. React 19 Patterns

```tsx
// useTransition — input stays urgent, search is interruptible
const [isPending, startTransition] = useTransition();
startTransition(() => setSearchQuery(text));

// useOptimistic — instant UI, real update in background
const [likes, addOptimistic] = useOptimistic(serverLikes, (cur, inc) => cur + inc);
async function handleLike() { addOptimistic(1); await likePost(id); }

// forwardRef is gone in React 19 — ref is a plain prop
function Input({ ref, ...props }: Props & { ref?: Ref<TextInput> }) {
  return <TextInput ref={ref} {...props} />;
}
```

---

## 4. Lists — FlashList v2

FlashList v2 uses New Architecture synchronous layout — no size estimation needed.

```tsx
<FlashList
  data={items}
  renderItem={({ item }) => <ItemRow item={item} />}
  keyExtractor={item => item.id}
  // v2: estimatedItemSize is DEPRECATED — do not add it
  getItemType={item => item.type}     // enables per-type recycler pools
  onEndReached={fetchNextPage}
  onEndReachedThreshold={0.5}
/>
```

- Item component must be a stable reference — no inline arrow functions as `renderItem`
- Never create objects/arrays inline inside `renderItem`
- Set `recyclingKey` on every `expo-image` inside list items (prevents stale image flash)
- Never use `index` as `keyExtractor` — breaks recycling identity
- FlatList: valid fallback if not on New Architecture. ScrollView rendering all items is always wrong for lists > ~20 items.

---

## 5. Animations — Reanimated 4

> Full patterns: `references/animations.md`

**`runOnJS` is removed. Use `scheduleOnRN` everywhere.**

```tsx
import { scheduleOnRN } from 'react-native-worklets';

// ❌ Reanimated 3 — crashes in Reanimated 4
onScroll: (e) => { runOnJS(setHeader)(e.contentOffset.y > 100); }

// ✅ Reanimated 4
onScroll: (e) => {
  scrollY.value = e.contentOffset.y;
  if (e.contentOffset.y > 100) scheduleOnRN(setHeader, true);
}
```

- Animate **only** `transform` and `opacity` — animating `width`/`height`/`top`/`left`/`margin` triggers layout recalculation every frame
- Scroll position → `useSharedValue`, never `useState`
- `useDerivedValue` for derived animated values; `useAnimatedReaction` only for side effects
- CSS transitions are first-class in Reanimated 4 (New Architecture only): `style={{ transition: { opacity: { duration: 300 } }, opacity: visible ? 1 : 0 }}`

---

## 6. Images

```tsx
import { Image } from 'expo-image';

<Image
  source={{ uri: url }}
  placeholder={{ blurhash }}
  contentFit="cover"
  transition={200}
  recyclingKey={item.id}   // required inside FlashList — prevents stale image flash
/>
```

Never: `Image` from `react-native`, `img` element, FastImage.

---

## 7. Expo SDK Breaking Changes

| SDK | Key changes |
|-----|-------------|
| 53 | New Architecture default; Expo Router v4; RN 0.79 + React 19 |
| 54 | React Compiler auto-configured; `react-native-worklets` required peer dep |
| 55 | `expo-av` split → `expo-audio` + `expo-video` |
| 56 | `@react-navigation/*` imports move to `expo-router` entry points |

---

## 8. Library Preferences

| Use | Never use |
|-----|-----------|
| `expo-audio` | `expo-av` for audio |
| `expo-video` | `expo-av` for video |
| `expo-image` | `react-native` Image, `img`, FastImage |
| `expo-image` `source="sf:name"` | `expo-symbols`, `@expo/vector-icons` |
| `react-native-safe-area-context` | `SafeAreaView` from `react-native` |
| `process.env.EXPO_OS` | `Platform.OS` (runtime, not tree-shakeable) |
| `React.use(Context)` | `useContext(Context)` |
| `useWindowDimensions()` | `Dimensions.get()` |
| CSS `boxShadow` prop | Legacy `shadow*` or `elevation` props |
| `expo-secure-store` | AsyncStorage for secrets |

---

## 9. Expo Router v4 (SDK 53+)

```tsx
// Guarded route groups — protect authenticated screens
// app/(protected)/_layout.tsx exports a guard function

// Route prefetching
<Link href="/detail" prefetch>View Detail</Link>

// Build-time redirects — app.json
{ "expo": { "router": { "redirects": [{ "source": "/old", "destination": "/new" }] } } }
```

File conventions:
- Route files only in `app/` — never co-locate components, utils, or types
- `_layout.tsx` in every route group
- kebab-case filenames: `user-profile.tsx`
- Always have a route matching `/`

```tsx
// NativeTabs — zero JS re-renders on tab switch
import { NativeTabs } from 'expo-router/unstable-native-tabs';

// Native sheets — prefer over custom bottom sheet libs
<Stack.Screen options={{
  presentation: 'formSheet',
  sheetAllowedDetents: [0.5, 1.0],
  sheetGrabberVisible: true,
  contentStyle: { backgroundColor: 'transparent' }, // liquid glass iOS 26+
}} />
```

**RSC + EAS Update are incompatible** — do not use React Server Components in production until EAS Update support ships.

---

## 10. Styling

```tsx
// ✅ New Architecture — CSS boxShadow
<View style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }} />
// ❌ Ignored on New Architecture
shadow={{ color: '#000', radius: 4, opacity: 0.2 }}

// ScrollView padding — always contentContainerStyle (avoids clipping)
<ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>

// Safe area — no SafeAreaView wrapper needed
<ScrollView contentInsetAdjustmentBehavior="automatic" />

// Apple HIG continuous corners
<View style={{ borderRadius: 12, borderCurve: 'continuous' }} />

// Tabular numbers for counters/prices
<Text style={{ fontVariant: ['tabular-nums'] }}>{count}</Text>

// Selectable text for user-copyable data
<Text selectable>{address}</Text>
```

For NativeWind (Tailwind in RN): see `references/nativewind.md`.

---

## 11. Anti-Pattern Hard Stops

| Anti-pattern | Replacement |
|---|---|
| `runOnJS` (Reanimated 4) | `scheduleOnRN` from `react-native-worklets` |
| `estimatedItemSize` on FlashList v2 | Remove — deprecated, auto-handled |
| `useState` for scroll position | `useSharedValue` |
| Animating `width`/`height`/`top`/`left` | Animate `transform` + `opacity` only |
| `useContext(X)` | `use(X)` (React 19) |
| `forwardRef` in function components | Plain `ref` prop (React 19) |
| `FlatList` for lists | `FlashList` v2 |
| `expo-av` | `expo-audio` + `expo-video` |
| `SafeAreaView` from `react-native` | `react-native-safe-area-context` |
| Legacy `shadow*` / `elevation` | CSS `boxShadow` |
| `Platform.OS` | `process.env.EXPO_OS` |
| `Dimensions.get()` | `useWindowDimensions()` |
| Barrel imports `import { X } from 'lib'` | Direct path `import X from 'lib/X'` |
| Inline style objects in list items | Hoisted `StyleSheet.create` const |
| `useMemo`/`useCallback` speculatively | Let React Compiler handle; verify with profiler |
| `img` / `div` elements | `expo-image` / `View` |
| `{count && <Text>}` (falsy number) | `{count > 0 && <Text>}` or ternary |
| RSC with EAS Update in production | Wait — EAS Update is incompatible |

---

## References

- `references/nativewind.md` — NativeWind v4 setup, dark mode, gotchas, third-party components
- `references/animations.md` — Reanimated 4: CSS transitions, gestures, layout animations, 120fps
- `references/state-and-effects.md` — TanStack Query patterns, Zustand+SecureStore, Jotai
- `references/performance.md` — cold start, bundle size, FlashList tuning, EAS config
