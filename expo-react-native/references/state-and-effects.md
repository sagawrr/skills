# State & Effects

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

## TanStack Query

```tsx
// Query — reactive on queryKey changes
const { data, isPending } = useQuery({
  queryKey: ['user', id],
  queryFn: () => api.users.get(id),
  staleTime: 60_000,   // serve from cache if fresh < 1min
  gcTime: 5 * 60_000,  // keep in cache 5min after unmount
});

// Optimistic mutation — rollback on error
const mutation = useMutation({
  mutationFn: (post: NewPost) => api.posts.create(post),
  onMutate: async (newPost) => {
    await queryClient.cancelQueries({ queryKey: ['posts'] });
    const snapshot = queryClient.getQueryData<Post[]>(['posts']);
    queryClient.setQueryData(['posts'], (old: Post[]) => [
      ...(old ?? []),
      { ...newPost, id: 'temp' },
    ]);
    return { snapshot };
  },
  onError: (_, __, ctx) => queryClient.setQueryData(['posts'], ctx?.snapshot),
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['posts'] }),
});

// Infinite scroll + FlashList
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: ['feed'],
  queryFn: ({ pageParam }) => api.feed.get({ cursor: pageParam }),
  getNextPageParam: (last) => last.nextCursor ?? undefined,
  initialPageParam: null as string | null,
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

## Zustand

### Store shape — colocate state and actions

```tsx
import { create } from 'zustand';

interface BearState {
  count: number;
  name: string;
  increment: () => void;
  setName: (name: string) => void;
  reset: () => void;
}

const INITIAL: Pick<BearState, 'count' | 'name'> = { count: 0, name: '' };

const useBearStore = create<BearState>()((set) => ({
  ...INITIAL,
  increment: () => set((s) => ({ count: s.count + 1 })),
  setName:   (name) => set({ name }),
  reset:     () => set(INITIAL),
}));
```

### Selectors — always subscribe to a slice, not the whole store

```tsx
// ❌ subscribes to entire store — re-renders on any state change
const store = useBearStore();

// ✅ re-renders only when count changes
const count = useBearStore((s) => s.count);
const increment = useBearStore((s) => s.increment);
```

### useShallow — when selector returns a new object/array each time

```tsx
import { useShallow } from 'zustand/react/shallow';

// ❌ new array on every render — causes re-render even if values didn't change
const [count, name] = useBearStore((s) => [s.count, s.name]);

// ✅ shallow equality check — only re-renders when count or name actually changes
const { count, name } = useBearStore(useShallow((s) => ({ count: s.count, name: s.name })));
```

### Auto-generated selectors (large stores)

```tsx
import { StoreApi, UseBoundStore } from 'zustand';

type WithSelectors<S> = S extends { getState: () => infer T }
  ? S & { use: { [K in keyof T]: () => T[K] } }
  : never;

function createSelectors<S extends UseBoundStore<StoreApi<object>>>(_store: S) {
  const store = _store as WithSelectors<typeof _store>;
  store.use = {};
  for (const k of Object.keys(store.getState())) {
    (store.use as Record<string, unknown>)[k] = () => store((s) => s[k as keyof typeof s]);
  }
  return store;
}

const useBearStore = createSelectors(create<BearState>()(/* ... */));

// Usage — no selector boilerplate
const count = useBearStore.use.count();
const increment = useBearStore.use.increment();
```

### Slices pattern (large app)

```tsx
import { StateCreator } from 'zustand';

// Fish slice
interface FishSlice { fish: number; addFish: () => void; }
const createFishSlice: StateCreator<FishSlice & BearSlice, [], [], FishSlice> =
  (set) => ({ fish: 0, addFish: () => set((s) => ({ fish: s.fish + 1 })) });

// Bear slice
interface BearSlice { bears: number; addBear: () => void; eatFish: () => void; }
const createBearSlice: StateCreator<BearSlice & FishSlice, [], [], BearSlice> =
  (set, get) => ({
    bears: 0,
    addBear: () => set((s) => ({ bears: s.bears + 1 })),
    eatFish: () => set((s) => ({ fish: s.fish - 1 })), // cross-slice via get()
  });

// Combine — apply middleware only at the root, not inside slices
const useStore = create<BearSlice & FishSlice>()((...a) => ({
  ...createBearSlice(...a),
  ...createFishSlice(...a),
}));
```

### Persist to SecureStore (React Native)

```tsx
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import * as SecureStore from 'expo-secure-store';

const useAppStore = create<AppState>()(
  persist(
    immer((set) => ({
      theme: 'dark' as 'light' | 'dark',
      userId: null as string | null,
      setTheme: (t) => set((s) => { s.theme = t }),
      setUser:  (id) => set((s) => { s.userId = id }),
    })),
    {
      name: 'app-store',
      storage: createJSONStorage(() => ({
        getItem:    SecureStore.getItemAsync,
        setItem:    SecureStore.setItemAsync,
        removeItem: SecureStore.deleteItemAsync,
      })),
      // Never persist sensitive fields — only what's safe to store
      partialize: (s) => ({ theme: s.theme }),
    }
  )
);
```

### Reading and writing outside React

```tsx
// Read — anywhere (event handlers, native callbacks, utils)
const { count } = useBearStore.getState();

// Write — anywhere
useBearStore.setState((s) => ({ count: s.count + 1 }));

// Subscribe — for non-React integrations
const unsub = useBearStore.subscribe(
  (state) => state.count,
  (count) => console.log('count changed:', count)
);
// Call unsub() to unsubscribe
```

### Dependency injection via Context (stores that need props)

```tsx
import { createContext, useContext, useRef } from 'react';
import { createStore, useStore } from 'zustand';

interface CountStore { count: number; increment: () => void; }
type CountStoreApi = ReturnType<typeof createStore<CountStore>>;
const CountStoreContext = createContext<CountStoreApi | null>(null);

// Provider — initialize with props
function CountStoreProvider({ initialCount = 0, children }: { initialCount?: number; children: React.ReactNode }) {
  const storeRef = useRef<CountStoreApi>();
  if (!storeRef.current) {
    storeRef.current = createStore<CountStore>()((set) => ({
      count: initialCount,
      increment: () => set((s) => ({ count: s.count + 1 })),
    }));
  }
  return <CountStoreContext.Provider value={storeRef.current}>{children}</CountStoreContext.Provider>;
}

// Consumer hook
function useCountStore<T>(selector: (state: CountStore) => T) {
  const store = useContext(CountStoreContext);
  if (!store) throw new Error('Missing CountStoreProvider');
  return useStore(store, selector);
}

// Usage
const count = useCountStore((s) => s.count);
```

---

## Context Rules

```tsx
// ✅ Context only for stable, rarely-changing values (auth, theme, i18n)
const AuthContext = createContext<AuthUser | null>(null);

// React 19: use() works in conditionals; useContext does not
export function useAuth() {
  const ctx = use(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}

// ❌ Fast-changing values in context re-render ALL consumers on every change
// → use Zustand selectors or useSharedValue instead
```
