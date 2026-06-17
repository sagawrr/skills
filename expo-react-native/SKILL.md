---
name: expo-react-native
description: Battle-tested Expo and React Native patterns verified against official sources (React Native 0.78+, Expo SDK 53–56, Reanimated 4, FlashList v2). Use when building, reviewing, or refactoring any Expo or React Native codebase. Covers code patterns, state, effects, performance, and architecture — not device interaction or profiling (see argent-react-native-* skills for those).
---

# Expo / React Native — Hardened Patterns

> Sources: reactnative.dev, expo.dev/changelog, shopify.engineering/flashlist-v2, react.dev, software-mansion-labs/skills, callstackincubator/agent-skills, expo/skills

## Ground Rules

1. **New Architecture is the default.** RN 0.76+ and Expo SDK 53+ ship with it on. Enabling it does not automatically improve performance — you must use concurrent features and synchronous layout effects for gains.
2. **React 19 is shipping now.** RN 0.78 (Feb 2025) + Expo SDK 53/54. Use `use()`, `useTransition`, `useOptimistic`. Function components no longer need `forwardRef`.
3. **React Compiler: SDK 54+ auto-configures.** Add `"experiments": { "reactCompiler": true }` to `app.json` — no Babel setup needed. It runs on app code only (not node_modules), is disabled during server rendering, and handles conditional memoization after early returns (impossible with manual hooks). Do NOT add `useMemo`/`useCallback`/`React.memo` speculatively — use the profiler to confirm compiler bail-out first.
4. **Reanimated 4 is the current target.** `runOnJS` is removed. Use `scheduleOnRN(fn, ...args)` from `react-native-worklets` instead. Install `react-native-worklets` (required peer dep in SDK 54+).
5. **Measure before optimizing.** Measure → fix one thing → re-measure → validate. Do not suggest `useMemo`/`useCallback` changes without profiler evidence.

---

## 1. Kill useEffect — Use the Right Primitive

`useEffect` has exactly three legitimate uses: (1) subscribing to an external system with no `useSyncExternalStore` interface, (2) triggering imperative native code after mount with cleanup, (3) synchronizing two external systems. Everything else has a better primitive.

### 1a. Derived state → compute during render

```tsx
// ❌ effect syncing state — extra render, stale frame
const [filtered, setFiltered] = useState(items);
useEffect(() => setFiltered(items.filter(active)), [items, active]);

// ✅ compute inline — zero lag, zero extra render
const filtered = items.filter(active);
```

### 1b. Async data → TanStack Query

```tsx
// ❌ useEffect fetch — race conditions, no caching, manual loading state
useEffect(() => { fetch(url).then(r => r.json()).then(setData); }, [url]);

// ✅ TanStack Query — caching, deduplication, background refresh
const { data, isPending } = useQuery({
  queryKey: ['user', id],
  queryFn: () => fetchUser(id),
  staleTime: 60_000,
});
```

### 1c. React 19 `use()` with Suspense

```tsx
// Promises must be created OUTSIDE render (stable reference required)
// ✅ correct — promise created in parent, passed as prop
function Profile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise); // suspends until resolved
  return <Text>{user.name}</Text>;
}

// Wrap with Suspense + ErrorBoundary
<ErrorBoundary fallback={<ErrorScreen />}>
  <Suspense fallback={<Skeleton />}>
    <Profile userPromise={stablePromise} />
  </Suspense>
</ErrorBoundary>
```

### 1d. Context → `React.use` (React 19)

```tsx
// ❌ old
const theme = useContext(ThemeContext);

// ✅ React 19 — same result, works in conditions and loops
const theme = use(ThemeContext);
```

### 1e. Event side-effect → put in handler, not effect

```tsx
// ❌ watches state to fire analytics
useEffect(() => { if (submitted) sendAnalytics('form_submitted'); }, [submitted]);

// ✅ fire directly in handler — no dependency array bugs
function handleSubmit() {
  setSubmitted(true);
  sendAnalytics('form_submitted');
}
```

### 1f. External store → `useSyncExternalStore`

```tsx
const value = useSyncExternalStore(store.subscribe, store.getSnapshot);
```

