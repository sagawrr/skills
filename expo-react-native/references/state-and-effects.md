# State & Effects

> Pinned: Zustand v5 · TanStack Query v5

---

## useEffect Replacement Map

| You want to… | Use instead |
|---|---|
| Fetch data | `useQuery` (TanStack Query) |
| Derive value from state/props | Compute during render |
| Side effect on user event | Put it in the event handler |
| Layout measurement | `onLayout` callback |
| Store subscription | `useSyncExternalStore` |
| Animated derived value | `useDerivedValue` worklet |
| State reset when ID changes | `key={id}` prop to remount |

---

## TanStack Query v5

```tsx
// Query — reactive on queryKey
const { data, isPending } = useQuery({
  queryKey: ['user', id],
  queryFn: () => api.users.get(id),
  staleTime: 60_000,
  gcTime: 5 * 60_000,   // renamed from cacheTime in v5
});

// Optimistic mutation — simple approach via mutation.variables (preferred for single-component use)
const addPost = useMutation({
  mutationFn: api.posts.create,
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['posts'] }),
});
// In JSX: {addPost.isPending && <PostItem post={addPost.variables} opacity={0.5} />}

// Optimistic mutation with full cache rollback (cross-component or server-confirmation scenarios)
const mutation = useMutation({
  mutationFn: (post: NewPost) => api.posts.create(post),
  onMutate: async (newPost) => {
    await queryClient.cancelQueries({ queryKey: ['posts'] });
    const snapshot = queryClient.getQueryData<Post[]>(['posts']);
    queryClient.setQueryData(['posts'], (old: Post[]) => [
      ...(old ?? []), { ...newPost, id: 'temp' },
    ]);
    return { snapshot };
  },
  // onError: 4 args — (error, variables, onMutateResult, context)
  // onMutateResult = return value of onMutate; context = internal MutationFunctionContext
  onError: (_, __, onMutateResult) => queryClient.setQueryData(['posts'], onMutateResult?.snapshot),
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['posts'] }),
});

// Infinite scroll + FlashList v2
// initialPageParam is required in v5 (was implicit/defaulted in v4)
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: ['feed'],
  queryFn: ({ pageParam }) => api.feed.get({ cursor: pageParam }),
  getNextPageParam: (last) => last.nextCursor ?? undefined,
  initialPageParam: null,
});
const items = data?.pages.flatMap(p => p.items) ?? [];

<FlashList
  data={items}
  onEndReached={() => { if (hasNextPage) fetchNextPage(); }}
  onEndReachedThreshold={0.5}
  ListFooterComponent={isFetchingNextPage ? <Spinner /> : null}
/>
```

---

## Zustand v5 — Breaking Changes from v4

| v4 (old) | v5 (correct) |
|---|---|
| Default import: `import create from 'zustand'` | Named: `import { create } from 'zustand'` |
| `create(fn, equalityFn)` | `createWithEqualityFn` from `'zustand/traditional'` |
| Persist auto-writes initial state to storage on creation | Initial state no longer auto-persisted; subsequent `setState` calls still persist normally |

---

## Zustand v5 — Store Shape

Colocate state and actions. Single store per app; split large apps with slices.

```tsx
import { create } from 'zustand';  // named import only in v5

interface BearState {
  count: number;
  name: string;
  increment: () => void;
  setName: (name: string) => void;
  reset: () => void;
}

const INITIAL = { count: 0, name: '' };

const useBearStore = create<BearState>()((set) => ({
  ...INITIAL,
  increment: () => set((s) => ({ count: s.count + 1 })),
  setName:   (name) => set({ name }),
  reset:     () => set(INITIAL),
}));
```

---

## Selectors — Always Subscribe to a Slice

```tsx
// ❌ subscribes to entire store — re-renders on any state change
const store = useBearStore();

// ✅ re-renders only when count changes
const count = useBearStore((s) => s.count);
const increment = useBearStore((s) => s.increment);
```

---

## `useShallow` — Object/Array Selectors

```tsx
import { useShallow } from 'zustand/shallow'; // v5 import path

// ❌ new object every render — always triggers re-render
const { count, name } = useBearStore((s) => ({ count: s.count, name: s.name }));

// ✅ shallow equality — only re-renders when count or name actually changes
const { count, name } = useBearStore(
  useShallow((s) => ({ count: s.count, name: s.name }))
);
```

---

