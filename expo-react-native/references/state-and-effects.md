# State & Effects — Full Catalog

## When useEffect IS Appropriate (3 cases only)

1. **External subscription** without a `useSyncExternalStore` interface (WebSocket, native EventEmitter). Must return cleanup.
2. **Imperative native call** after mount (focus input, start camera). Must return cleanup.
3. **Synchronizing two external systems** (rare — usually architectural debt).

Any `useEffect` that reads or writes React state: find the replacement below.

---

## Replacement Map

| You want to… | Use instead |
|---|---|
| Fetch data on mount/dependency change | `useQuery` (TanStack Query) |
| Fetch a one-off Promise | `use(promise)` + Suspense |
| Derive from props/state | Compute during render (no hook) |
| Sync two state variables | Merge into one or derive |
| Run code on event | Put it in the event handler |
| Listen to a store | `useSyncExternalStore` |
| Animate on value change | `useDerivedValue` worklet |
| Measure layout | `onLayout` callback |
| Focus input after mount | `ref.current?.focus()` in `useLayoutEffect` |
| Send analytics on user action | Call in handler |
| Reset state when ID prop changes | `key={id}` to remount component |
| Initialize state from prop | `useState(initialProp)` — one-time default |
| Read context | `use(Context)` (React 19) |

---

## TanStack Query Patterns

```tsx
// Standard query — reactive on queryKey
const { data, isPending, isError } = useQuery({
  queryKey: ['posts', userId],
  queryFn: () => api.posts.list(userId),
  staleTime: 60_000,   // don't refetch if fresh < 1min
  gcTime: 5 * 60_000,  // keep in cache 5min after unmount
});

// Mutation with optimistic update
const mutation = useMutation({
  mutationFn: (post: NewPost) => api.posts.create(post),
  onMutate: async (newPost) => {
    await queryClient.cancelQueries({ queryKey: ['posts'] });
    const previous = queryClient.getQueryData<Post[]>(['posts']);
    queryClient.setQueryData(['posts'], (old: Post[]) => [...old, { ...newPost, id: 'temp' }]);
    return { previous };
  },
  onError: (_, __, ctx) => queryClient.setQueryData(['posts'], ctx?.previous),
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['posts'] }),
});

// Infinite scroll — pairs with FlashList
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: ['feed'],
  queryFn: ({ pageParam }) => api.feed.get({ cursor: pageParam }),
  getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
  initialPageParam: null as string | null,
});
const items = data?.pages.flatMap(p => p.items) ?? [];

// Pair with FlashList:
<FlashList
  data={items}
  onEndReached={() => { if (hasNextPage) fetchNextPage(); }}
  onEndReachedThreshold={0.5}
  ListFooterComponent={isFetchingNextPage ? <Spinner /> : null}
/>
```

---

## Zustand Patterns

```tsx
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist, createJSONStorage } from 'zustand/middleware';
import * as SecureStore from 'expo-secure-store';

// Store with immer (mutable syntax → immutable output)
interface AppStore {
  theme: 'light' | 'dark';
  userId: string | null;
  setTheme: (t: 'light' | 'dark') => void;
  setUser: (id: string | null) => void;
}

const useAppStore = create<AppStore>()(
  persist(
    immer((set) => ({
      theme: 'dark',
      userId: null,
      setTheme: (t) => set(s => { s.theme = t }),
      setUser: (id) => set(s => { s.userId = id }),
    })),
    {
      name: 'app-store',
      storage: createJSONStorage(() => ({
        // Use SecureStore for sensitive data
        getItem: SecureStore.getItemAsync,
        setItem: SecureStore.setItemAsync,
        removeItem: SecureStore.deleteItemAsync,
      })),
      partialize: (s) => ({ theme: s.theme }), // only persist non-sensitive fields
    }
  )
);

// Selector — subscribe to a slice only (prevents unnecessary re-renders)
const theme = useAppStore(s => s.theme);
const setTheme = useAppStore(s => s.setTheme);

// Outside React — read/write from event handlers, native modules, etc.
const { theme } = useAppStore.getState();
useAppStore.setState(s => { s.theme = 'light'; });
```

---

## Jotai Patterns (fine-grained, atom-based)

```tsx
import { atom, useAtomValue, useSetAtom } from 'jotai';
import { atomWithStorage } from 'jotai/utils';
import AsyncStorage from '@react-native-async-storage/async-storage';

const countAtom = atom(0);

// Derived atom — replaces useEffect sync between states
const doubleAtom = atom(get => get(countAtom) * 2);

// Async derived atom — replaces useEffect data fetch
const userAtom = atom(async (get) => {
  const id = get(userIdAtom);
  return id ? fetchUser(id) : null;
});

// Read-only in one component — zero re-render from write
const count = useAtomValue(countAtom);
// Write-only in another — no re-render from reads
const setCount = useSetAtom(countAtom);

// Persisted atom with AsyncStorage
const themeAtom = atomWithStorage('theme', 'dark', {
  getItem: async (key, init) => (await AsyncStorage.getItem(key)) ?? init,
  setItem: (key, val) => AsyncStorage.setItem(key, String(val)),
  removeItem: (key) => AsyncStorage.removeItem(key),
});
```

---

## Context — Correct Patterns

```tsx
// ✅ Context only for stable, rarely-changing values
const AuthContext = createContext<AuthUser | null>(null);
const ThemeContext = createContext<'light' | 'dark'>('dark');

// ✅ React 19 — use() over useContext
// Works in conditionals and loops (useContext does not)
export function useAuth() {
  const ctx = use(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

// ✅ Split contexts by update frequency
// Theme — changes once per session (dark/light toggle)
// Auth  — changes on login/logout
// Search query — changes on every keystroke → Zustand, NOT context

// ❌ Don't store fast-changing UI state in context
// This re-renders every consumer on every keystroke
const SearchContext = createContext({ query: '', setQuery: () => {} });
```

---

## Async Patterns — No useEffect

```tsx
// ✅ React 19 Actions — form/mutation handling without useEffect
async function submitAction(formData: FormData) {
  'use server'; // or client action
  const name = formData.get('name');
  await api.update({ name });
}

// ✅ useActionState — replaces useEffect + useState for form state
const [state, dispatch, isPending] = useActionState(submitAction, initialState);

// ✅ useFormStatus — within a form component
const { pending } = useFormStatus();
```
