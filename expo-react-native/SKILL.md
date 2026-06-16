---
name: expo-react-native
description: Battle-tested Expo and React Native best practices aligned with New Architecture (Fabric/JSI/Turbo Modules), React 19+, and Expo SDK 53+. Use when building, reviewing, or refactoring any Expo or React Native codebase. Covers code patterns, state, effects, performance, and architecture — not tooling (see argent-react-native-* skills for profiling and device interaction).
---

# Expo / React Native — Hardened Patterns

## Rules Before You Write a Line

1. **New Architecture by default.** Every project should have `newArchEnabled: true` in `app.json`. Fabric renders on the native thread; JSI eliminates the JSON bridge. Never assume the old bridge.
2. **React 19 everywhere.** React 18 compat mode still compiles — doesn't mean it's correct. Use `use()`, `useTransition`, `useDeferredValue`, Suspense boundaries. Delete `useEffect` where a better primitive fits.
3. **Compiler first.** Assume React Compiler is enabled (Expo SDK 52+). Do NOT add `useCallback`/`useMemo`/`React.memo` speculatively. Add them only when the profiler proves the compiler bailed out (`react-profiler-fiber-tree` → absent `useMemoCache`).
4. **No tooling in this skill.** For device interaction, profiling, and Metro debugging see `argent-react-native-*` skills.

---

## 1. Kill useEffect — Use the Right Primitive

`useEffect` is the most misused hook. Each case below has a better replacement.

### 1a. Derived state → compute during render

```tsx
// ❌ effect to sync state
const [filtered, setFiltered] = useState(items);
useEffect(() => setFiltered(items.filter(active)), [items, active]);

// ✅ derive inline — zero lag, zero extra render
const filtered = items.filter(active);
```

### 1b. Async data → TanStack Query / SWR / React `use()`

```tsx
// ❌ useEffect data fetching — loading/error state boilerplate, race conditions
useEffect(() => {
  fetch(url).then(r => r.json()).then(setData);
}, [url]);

// ✅ TanStack Query — automatic caching, deduplication, background refresh
const { data, isPending } = useQuery({ queryKey: ['user', id], queryFn: () => fetchUser(id) });

// ✅ React 19 use() with Suspense — no loading state needed in component
const data = use(fetchUserPromise(id)); // throws Promise → Suspense catches it
```

### 1c. Event-driven side-effect → event handler, not effect

```tsx
// ❌ watches state to trigger a side-effect
useEffect(() => {
  if (submitted) sendAnalytics('form_submitted');
}, [submitted]);

// ✅ call directly in the handler — no dependency array bugs
function handleSubmit() {
  setSubmitted(true);
  sendAnalytics('form_submitted');
}
```

### 1d. Subscriptions → `useSyncExternalStore`

```tsx
// ❌ useEffect subscription with manual cleanup errors
useEffect(() => {
  const sub = store.subscribe(setState);
  return () => sub.unsubscribe();
}, []);

// ✅ built-in, concurrent-safe
const value = useSyncExternalStore(store.subscribe, store.getSnapshot);
```

### 1e. Ref/DOM mutation after render → `useLayoutEffect` or callback ref

```tsx
// ❌ layout measurement in useEffect causes visible flicker
useEffect(() => { ref.current?.measure(setSize); }, []);

// ✅ onLayout — fires synchronously with layout, no flicker
<View onLayout={e => setSize(e.nativeEvent.layout)} />
```

---

## 2. State Architecture

### 2a. Minimize state — derive everything possible

State = things that cannot be computed. If it can be derived from props or other state, it is not state.

```tsx
// ❌ three interdependent states that drift
const [items, setItems] = useState([]);
const [count, setCount] = useState(0);
const [isEmpty, setIsEmpty] = useState(true);

// ✅ one state, rest derived
const [items, setItems] = useState([]);
const count = items.length;
const isEmpty = count === 0;
```

### 2b. Server state → TanStack Query; client state → Zustand/Jotai

Never put server data into Redux or useState. Server state has its own lifecycle (loading, stale, refetch).

```tsx
// Client global state — Zustand (tiny, no boilerplate)
const useStore = create<State>()(
  immer((set) => ({
    theme: 'dark',
    setTheme: (t) => set(s => { s.theme = t }),
  }))
);
```