## Auto-Generated Selectors (large stores)

```tsx
import { StoreApi, UseBoundStore } from 'zustand';

type WithSelectors<S> = S extends { getState: () => infer T }
  ? S & { use: { [K in keyof T]: () => T[K] } }
  : never;

function createSelectors<S extends UseBoundStore<StoreApi<object>>>(_store: S) {
  const store = _store as WithSelectors<typeof _store>;
  store.use = {};
  for (const k of Object.keys(store.getState())) {
    (store.use as Record<string, unknown>)[k] = () =>
      store((s) => s[k as keyof typeof s]);
  }
  return store;
}

const useBearStore = createSelectors(create<BearState>()(/* ... */));

// No selector boilerplate
const count = useBearStore.use.count();
const increment = useBearStore.use.increment();
```

---

## Slices Pattern

```tsx
import { StateCreator } from 'zustand';

interface FishSlice { fish: number; addFish: () => void; }
const createFishSlice: StateCreator<FishSlice & BearSlice, [], [], FishSlice> =
  (set) => ({ fish: 0, addFish: () => set((s) => ({ fish: s.fish + 1 })) });

interface BearSlice { bears: number; eatFish: () => void; }
const createBearSlice: StateCreator<BearSlice & FishSlice, [], [], BearSlice> =
  (set, get) => ({
    bears: 0,
    eatFish: () => set((s) => ({ fish: s.fish - 1 })),
  });

// Apply middleware at root only — not inside individual slices
const useStore = create<BearSlice & FishSlice>()((...a) => ({
  ...createBearSlice(...a),
  ...createFishSlice(...a),
}));
```

---

## Persist to SecureStore (React Native)

```tsx
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import * as SecureStore from 'expo-secure-store';

// v5: initial state no longer auto-written to storage on creation; rehydration on load still works
const useAppStore = create<AppState>()(
  persist(
    immer((set) => ({
      theme: 'dark' as 'light' | 'dark',
      setTheme: (t) => set((s) => { s.theme = t }),
    })),
    {
      name: 'app-store',
      storage: createJSONStorage(() => ({
        getItem:    SecureStore.getItemAsync,
        setItem:    SecureStore.setItemAsync,
        removeItem: SecureStore.deleteItemAsync,
      })),
      partialize: (s) => ({ theme: s.theme }), // only persist safe fields
    }
  )
);
```

---

## Read / Write Outside React

```tsx
// Read anywhere
const { count } = useBearStore.getState();

// Write anywhere (event handlers, native callbacks)
useBearStore.setState((s) => ({ count: s.count + 1 }));

// replace: true in v5 requires complete state (stricter types)
useBearStore.setState(INITIAL, true); // full replacement — must match entire state shape

// Subscribe with selector — requires subscribeWithSelector middleware
// Without it, subscribe only accepts (state, prevState) => void with no selector
import { subscribeWithSelector } from 'zustand/middleware';
const useStore = create<BearState>()(subscribeWithSelector((set) => ({ ... })));
const unsub = useStore.subscribe(
  (state) => state.count,
  (count) => console.log('count:', count)
);
```

---

## Context Injection (prop-initialized stores)

```tsx
import { createContext, useContext, useState } from 'react';
import { createStore, useStore } from 'zustand';

type CountStore = { count: number; increment: () => void };
type CountApi = ReturnType<typeof createStore<CountStore>>;
const CountCtx = createContext<CountApi | null>(null);

// useState with initializer — official Zustand pattern (guaranteed single init)
function CountProvider({ initial = 0, children }: { initial?: number; children: React.ReactNode }) {
  const [store] = useState(() =>
    createStore<CountStore>()((set) => ({
      count: initial,
      increment: () => set((s) => ({ count: s.count + 1 })),
    }))
  );
  return <CountCtx.Provider value={store}>{children}</CountCtx.Provider>;
}

function useCountStore<T>(selector: (s: CountStore) => T) {
  const store = useContext(CountCtx); // use() also works in React 19+
  if (!store) throw new Error('Missing CountProvider');
  return useStore(store, selector);
}
```

---

## Context Rules

```tsx
// Context only for stable values (auth, theme, i18n)
export function useAuth() {
  const ctx = use(AuthContext); // React 19 — works in conditionals
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}

// ❌ Fast-changing values in context re-render ALL consumers
// → Zustand selector or useSharedValue instead
```