### 1g. Layout measurement → `onLayout`, not `useEffect`

```tsx
// ❌ useEffect measure causes a visible flicker frame
useEffect(() => { ref.current?.measure(setSize); }, []);

// ✅ onLayout fires synchronously with layout
<View onLayout={e => setSize(e.nativeEvent.layout)} />
```

---

## 2. State Architecture

### 2a. Minimize state — derive everything possible

```tsx
// ❌
const [items, setItems] = useState([]);
const [count, setCount] = useState(0);
const [isEmpty, setIsEmpty] = useState(true);

// ✅
const [items, setItems] = useState([]);
const count = items.length;
const isEmpty = count === 0;
```

### 2b. Server state → TanStack Query; client global state → Zustand/Jotai

Never put server data in Redux or `useState`. Server state has its own lifecycle.

```tsx
// Zustand — atomic client state
const useStore = create<State>()(
  immer((set) => ({
    theme: 'dark',
    setTheme: (t) => set(s => { s.theme = t }),
  }))
);
const theme = useStore(s => s.theme); // selector — subscribe to a slice only
```

### 2c. Context = dependency injection, not state manager

```tsx
// ❌ context with fast-changing values re-renders all consumers
<SearchContext.Provider value={{ search, setSearch }}>

// ✅ context for stable values only (auth, theme)
// Fast-changing values → Zustand atom or useSharedValue
```

### 2d. Updater form for state depending on previous value

```tsx
setCount(c => c + 1); // always safe in concurrent mode
```

---

## 3. React 19 Patterns

### 3a. `useTransition` — non-urgent updates

```tsx
const [isPending, startTransition] = useTransition();
function handleSearch(text: string) {
  setInputValue(text); // urgent — updates input immediately
  startTransition(() => setSearchQuery(text)); // deferred — interruptible
}
```

### 3b. `useDeferredValue` — expensive derived renders

```tsx
const deferredQuery = useDeferredValue(query);
// Heavy list renders stale while typing — no jank on input
```

### 3c. `useOptimistic` — instant UI feedback

```tsx
const [optimisticLikes, addOptimistic] = useOptimistic(likes, (cur, inc) => cur + inc);
async function handleLike() {
  addOptimistic(1);  // instant
  await likePost(id); // real
}
```

### 3d. `forwardRef` no longer needed in function components (React 19)

```tsx
// ❌ old
const Input = forwardRef<TextInput, Props>((props, ref) => <TextInput ref={ref} {...props} />);

// ✅ React 19 — ref is a plain prop
function Input({ ref, ...props }: Props & { ref?: Ref<TextInput> }) {
  return <TextInput ref={ref} {...props} />;
}
```

---

## 4. Lists — FlashList v2

FlashList v2 uses New Architecture synchronous layout measurement — no size estimation required.

```tsx
import { FlashList } from '@shopify/flash-list';

<FlashList
  data={items}
  renderItem={({ item }) => <ItemRow item={item} />}
  keyExtractor={item => item.id}
  // v2: estimatedItemSize is DEPRECATED — do NOT add it
  getItemType={item => item.type}   // heterogeneous lists — enables recycling optimization
  onEndReached={fetchNextPage}
  onEndReachedThreshold={0.5}
/>
```

**FlashList item rules:**
- Item component must be stable — no inline arrow functions as renderItem props
- Never create objects/arrays inline in `renderItem`
- Pass primitives (id, title, imageUri) not full objects when possible
- Set `recyclingKey` on `expo-image` inside list items — prevents old image flash on scroll

**FlatList**: valid fallback if not yet on New Architecture. ScrollView rendering all items is always wrong for lists > 20 items.

---

## 5. Animations — Reanimated 4

> See `references/animations.md` for full patterns.

### 5a. `runOnJS` is removed — use `scheduleOnRN`

```tsx
import { scheduleOnRN } from 'react-native-worklets';

// ❌ Reanimated 4 — runOnJS does not exist
const handler = useAnimatedScrollHandler({
  onScroll: (e) => { runOnJS(onScroll)(e.contentOffset.y); }, // CRASH
});

// ✅
const handler = useAnimatedScrollHandler({
  onScroll: (e) => {
    scrollY.value = e.contentOffset.y;
    if (e.contentOffset.y > 100) scheduleOnRN(onScrollPast100);
  },
});
```

