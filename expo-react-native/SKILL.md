---
name: expo-react-native
description: Battle-tested code patterns pinned to Expo SDK 56 (RN 0.85.2, React 19.2.3, Hermes v1), Reanimated 4, FlashList v2, NativeWind v4, Zustand v5, Zod v4, React Hook Form v7. Use when writing, reviewing, or refactoring React Native component code. Covers hooks, state, animations, lists, images, forms, and styling — not build config or tooling.
---

# Expo / React Native — Hardened Patterns

> Pinned: Expo SDK 56 · RN 0.85.2 · React 19.2.3 · Reanimated 4 · FlashList v2 · NativeWind v4 · Zustand v5 · Zod v4 · RHF v7

## Ground Rules

1. **New Architecture is default** (RN 0.76+, Expo SDK 53+). Two silent breakage patterns:
   - Auto state-batching drops intermediate values — components relying on them break silently
   - View flattening makes refs null — add `collapsable={false}` to every `<View ref={...}>`
2. **`StyleSheet.absoluteFillObject` removed in RN 0.85** — use `StyleSheet.absoluteFill`
3. **Expo Router SDK 56**: forks React Navigation — `@react-navigation/*` is no longer a peer dep of `expo-router`. Run the codemod after upgrading.
4. **React 19 in SDK 56** — `use()`, `useTransition`, `useOptimistic`. `ref` is now a plain prop; `forwardRef` still works but not needed for new components.
5. **React Compiler (SDK 54+)** — handles most memoization. Don't add `useMemo`/`useCallback` without profiler evidence of bail-out (`useMemoCache` absent in fiber tree = bailed out).
6. **Reanimated 4 (requires New Architecture)** — `scheduleOnRN` is preferred over `runOnJS`. Layout props can now animate with the native driver (Shared Animation Backend). See `references/animations.md`.
7. **Profile before optimizing** — measure first, fix one thing, re-measure.

---

## 1. useEffect — 3 Legitimate Uses

Valid: (1) subscribing to an external system, (2) imperative native call after mount with cleanup, (3) synchronizing two external systems.

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
useEffect(() => { if (submitted) analytics.track('submitted'); }, [submitted]);

// ✅ in the handler
async function handleSubmit() { await submit(data); analytics.track('submitted'); }

// use() — promise must be stable (created outside render)
function Profile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise); // wrap parent in <Suspense> + <ErrorBoundary>
  return <Text>{user.name}</Text>;
}
```

---

## 2. State — Zustand v5

```tsx
// Named imports only in v5 — no default exports
import { create } from 'zustand';
import { useShallow } from 'zustand/react/shallow';

// ✅ Selector — re-renders only when subscribed slice changes
const count = useStore((s) => s.count);

// ✅ useShallow — when selector returns object/array (prevents re-render on same shallow values)
const { count, name } = useStore(useShallow((s) => ({ count: s.count, name: s.name })));

// Context for stable values (auth, theme) — use() in React 19
const user = use(AuthContext); // works in conditionals; useContext does not
```

See `references/state-and-effects.md` for full Zustand v5 patterns, slices, persist.

---

## 3. React 19

```tsx
const [isPending, startTransition] = useTransition();
startTransition(() => setSearchQuery(text)); // interruptible

const [likes, addOptimistic] = useOptimistic(serverLikes, (cur, inc) => cur + inc);
async function handleLike() { addOptimistic(1); await likePost(id); }

// ref is a plain prop in React 19
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
  keyExtractor={item => item.id}
  getItemType={item => item.type}   // required for heterogeneous lists
  onEndReached={fetchNextPage}
  onEndReachedThreshold={0.5}
  // estimatedItemSize / estimatedListSize / estimatedFirstItemOffset — ALL removed in v2
  // masonry layout (replaces standalone MasonryFlashList):
  // masonry numColumns={2}