### 2c. Context is not a state manager — it is a dependency injector

```tsx
// ❌ updating context on every keystroke re-renders all consumers
const [search, setSearch] = useState('');
<SearchContext.Provider value={{ search, setSearch }}>

// ✅ split stable values (theme, auth) from frequently-updating values
// Frequently-updating values: keep local or in Zustand
```

### 2d. Updater form for state that depends on previous value

```tsx
// ❌ closure stale bug in concurrent mode
setCount(count + 1);

// ✅ always safe
setCount(c => c + 1);
```

---

## 3. React 19 Patterns

### 3a. `useTransition` for non-urgent updates

```tsx
const [isPending, startTransition] = useTransition();

function handleSearch(text: string) {
  setInputValue(text); // urgent — updates input immediately
  startTransition(() => setSearchQuery(text)); // deferred — can be interrupted
}
```

### 3b. `useDeferredValue` for expensive derived renders

```tsx
const deferredQuery = useDeferredValue(query);
// Pass deferredQuery to the heavy list — it renders stale during typing
const results = useMemo(() => heavyFilter(items, deferredQuery), [items, deferredQuery]);
```

### 3c. `use()` for resources in render

```tsx
// Wrap in Suspense + ErrorBoundary above
function Profile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise); // suspends until resolved
  return <Text>{user.name}</Text>;
}
```

### 3d. `useOptimistic` for instant UI feedback

```tsx
const [optimisticLikes, addOptimisticLike] = useOptimistic(likes, (cur, inc) => cur + inc);

async function handleLike() {
  addOptimisticLike(1); // instant
  await likePost(id);   // real
}
```

---

## 4. Performance — Code Patterns

### 4a. FlashList over FlatList — always

```tsx
import { FlashList } from '@shopify/flash-list';

<FlashList
  data={items}
  renderItem={({ item }) => <ItemRow item={item} />}
  estimatedItemSize={72}      // measure a real item, not a guess
  keyExtractor={item => item.id}
/>
```

Rules for list items:
- Pass primitives (id, title, imageUrl) not full objects when possible
- `ItemRow` must be a stable component — no inline arrow functions as props
- Never create objects/arrays inline in `renderItem`

### 4b. Scroll position → shared value, never state

```tsx
// ❌ setState on scroll = re-render at 60fps
const [scrollY, setScrollY] = useState(0);
onScroll={e => setScrollY(e.nativeEvent.contentOffset.y)}

// ✅ Reanimated shared value — lives on UI thread
const scrollY = useSharedValue(0);
const scrollHandler = useAnimatedScrollHandler(e => { scrollY.value = e.contentOffset.y; });
```

### 4c. Animations — UI thread only

```tsx
// ✅ Only animate transform and opacity (GPU-composited)
const animatedStyle = useAnimatedStyle(() => ({
  transform: [{ translateY: withSpring(offset.value) }],
  opacity: withTiming(visible.value ? 1 : 0),
}));

// ❌ Never animate: width, height, top, left, margin, padding
// These trigger layout recalculation on every frame
```

### 4d. `useDerivedValue` over `useAnimatedReaction`

```tsx
// ❌ useAnimatedReaction runs a worklet reaction (more overhead)
useAnimatedReaction(() => scrollY.value, (v) => { header.value = v > 100; });

// ✅ derive directly — zero overhead
const headerVisible = useDerivedValue(() => scrollY.value > 100);
```

### 4e. Gesture Handler v2 — Gesture.Tap over Pressable for animations

```tsx
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

const tap = Gesture.Tap()
  .onBegin(() => { scale.value = withSpring(0.95); })
  .onFinalize(() => { scale.value = withSpring(1); });

<GestureDetector gesture={tap}>
  <Animated.View style={animatedStyle}>{children}</Animated.View>
</GestureDetector>
```

### 4f. Images — expo-image always

```tsx
import { Image } from 'expo-image';

<Image
  source={{ uri: url }}
  placeholder={blurhash}      // show while loading
  contentFit="cover"
  transition={200}
  recyclingKey={item.id}      // critical for list reuse
/>
```

Never: `<Image>` from react-native, `<img>`, FastImage (deprecated).

---

## 5. New Architecture Patterns