### 5b. Scroll position → shared value, never state

```tsx
const scrollY = useSharedValue(0);
const scrollHandler = useAnimatedScrollHandler(e => {
  scrollY.value = e.contentOffset.y;
});
```

### 5c. Animate only GPU-composited properties

```tsx
// ✅ transform + opacity — no layout recalculation
const style = useAnimatedStyle(() => ({
  transform: [{ translateY: withSpring(offset.value) }],
  opacity: withTiming(visible.value ? 1 : 0),
}));
// ❌ Never animate: width, height, top, left, margin, padding
```

### 5d. CSS transitions (Reanimated 4 — New Architecture only)

```tsx
// Reanimated 4 exposes CSS-like transition API
import Animated from 'react-native-reanimated';

<Animated.View style={{ transition: { opacity: { duration: 300 } }, opacity: visible ? 1 : 0 }} />
```

### 5e. `useDerivedValue` over `useAnimatedReaction` for derived state

```tsx
const headerVisible = useDerivedValue(() => scrollY.value > 100);
```

---

## 6. Images

```tsx
import { Image } from 'expo-image';

<Image
  source={{ uri: url }}
  placeholder={{ blurhash }}
  contentFit="cover"
  transition={200}
  recyclingKey={item.id}   // REQUIRED inside FlashList items
/>
```

Never: `Image` from `react-native`, `img` element, FastImage.

---

## 7. Expo SDK & Router Patterns

### 7a. SDK versioned breaking changes

| SDK | Change |
|-----|--------|
| 53 | New Architecture default; Expo Router v4; RN 0.79 + React 19 |
| 54 | React Compiler auto-configured (`"experiments": { "reactCompiler": true }`); `react-native-worklets` required |
| 55 | NativeTabs changes; `expo-av` → `expo-audio` + `expo-video` |
| 56 | `@react-navigation/*` imports → `expo-router` entry points |

### 7b. Library preferences (hard rules)

| Use | Never use |
|-----|-----------|
| `expo-audio` | `expo-av` for audio |
| `expo-video` | `expo-av` for video |
| `expo-image` | `react-native` Image, `img`, FastImage |
| `expo-image` `source="sf:name"` | `expo-symbols`, `@expo/vector-icons` |
| `react-native-safe-area-context` | `SafeAreaView` from `react-native` |
| `process.env.EXPO_OS` | `Platform.OS` (not tree-shakeable) |
| `React.use(Context)` | `useContext(Context)` |
| `useWindowDimensions()` | `Dimensions.get()` |
| CSS `boxShadow` prop | Legacy `shadow*` or `elevation` props |
| Flexbox | `Dimensions` API for layouts |

### 7c. Expo Router v4 new features (SDK 53+)

```tsx
// Guarded route groups — protect authenticated routes
// app/(protected)/_layout.tsx
export { guard } from './guard'; // redirects unauthenticated users

// Route prefetching
<Link href="/detail" prefetch>View Detail</Link>
// or imperative
router.prefetch('/detail');

// Build-time redirects (app.json)
{
  "expo": {
    "router": {
      "redirects": [{ "source": "/old", "destination": "/new" }]
    }
  }
}
```

### 7d. File conventions

```
app/
  _layout.tsx          root layout — wrap providers here only
  (tabs)/
    _layout.tsx        NativeTabs
    index.tsx
  (modal)/
    sheet.tsx          presentation: 'formSheet'
```

- Never co-locate components/utils/types in `app/` — only route files
- `_layout.tsx` must exist in every route group
- Always have a route matching `/`
- kebab-case filenames: `user-profile.tsx` not `UserProfile.tsx`

### 7e. NativeTabs over JS tabs

```tsx
import { NativeTabs } from 'expo-router/unstable-native-tabs';
// Renders UITabBarController (iOS) / BottomNavigationView (Android)
// Zero JS re-renders on tab switch
```

### 7f. Native modals over custom bottom sheets

