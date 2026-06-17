---
name: expo-react-native
description: Battle-tested Expo and React Native patterns for New Architecture (RN 0.76+), Expo SDK 53–56, Reanimated 4, FlashList v2, NativeWind v4/v5. Use when building, reviewing, or refactoring any Expo or React Native codebase. Covers code patterns, state, animations, performance, and styling — not device interaction or profiling (see argent-react-native-* skills for those).
---

# Expo / React Native — Hardened Patterns

> Verified: reactnative.dev, expo.dev/changelog, shopify.engineering, software-mansion-labs/skills, callstackincubator/agent-skills, expo/skills, nativewind.dev

## Ground Rules

1. **New Architecture is default** — RN 0.76+, Expo SDK 53+. Enabling it alone does not improve perf — apps need refactoring to use concurrent features and synchronous layout effects.
2. **New Architecture breakage to fix proactively:**
   - State batching removes intermediate values — components relying on them silently break
   - View flattening makes refs null — add `collapsable={false}` to every `<View>` that has a `ref`
3. **React 19 in SDK 53/54** — `use()`, `useTransition`, `useOptimistic`. No more `forwardRef`. `React.use(Context)` over `useContext`.
4. **React Compiler: SDK 54+** — `"experiments": { "reactCompiler": true }` in `app.json`. App code only. Does NOT auto-remove all `useMemo`/`useCallback` — verify with profiler (`useMemoCache` absent = bailed out).
5. **Reanimated 4: `runOnJS` removed** — use `scheduleOnRN(fn, ...args)` from `react-native-worklets` (required peer dep SDK 54+). See `references/animations.md`.
6. **Measure before optimizing** — profile first, fix one thing, re-measure. No `useMemo`/`useCallback` changes without profiler evidence.

---

## 1. useEffect — Know the 3 Legitimate Uses

Valid: (1) subscribing to an external system with no `useSyncExternalStore` interface, (2) imperative native call after mount with cleanup, (3) synchronizing two external systems.

**Everything else has a better primitive:**

| You want to… | Use instead |
|---|---|
| Fetch data | `useQuery` (TanStack Query) |
| Derive from props/state | Compute during render |
| Side effect on event | Put it in the event handler |
| Layout measurement | `onLayout` callback |
| Animate on value change | `useDerivedValue` |
| Store subscription | `useSyncExternalStore` |
| Reset state when ID changes | `key={id}` prop to remount |

```tsx
// use() — promise must be created outside render (stable reference)
function Profile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise); // suspends; wrap parent in <Suspense> + <ErrorBoundary>
  return <Text>{user.name}</Text>;
}
```

---

## 2. State

- **Server state** → TanStack Query. Never `useState` or Redux for server data.
- **Client global state** → Zustand or Jotai. See `references/state-and-effects.md`.
- **Context** — stable values only (auth, theme). Fast-changing values in context re-render all consumers; use Zustand or `useSharedValue` instead.
- `React.use(Context)` works in conditionals; `useContext` does not.

---

## 3. React 19

```tsx
// useTransition — input stays urgent, heavy update is interruptible
const [isPending, startTransition] = useTransition();
startTransition(() => setSearchQuery(text));

// useOptimistic — instant UI, real update in background
const [likes, addOptimistic] = useOptimistic(serverLikes, (cur, inc) => cur + inc);

// forwardRef gone in React 19 — ref is a plain prop
function Input({ ref, ...props }: Props & { ref?: Ref<TextInput> }) {
  return <TextInput ref={ref} {...props} />;
}
```

---

## 4. Lists — FlashList v2

```tsx
<FlashList
  data={items}
  renderItem={({ item }) => <ItemRow item={item} />}
  keyExtractor={item => item.id}          // never index — breaks recycler identity
  getItemType={item => item.type}         // required for heterogeneous lists
  onEndReached={fetchNextPage}
  onEndReachedThreshold={0.5}
  // estimatedItemSize — DEPRECATED in v2, do not add
/>
```

- Item component must be a stable reference — no inline arrow functions as `renderItem`
- Set `recyclingKey={item.id}` on every `expo-image` inside list items
- FlatList: valid fallback when not on New Architecture. `ScrollView` + `.map()` is never correct for lists > 20 items.

---

## 5. Animations

See `references/animations.md` for full Reanimated 4 patterns including `scheduleOnRN`, CSS transitions, layout animations, and 120fps setup.

Core rules:
- Animate **only** `transform` and `opacity` — `width`/`height`/`top`/`left`/`margin` trigger layout recalculation every frame
- Scroll position → `useSharedValue`, never `useState`
- `useDerivedValue` for derived animated values; `useAnimatedReaction` for side effects only

