# State & Effects — Full Catalog

## When useEffect IS Appropriate

`useEffect` has exactly three legitimate uses in a React 19 / New Architecture app:

1. **Setting up a subscription** to an external system (WebSocket, EventEmitter, native module listener). Use `useSyncExternalStore` if the store supports it — prefer that. Fall back to `useEffect` only for truly imperative subscriptions with no subscribe/snapshot interface.
2. **Triggering imperative native code** after mount (e.g. focusing an input, starting a camera stream). Must have a cleanup return.
3. **Synchronizing two external systems** with each other (rare — usually a sign of architectural debt).

If your `useEffect` reads or writes React state: almost certainly wrong. Find the right primitive below.

---

## Full Replacement Map

| You want to… | Use instead |
|---|---|
| Fetch data on mount | `useQuery` (TanStack Query) |
| Fetch data reactively | `useQuery` with reactive queryKey |
| Fetch a one-off Promise | `use(promise)` + Suspense |
| Derive from props/state | Compute during render (no hook) |
| Sync two state variables | Merge into one state or derive |
| Run code on event | Put it in the event handler |
| Animate on value change | `useAnimatedReaction` (worklet only) |
| Listen to a store | `useSyncExternalStore` |
| Measure layout | `onLayout` callback |
| Focus an input on mount | `ref.current?.focus()` in `useLayoutEffect` |
| Send analytics on user action | Call in handler, not effect |
| Reset state when prop changes | `key` prop to remount |
| Initialize state from prop | Pass as `useState(initialProp)` default |

---

## TanStack Query Patterns

```tsx
// Standard query
const { data, isPending, isError } = useQuery({
  queryKey: ['posts', userId],  // reactive — refetches when userId changes
  queryFn: () => api.posts.list(userId),
  staleTime: 60_000,            // don't refetch if fresh within 1min
  gcTime: 5 * 60_000,           // keep in cache 5min after last use
});

// Mutation with optimistic update
const mutation = useMutation({
  mutationFn: (post) => api.posts.create(post),
  onMutate: async (newPost) => {
    await queryClient.cancelQueries({ queryKey: ['posts'] });
    const previous = queryClient.getQueryData(['posts']);
    queryClient.setQueryData(['posts'], old => [...old, { ...newPost, id: 'temp' }]);
    return { previous };
  },
  onError: (_, __, ctx) => queryClient.setQueryData(['posts'], ctx?.previous),
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['posts'] }),
});

// Infinite scroll
const { data, fetchNextPage, hasNextPage } = useInfiniteQuery({
  queryKey: ['feed'],
  queryFn: ({ pageParam }) => api.feed.get({ cursor: pageParam }),
  getNextPageParam: (last) => last.nextCursor,
  initialPageParam: null,
});
const items = data?.pages.flatMap(p => p.items) ?? [];
```

---

## Zustand Patterns

```tsx
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Typed store with immer (mutable syntax, immutable updates)
interface AppStore {
  theme: 'light' | 'dark';
  setTheme: (t: 'light' | 'dark') => void;
}

const useAppStore = create<AppStore>()(
  persist(
    immer((set) => ({
      theme: 'dark',
      setTheme: (t) => set(s => { s.theme = t }),
    })),
    {
      name: 'app-store',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s) => ({ theme: s.theme }), // only persist what matters
    }
  )
);

// Selector — subscribe to a slice, not the whole store
const theme = useAppStore(s => s.theme);

// Outside React — read/write store from anywhere
const { theme } = useAppStore.getState();
useAppStore.setState(s => { s.theme = 'light'; });
```

---

## Jotai Patterns (atom-based, good for fine-grained subscriptions)

```tsx
import { atom, useAtom, useAtomValue, useSetAtom } from 'jotai';
import { atomWithStorage } from 'jotai/utils';

const countAtom = atom(0);
const doubleAtom = atom((get) => get(countAtom) * 2); // derived atom, no useEffect

// Read-only in one component
const count = useAtomValue(countAtom);
// Write-only in another (no re-render from read)
const setCount = useSetAtom(countAtom);

// Persisted atom
const themeAtom = atomWithStorage('theme', 'dark');
```

---

## React Context — Correct Patterns

```tsx
// ✅ Context for stable values only: auth user, theme, navigation
const AuthContext = createContext<AuthUser | null>(null);

// ✅ Split context by update frequency
const ThemeContext = createContext<Theme>(defaultTheme);       // never changes
const UserContext = createContext<User | null>(null);           // changes on login/logout
// NOT: one context with theme + user + search + filters

// ✅ Custom hook with null guard
export function useAuth() {
  const ctx = use(AuthContext); // React 19 — no need for useContext
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
```
