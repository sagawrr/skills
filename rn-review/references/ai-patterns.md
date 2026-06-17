# AI-Era Anti-Patterns in React Native

Patterns AI tools reliably get wrong. Each has a detection signal, the failure mode, and the fix.

---

## 1. Hallucinated APIs (version mismatch)

AI training data predates breaking changes. The model generates the old API confidently.

| Hallucinated | Real (current) | Library |
|---|---|---|
| `useQuery({ onSuccess })` | `useMutation.onSuccess` or `useEffect` on `data` | TanStack Query v5 |
| `useQuery({ cacheTime })` | `useQuery({ gcTime })` | TanStack Query v5 |
| `runOnJS(fn)(args)` | `scheduleOnRN(fn, ...args)` | Reanimated 4 |
| `estimatedItemSize` on FlashList | Remove — auto-handled | FlashList v2 |
| `expo-av` for audio | `expo-audio` | Expo SDK 55 |
| `expo-av` for video | `expo-video` | Expo SDK 55 |
| `jsxImportSource: 'nativewind'` in Babel | Delete entirely | NativeWind v5 |
| `'nativewind/babel'` preset | Delete entirely | NativeWind v5 |
| `forwardRef` on function component | Plain `ref` prop | React 19 |
| `useContext(X)` | `use(X)` | React 19 |

**Detection:** Every time a PR touches a dependency that had a major breaking change, grep the diff for the old API names.

---

## 2. useEffect for Derived State

```tsx
// ❌ AI-generated — extra render, stale frame, race condition
const [filtered, setFiltered] = useState(items);
useEffect(() => {
  setFiltered(items.filter(activeFilter));
}, [items, activeFilter]);

// ✅ derive during render — zero lag, zero state
const filtered = items.filter(activeFilter);
```

**Why AI does this:** Pattern-matches on "recalculate when X changes" → reaches for `useEffect`.
**Detection:** `grep "useEffect.*setState\|useEffect.*setData\|useEffect.*dispatch"` in diff.

---

## 3. useEffect for User-Triggered Side Effects

```tsx
// ❌ AI-generated — fires on every render where submitted=true, hard to reason about
useEffect(() => {
  if (submitted) {
    analytics.track('form_submitted');
    router.push('/success');
  }
}, [submitted]);

// ✅ in the handler — obvious, synchronous, no timing issues
async function handleSubmit() {
  await submitForm(data);
  analytics.track('form_submitted');
  router.push('/success');
}
```

**Why AI does this:** Associates "do X after Y happens" with `useEffect` regardless of whether Y is external.
**Detection:** `useEffect` body contains `router.push`, analytics calls, or other event-response actions.

---

## 4. Speculative Memoization

```tsx
// ❌ AI-generated — useMemo/useCallback added "for performance" with no evidence
const handlePress = useCallback(() => {
  setCount(c => c + 1);
}, []); // empty deps — React Compiler would handle this

const doubled = useMemo(() => count * 2, [count]); // trivial computation

// ✅ React Compiler (SDK 54+) handles most memoization automatically
// Only add useMemo/useCallback when profiler shows the component bailing out
const handlePress = () => setCount(c => c + 1);
const doubled = count * 2;
```

**Why AI does this:** Trained on pre-compiler codebases where manual memoization was best practice. Now it's mostly noise.
**Detection:** `useMemo`/`useCallback` on trivial values or with no performance comment.

---

## 5. Over-Abstraction of Single-Use Patterns

```tsx
// ❌ AI-generated — abstraction used exactly once, adds indirection for no gain
function withLoadingState<T>(Component: React.FC<T>, isLoading: boolean) {
  return isLoading ? <Skeleton /> : <Component />;
}

// ✅ inline when used once
{isLoading ? <Skeleton /> : <UserCard user={user} />}
```

**Why AI does this:** Trained to "follow best practices" and generalizes prematurely.
**Rule:** Abstraction is justified when the pattern appears ≥3 times OR the abstraction name communicates non-obvious domain logic.

---

## 6. God Components

AI fills a single component with: fetching, transformation, business logic, and rendering. This is the #1 maintainability problem in AI-generated RN code.

**Signs:**
- Component file > 300 lines
- Component `useState` > 5 hooks
- Component has both data fetching logic and detailed JSX
- File imports from 10+ different modules

**Fix:** Separate concerns — `useXxxData` hooks for fetching/logic, pure components for rendering.

```tsx
// ❌ Everything in one component
function ProfileScreen() {
  const [user, setUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { fetchUser().then(setUser); }, []);
  useEffect(() => { fetchPosts().then(setPosts); }, []);
  // 200 lines of JSX...
}

// ✅ Split by concern
function ProfileScreen() {
  const { user, posts, isPending } = useProfileData(userId);
  if (isPending) return <ProfileSkeleton />;
  return <ProfileLayout user={user} posts={posts} />;
}
```

---

## 7. Type Safety Shortcuts

AI takes the fastest path to "no TypeScript error," not the correct one.

```tsx
// ❌ AI reaches for these when types get hard
const data = response as UserData;
const handler = (x: any) => x.name;
// @ts-ignore

// ✅ Correct approaches
// Use type guard
function isUserData(x: unknown): x is UserData {
  return typeof x === 'object' && x !== null && 'name' in x;
}
// Use Zod for runtime validation at API boundaries
const schema = z.object({ name: z.string(), id: z.number() });
const data = schema.parse(response);
```

**Rule:** Every `any`, `as SomeType`, and `@ts-ignore` in a diff should have a comment explaining why it's safe. Without a comment, it's a bug waiting to happen.

---

## 8. Comment Noise

AI generates comments that restate what the code does. These rot as the code changes.

```tsx
// ❌ AI-generated noise
// This function fetches user data from the API
const fetchUser = async (id: string) => {
  // Make API call with user id
  const response = await api.get(`/users/${id}`);
  // Return the data
  return response.data;
};

// ✅ No comments needed — the code is self-documenting
const fetchUser = (id: string) => api.get(`/users/${id}`).then(r => r.data);

// ✅ Comment only when WHY is non-obvious
// collapsable={false} required — New Architecture view flattening makes refs null without it
<View ref={cardRef} collapsable={false}>
```

---

## 9. Flat File Structure (Expo Router)

AI places components, types, and utilities directly in the `app/` directory. This breaks Expo Router.

```
// ❌ AI-generated structure
app/
  index.tsx
  UserCard.tsx        ← component, not a route
  useProfileData.ts   ← hook, not a route
  types.ts            ← types, not a route

// ✅ Correct
app/
  index.tsx
  _layout.tsx
components/
  UserCard.tsx
hooks/
  useProfileData.ts
types/
  index.ts
```

---

## 10. New Architecture Blindspots

AI training data skews to pre-New-Architecture patterns. Two silent breakage patterns:

**Ref on flattened view:**
```tsx
// ❌ New Architecture view flattening makes this ref null
const cardRef = useRef<View>(null);
<View ref={cardRef} style={styles.card}>

// ✅ collapsable={false} prevents flattening
<View ref={cardRef} collapsable={false} style={styles.card}>
```

**State batching regression:**
```tsx
// ❌ relied on intermediate state between these two setStates
// Old arch: two renders. New arch: one render with final value only.
setStep(1);      // intermediate value lost under batching
setStep(step + 1);

// ✅ use functional update or a single state object
setStep(s => s + 1);
```
