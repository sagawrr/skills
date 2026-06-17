# State & Effects

## TanStack Query Patterns

```tsx
// Standard query — reactive on queryKey changes
const { data, isPending } = useQuery({
  queryKey: ['posts', userId],
  queryFn: () => api.posts.list(userId),
  staleTime: 60_000,   // serve from cache < 1min old
  gcTime: 5 * 60_000,  // keep in cache 5min after unmount
});

// Optimistic mutation — the rollback pattern is what's hard to get right
const mutation = useMutation({
  mutationFn: (post: NewPost) => api.posts.create(post),
  onMutate: async (newPost) => {
    await queryClient.cancelQueries({ queryKey: ['posts'] });           // prevent overwrite
    const snapshot = queryClient.getQueryData<Post[]>(['posts']);
    queryClient.setQueryData(['posts'], (old: Post[]) => [...old, { ...newPost, id: 'temp' }]);
    return { snapshot };
  },
  onError: (_, __, ctx) => queryClient.setQueryData(['posts'], ctx?.snapshot),
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['posts'] }),
});

// Infinite scroll — paired with FlashList
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

## Zustand Patterns

```tsx
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist, createJSONStorage } from 'zustand/middleware';
import * as SecureStore from 'expo-secure-store';

const useStore = create<AppState>()(
  persist(
    immer((set) => ({
      theme: 'dark' as 'light' | 'dark',
      userId: null as string | null,
      setTheme: (t) => set(s => { s.theme = t }),
      setUser:  (id) => set(s => { s.userId = id }),
    })),
    {
      name: 'app-store',
      // Use SecureStore for sensitive data
      storage: createJSONStorage(() => ({
        getItem:    SecureStore.getItemAsync,
        setItem:    SecureStore.setItemAsync,
        removeItem: SecureStore.deleteItemAsync,
      })),
      partialize: (s) => ({ theme: s.theme }), // only persist non-sensitive fields
    }
  )
);

// Selector — subscribe to a slice, not the whole store
const theme  = useStore(s => s.theme);
const setUser = useStore(s => s.setUser);

// Outside React (native callbacks, event handlers)
useStore.getState().setUser('123');
```

---

## Jotai Patterns

```tsx
import { atom, useAtomValue, useSetAtom } from 'jotai';

const countAtom = atom(0);

// Async derived atom — replaces useEffect data fetch
const userAtom = atom(async (get) => {
  const id = get(userIdAtom);
  return id ? await fetchUser(id) : null;
});

// Read-write split — subscribe only where needed
const count  = useAtomValue(countAtom); // re-renders on change
const setCount = useSetAtom(countAtom); // never re-renders from reads
```

---

## Context Rules

```tsx
// ✅ Context only for stable, rarely-changing values (auth, theme)
const AuthContext = createContext<AuthUser | null>(null);

// React 19: use() works in conditions and loops; useContext does not
export function useAuth() {
  const ctx = use(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}

// ❌ Fast-changing values in context re-render ALL consumers
// Route these to Zustand, Jotai, or useSharedValue instead
const [query, setQuery] = useState('');
<SearchContext.Provider value={{ query, setQuery }}> // every keystroke = all consumers re-render
```