---

## 6. Images

```tsx
import { Image } from 'expo-image';
<Image source={{ uri }} placeholder={{ blurhash }} contentFit="cover" transition={200} recyclingKey={item.id} />
```

Never: `Image` from `react-native`, `img` element, FastImage.

---

## 7. SDK Breaking Changes

| SDK | Key changes |
|-----|-------------|
| 53 | New Architecture default; Expo Router v4; RN 0.79 + React 19 |
| 54 | React Compiler auto-configured; `react-native-worklets` required |
| 55 | `expo-av` → `expo-audio` + `expo-video` |
| 56 | `@react-navigation/*` imports → `expo-router` entry points |

---

## 8. Library Preferences

| Use | Never |
|-----|-------|
| `expo-audio` / `expo-video` | `expo-av` |
| `expo-image` | `react-native` Image, FastImage, `img` |
| `expo-image source="sf:name"` | `expo-symbols`, `@expo/vector-icons` |
| `react-native-safe-area-context` | `SafeAreaView` from `react-native` |
| `process.env.EXPO_OS` | `Platform.OS` (not tree-shakeable) |
| `React.use(Context)` | `useContext(Context)` |
| `useWindowDimensions()` | `Dimensions.get()` |
| CSS `boxShadow` prop | Legacy `shadow*` / `elevation` |
| `expo-secure-store` | AsyncStorage for secrets |

---

## 9. Expo Router v4 (SDK 53+)

```
app/
  _layout.tsx          root layout — providers here only
  (tabs)/
    _layout.tsx        NativeTabs
    index.tsx
  (modal)/
    sheet.tsx          presentation: formSheet
```

- Route files only in `app/` — never co-locate components/utils/types
- `_layout.tsx` required in every route group; always have a route matching `/`
- kebab-case filenames: `user-profile.tsx`

```tsx
// Guarded routes
<Link href="/detail" prefetch>View</Link>

// Native sheet — prefer over custom bottom sheet libs
<Stack.Screen options={{ presentation: 'formSheet', sheetAllowedDetents: [0.5, 1.0], sheetGrabberVisible: true }} />

// NativeTabs — zero JS re-renders on tab switch
import { NativeTabs } from 'expo-router/unstable-native-tabs';
```

**RSC + EAS Update are incompatible** — do not ship RSC in production until EAS Update support lands.

---

## 10. Styling

```tsx
// New Architecture: CSS boxShadow (legacy shadow* props ignored)
<View style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }} />

// ScrollView padding — contentContainerStyle only (avoids clipping)
<ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>

// Safe area — no wrapper needed
<ScrollView contentInsetAdjustmentBehavior="automatic" />

// Apple HIG corners
<View style={{ borderRadius: 12, borderCurve: 'continuous' }} />
```

For NativeWind (Tailwind in RN): `references/nativewind.md`.

---

## 11. Anti-Pattern Hard Stops

| Anti-pattern | Fix |
|---|---|
| `runOnJS` (Reanimated 4) | `scheduleOnRN` from `react-native-worklets` |
| `estimatedItemSize` on FlashList v2 | Remove — deprecated |
| Animating `width`/`height`/layout props | `transform` + `opacity` only |
| Refs on views without `collapsable={false}` | Add `collapsable={false}` (New Architecture) |
| `useEffect` for derived state | Compute during render |
| `useEffect` for event side effects | Move to event handler |
| `useState` for scroll position | `useSharedValue` |
| `onSuccess` in `useQuery` (TanStack Query v5) | Use `useEffect` on `data` or `mutation.onSuccess` |
| `forwardRef` in function components | Plain `ref` prop (React 19) |
| `FlatList` for lists | `FlashList` v2 |
| `expo-av` | `expo-audio` + `expo-video` |
| `SafeAreaView` from `react-native` | `react-native-safe-area-context` |
| Legacy `shadow*` / `elevation` | CSS `boxShadow` |
| `Platform.OS` | `process.env.EXPO_OS` |
| `useMemo`/`useCallback` speculatively | Profiler first; compiler handles most cases |
| `{count && <Text>}` (falsy 0) | `{count > 0 && <Text>}` or ternary |
| RSC + EAS Update in production | Wait — incompatible |

---

## References

- `references/nativewind.md` — NativeWind v4/v5 setup, dark mode, gotchas, third-party interop
- `references/animations.md` — Reanimated 4: `scheduleOnRN`, CSS transitions, gestures, 120fps
- `references/state-and-effects.md` — TanStack Query, Zustand+SecureStore, Jotai, context rules
- `references/performance.md` — cold start, bundle size, FlashList tuning, EAS config