```tsx
<Stack.Screen options={{
  presentation: 'formSheet',
  sheetAllowedDetents: [0.5, 1.0],
  sheetGrabberVisible: true,
  contentStyle: { backgroundColor: 'transparent' }, // liquid glass on iOS 26+
}} />
```

### 7g. RSC — not production-ready

React Server Components in Expo Router are experimental. **EAS Update (OTA) is incompatible with RSC.** Do not ship RSC in production until EAS Update support lands.

### 7h. Try Expo Go first

Before running `npx expo run:ios/android`, verify the feature works in Expo Go (`npx expo start`). Custom builds are only required for: local Expo modules, Apple targets/widgets, third-party native modules not in Expo Go, or custom native config.

---

## 8. Styling Rules

```tsx
// ❌ Legacy shadows — ignored on New Architecture
shadow={{ color: '#000', radius: 4, opacity: 0.2 }}
elevation={4}

// ✅ CSS boxShadow — works on New Architecture
<View style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }} />

// Inset shadows supported
<View style={{ boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.06)' }} />

// ScrollView — always contentContainerStyle for padding (not style)
<ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>

// Safe area — contentInsetAdjustmentBehavior, not SafeAreaView wrapper
<ScrollView contentInsetAdjustmentBehavior="automatic" />

// Continuous border radius (Apple HIG)
<View style={{ borderRadius: 12, borderCurve: 'continuous' }} />

// Tabular numbers for counters
<Text style={{ fontVariant: ['tabular-nums'] }}>{count}</Text>

// Selectable text for data the user might want to copy
<Text selectable>{address}</Text>
```

---

## 9. TypeScript Patterns

```tsx
// Expo env vars — typed
declare global { namespace NodeJS { interface ProcessEnv { EXPO_OS: 'ios' | 'android' | 'web' } } }

// Path aliases — always over relative imports
// tsconfig.json: { "paths": { "@/*": ["./src/*"] } }
import { Button } from '@/components/Button'; // ✅
import { Button } from '../../../components/Button'; // ❌

// Discriminated unions over optional props — compiler enforces completeness
type CardProps =
  | { variant: 'image'; imageUri: string; title: string }
  | { variant: 'text'; body: string };
```

---

## 10. Anti-Pattern Hard Stops

| Anti-pattern | Replacement |
|---|---|
| `useEffect` for data fetch | TanStack Query / `use()` |
| `useEffect` to sync state | Derive during render |
| `useState` for scroll position | `useSharedValue` |
| `runOnJS` (Reanimated 4) | `scheduleOnRN` from `react-native-worklets` |
| `estimatedItemSize` on FlashList v2 | Remove — deprecated, auto-handled |
| `TouchableOpacity` | `Pressable` |
| `AsyncStorage` for secrets | `expo-secure-store` |
| `Dimensions.get()` | `useWindowDimensions()` |
| `Platform.OS` | `process.env.EXPO_OS` |
| `useContext(X)` | `use(X)` (React 19) |
| Inline style objects in list items | Hoisted `StyleSheet.create` or stable const |
| `useMemo`/`useCallback` speculatively | Let React Compiler handle it; verify with profiler |
| `FlatList` for any list | `FlashList` (v2 on New Architecture) |
| `expo-av` | `expo-audio` + `expo-video` separately |
| `SafeAreaView` from `react-native` | `react-native-safe-area-context` |
| Legacy `shadow*`/`elevation` props | CSS `boxShadow` prop |
| `forwardRef` in function components | Plain `ref` prop (React 19) |
| Barrel imports `import { X } from 'lib'` | Direct path `import X from 'lib/X'` |
| RSC in production with EAS Update | Wait — EAS Update is incompatible |
| `img` / `div` elements | `expo-image` / `View` |
| Falsy `&&` with number or string | Ternary or `!!` cast |

---

## References

- `references/state-and-effects.md` — full useEffect replacement catalog, TanStack Query patterns, Zustand/Jotai
- `references/animations.md` — Reanimated 4 full guide, CSS transitions, layout animations, 120fps
- `references/performance.md` — cold start, bundle size, FlashList tuning, memory leaks, EAS config
- Related skills: `vercel-react-native-skills` (list/animation rules), `building-native-ui` (Expo Router UI), `argent-react-native-optimization` (profiling pipeline)