### 5a. Turbo Modules — typed native modules

```tsx
// Always use the NativeModules typed interface, not the bridge
import NativeMyModule from './specs/NativeMyModule'; // codegen spec
NativeMyModule.doWork(arg);  // synchronous JSI call, no serialization
```

### 5b. Fabric — avoid `findNodeHandle` and legacy refs

```tsx
// ❌ findNodeHandle is bridge-era, undefined in Fabric
const handle = findNodeHandle(ref.current);

// ✅ use ref directly or onLayout callback
<View onLayout={e => { /* use e.nativeEvent.layout */ }} />
```

### 5c. Concurrent features require Suspense boundaries

New Architecture enables concurrent rendering. Wrap async trees:

```tsx
<ErrorBoundary fallback={<ErrorScreen />}>
  <Suspense fallback={<Skeleton />}>
    <DataDrivenScreen />
  </Suspense>
</ErrorBoundary>
```

---

## 6. Expo SDK 53 Patterns

### 6a. Expo Router v4 — file conventions

```
app/
  _layout.tsx         root layout, wrap with providers here
  (tabs)/
    _layout.tsx       NativeTabs
    index.tsx
    search.tsx
  (modal)/
    confirm.tsx       presentation: 'formSheet'
```

- Never co-locate components/utils in `app/` — only route files
- Use group routes `(name)` to share stacks across tabs
- `process.env.EXPO_OS` not `Platform.OS` (tree-shakeable at build time)

### 6b. NativeTabs — prefer over JS tabs

```tsx
import { NativeTabs } from 'expo-router/unstable-native-tabs';

// Renders native UITabBarController (iOS) / BottomNavigationView (Android)
// Zero JS re-renders on tab switch
```

### 6c. Native modals over JS bottom sheets

```tsx
// Use formSheet presentation — native iOS sheet with detents
<Stack.Screen options={{
  presentation: 'formSheet',
  sheetAllowedDetents: [0.5, 1.0],
  sheetGrabberVisible: true,
}} />
```

### 6d. EAS Update strategy

- Use `channel` per environment: `preview`, `production`
- Never ship a full rebuild for JS-only changes — use `eas update`
- Pin `expo` SDK version in `eas.json` build profiles

---

## 7. Anti-Patterns — Hard Stops

| Anti-pattern | Replacement |
|---|---|
| `useEffect` for data fetch | TanStack Query / `use()` |
| `useEffect` to sync state | Derive during render |
| `useState` for scroll position | `useSharedValue` |
| `TouchableOpacity` | `Pressable` |
| `AsyncStorage` for sensitive data | `expo-secure-store` |
| `Dimensions.get()` | `useWindowDimensions()` |
| `Platform.OS` | `process.env.EXPO_OS` |
| Inline style objects in list items | Hoisted `StyleSheet.create` |
| `React.memo` / `useMemo` speculatively | Let React Compiler handle it |
| `useContext` for fast-changing values | Zustand atom / shared value |
| `FlatList` for any list | `FlashList` |
| `expo-av` | `expo-audio` + `expo-video` separately |
| `SafeAreaView` from RN | `react-native-safe-area-context` |
| Custom fonts via JS | Expo config plugin (compile-time) |
| `img` / `div` elements | `expo-image` / `View` |
| Falsy `&&` with number/string | Ternary or `!!` cast |

---

## 8. TypeScript Patterns

```tsx
// Strongly type navigation params — never use `any` for route params
type RootStackParamList = {
  Profile: { userId: string };
  Settings: undefined;
};

// Process.env type safety with Expo
declare module 'process' {
  global { namespace NodeJS { interface ProcessEnv { EXPO_OS: 'ios' | 'android' | 'web' } } }
}

// Discriminated unions over optional props
type CardProps =
  | { variant: 'image'; imageUri: string; title: string }
  | { variant: 'text'; body: string };
```

---

## References

For deeper patterns on specific areas:

- `references/state-and-effects.md` — full useEffect replacement catalog, Zustand patterns, React Query patterns
- `references/performance.md` — bundle optimization, cold start, FlashList tuning, memory leaks
- Related skills: `vercel-react-native-skills` (list/animation rules), `building-native-ui` (Expo Router UI), `argent-react-native-optimization` (profiling pipeline)