/>
```

- `renderItem` must be a stable reference — no inline arrow functions
- `recyclingKey={item.id}` on every `expo-image` inside list items
- Never use `index` as `keyExtractor` — breaks recycler identity
- `MasonryFlashList` no longer exists — use `<FlashList masonry numColumns={2} />`

---

## 5. Animations — Reanimated 4

See `references/animations.md`. Core rules:
- Animate **only** `transform` + `opacity` — layout props can now also be animated via the Shared Animation Backend (RN 0.85+)
- Scroll position → `useSharedValue`, never `useState`
- `scheduleOnRN` preferred over `runOnJS` for calling JS from a worklet
- CSS transitions: `style={{ transition: { opacity: { duration: 300 } }, opacity: isVisible ? 1 : 0 }}`

---

## 6. Forms — RHF v7 + Zod v4

See `references/forms.md`. Core rules:
- **`useController`** always in RN — `register()` doesn't work on `TextInput`
- **Zod v4**: format validators are now top-level: `z.email()`, `z.url()`, `z.uuid()` (not `z.string().email()`)
- **`z.coerce.number()`** for numeric TextInput values (TextInput always returns strings)
- `formState` is a Proxy — read sub-properties unconditionally, never conditionally

---

## 7. Images

```tsx
import { Image } from 'expo-image';
<Image source={{ uri }} placeholder={{ blurhash }} contentFit="cover" transition={200} recyclingKey={item.id} />
```

---

## 8. Library Preferences

| Use | Not |
|-----|-----|
| `expo-audio` | `expo-av` for audio |
| `expo-video` | `expo-av` for video |
| `expo-image` | `react-native` Image, FastImage |
| `expo-image source="sf:name"` | `expo-symbols`, `@expo/vector-icons` |
| `react-native-safe-area-context` | `SafeAreaView` from `react-native` |
| `process.env.EXPO_OS` | `Platform.OS` |
| `React.use(Context)` | `useContext(Context)` |
| `useWindowDimensions()` | `Dimensions.get()` |
| `expo-secure-store` | AsyncStorage for secrets |
| `Pressable` | `TouchableOpacity`, `TouchableHighlight` |
| `StyleSheet.absoluteFill` | `StyleSheet.absoluteFillObject` (removed in RN 0.85) |

---

## 9. SDK / RN Breaking Changes by Version

| Version | Key code-level changes |
|---|---|
| RN 0.85 | `StyleSheet.absoluteFillObject` removed; layout props animatable with native driver |
| Expo SDK 56 | RN 0.85.2 + React 19.2.3; Expo Router forks React Navigation (codemod required) |
| Expo SDK 55 | `expo-av` → `expo-audio` + `expo-video` |
| Expo SDK 54 | React Compiler available; `react-native-worklets` required for Reanimated |

---

## 10. Expo Router (SDK 56)

```
app/
  _layout.tsx          root layout — providers only
  (tabs)/_layout.tsx   NativeTabs
  (modal)/sheet.tsx    presentation: formSheet
```

- **SDK 56**: import from `expo-router` directly — `@react-navigation/native` no longer available via `expo-router`'s deps
- Route files only in `app/`; components/hooks/types in `components/`/`hooks/`/`types/`
- kebab-case filenames; `_layout.tsx` in every route group

```tsx
<Link href="/detail" prefetch>View</Link>

import { NativeTabs } from 'expo-router/unstable-native-tabs'; // zero JS re-renders on tab switch

<Stack.Screen options={{ presentation: 'formSheet', sheetAllowedDetents: [0.5, 1.0] }} />
```

---

## 11. Styling

```tsx
<View style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }} />  // legacy shadow* ignored
<ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
<ScrollView contentInsetAdjustmentBehavior="automatic" />
<View style={{ borderRadius: 12, borderCurve: 'continuous' }} />
<Text style={{ fontVariant: ['tabular-nums'] }}>{price}</Text>
<Text selectable>{address}</Text>
```

For NativeWind v4: `references/nativewind.md`.

---

## 12. Hard Stops

| ❌ | ✅ |
|---|---|
| `StyleSheet.absoluteFillObject` | `StyleSheet.absoluteFill` |
| `z.string().email()` (Zod v4) | `z.email()` |
| `z.string().url()` (Zod v4) | `z.url()` |
| `z.record(z.string())` (Zod v4) | `z.record(z.string(), z.string())` |
| `z.nativeEnum(MyEnum)` (Zod v4) | `z.enum(MyEnum)` |
| `invalid_type_error` / `required_error` (Zod v4) | unified `error` param |
| Default import from `'zustand'` (v5) | Named: `import { create } from 'zustand'` |
| `create(fn, equalityFn)` (Zustand v5) | `createWithEqualityFn` from `'zustand/traditional'` |
| `MasonryFlashList` | `<FlashList masonry numColumns={N} />` |
| `estimatedItemSize` on FlashList v2 | Remove — all size props deprecated |
| Refs on `<View>` without `collapsable={false}` | `<View ref={r} collapsable={false}>` |
| `useEffect` for derived state | Compute during render |
| `register()` on RN TextInput | `useController` / `Controller` |
| `watch()` at form root | `useWatch({ control, name })` |
| `mode: 'onChange'` in RHF | `mode: 'onBlur'` |
| `useMemo`/`useCallback` without profiler evidence | Let React Compiler handle it |
| `{count && <Text>}` where count can be 0 | `{count > 0 && <Text>}` |
| RSC + EAS Update in production | EAS Update is incompatible with RSC |

---

## References

- `references/forms.md` — RHF v7 + Zod v4: useController, formState Proxy, Zod v4 API changes
- `references/animations.md` — Reanimated 4: scheduleOnRN, CSS transitions, Shared Animation Backend
- `references/state-and-effects.md` — TanStack Query, Zustand v5 (slices, persist, selectors)
- `references/performance.md` — FlashList v2 tuning, Hermes, bundle, memory
- `references/nativewind.md` — NativeWind v4 patterns, dark mode, CSS vars
