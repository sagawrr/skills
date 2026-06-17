# AI-Era Anti-Patterns in React Native

Defects AI tools reliably produce — code that looks correct, compiles cleanly, but breaks at runtime or degrades performance silently.

---

## 1. Hallucinated APIs (Wrong Library Version)

AI training data predates breaking changes. The model generates the old API with full confidence.

| Hallucinated pattern | What's actually correct | Library |
|---|---|---|
| `useQuery({ onSuccess, onError })` | `useMutation.onSuccess` or `useEffect` on `data` | TanStack Query v5 |
| `useQuery({ cacheTime: 5000 })` | `useQuery({ gcTime: 5000 })` | TanStack Query v5 |
| `estimatedItemSize={72}` on FlashList | Remove — auto-handled in v2 | FlashList v2 |
| `estimatedListSize` / `estimatedFirstItemOffset` | Remove — all size props removed in v2 | FlashList v2 |
| `import { Audio } from 'expo-av'` | `import { Audio } from 'expo-audio'` | Expo SDK 55 |
| `forwardRef` on new function components | Plain `ref` prop (still works, not needed) | React 19 |
| `jsxImportSource: 'nativewind'` in Babel | Remove for NativeWind v5 | NativeWind v5 |
| `z.string().email()` / `.url()` / `.uuid()` | `z.email()` / `z.url()` / `z.uuid()` | Zod v4 |
| `z.record(z.string())` | `z.record(z.string(), ValueSchema)` | Zod v4 |
| `z.nativeEnum(E)` | `z.enum(E)` | Zod v4 |
| `{ invalid_type_error }` / `{ required_error }` | `{ error: '...' }` | Zod v4 |
| `import create from 'zustand'` | `import { create } from 'zustand'` | Zustand v5 |
| `create(fn, equalityFn)` | `createWithEqualityFn` from `'zustand/traditional'` | Zustand v5 |
| `StyleSheet.absoluteFillObject` | `StyleSheet.absoluteFill` | RN 0.85 |
| `import { MasonryFlashList }` | `<FlashList masonry numColumns={N} />` | FlashList v2 |

**Why it happens:** The model saw thousands of examples of the old API. It generates them fluently because they look like correct code. The fix is always to check the installed major version against what the code uses.

---

## 2. useEffect for Derived State

```tsx
// ❌ AI-generated — extra render, one frame of stale state, easy to get deps wrong
const [filtered, setFiltered] = useState(items);
useEffect(() => {
  setFiltered(items.filter(isActive));
}, [items, isActive]);

// ✅ compute during render — zero lag, zero extra state
const filtered = items.filter(isActive);
```

**Why it happens:** Model associates "recompute when dependency changes" with `useEffect`. The React mental model is to reach for `useEffect` for any "reaction." Correct model: `useEffect` is only for synchronizing with external systems.

---

## 3. useEffect for Event Side Effects

```tsx
// ❌ AI-generated — fires on every render where submitted=true; fragile, hard to trace
useEffect(() => {
  if (submitted) {
    analytics.track('form_submitted');
    router.push('/success');
  }
}, [submitted]);

// ✅ in the handler — obvious, synchronous, no timing surprises
async function handleSubmit() {
  await submit(data);
  analytics.track('form_submitted');
  router.push('/success');
}
```

**Why it happens:** Model sees "do X when Y" and reaches for `useEffect`. Correct: if Y is caused by a user action, the side effect belongs in that action's handler.

---

## 4. Speculative Memoization

```tsx
// ❌ AI adds useMemo/useCallback "for performance" with no measurement
const handlePress = useCallback(() => {
  setCount(c => c + 1);
}, []); // React Compiler would handle this

const expensiveValue = useMemo(() => a + b, [a, b]); // trivial computation

// ✅ let React Compiler handle it (SDK 54+)
const handlePress = () => setCount(c => c + 1);
const expensiveValue = a + b;
```

**Why it happens:** Trained on pre-compiler codebases where manual memoization was best practice. In 2025 codebases with React Compiler enabled, most of this is noise that adds visual complexity without benefit.

**When manual memoization IS justified:** Profiler confirms a component re-renders with identical inputs AND the computation is measurably expensive (> 1ms, or causes visible jank).

---

## 5. New Architecture Blindspots

Two silent breakage patterns AI tools never get right because they weren't in training data:

**Ref on flattened view:**
```tsx
// ❌ New Architecture view flattening → ref is always null
const cardRef = useRef<View>(null);
<View ref={cardRef} style={styles.card}>

// ✅ prevent view from being optimized out
<View ref={cardRef} collapsable={false} style={styles.card}>
```

**State batching regression:**
```tsx
// ❌ relied on intermediate state between these two setStates
// Old arch: two separate renders. New arch: one render with final values.
setLoading(true);         // this intermediate state is lost
await fetchData();
setLoading(false);
setData(result);

// ✅ if the intermediate state matters, batch explicitly or use a reducer
dispatch({ type: 'FETCH_START' });
const result = await fetchData();
dispatch({ type: 'FETCH_SUCCESS', data: result });
```

---

## 6. God Components

AI fills a single component with fetching, transformation, business logic, and rendering. This is the #1 maintainability problem in AI-generated React Native code.

```tsx
// ❌ AI-generated — 250 lines, mixes concerns, impossible to test in isolation
function ProfileScreen() {
  const [user, setUser] = useState(null);
  const [posts, setPosts] = useState([]);
  useEffect(() => { fetchUser(id).then(setUser); }, [id]);
  useEffect(() => { fetchPosts(id).then(setPosts); }, [id]);
  // 200 lines of nested JSX...
}

// ✅ separate concerns
function ProfileScreen() {
  const { user, posts, isPending } = useProfileData(id); // data hook
  if (isPending) return <ProfileSkeleton />;
  return <ProfileLayout user={user} posts={posts} />;    // pure render
}
```

**Rule of thumb:** If a component has > 5 `useState` calls, it's doing too much. If it both fetches data and renders detail, split it.

---

## 7. Single-Use Abstraction

```tsx
// ❌ AI generalizes a pattern it sees once — adds indirection with zero payoff
function withLoadingState<T>(Component: React.FC<T>, isLoading: boolean) {
  return isLoading ? <Skeleton /> : <Component />;
}
<ProfileContent user={user} />

// ✅ inline it — the abstraction added nothing
{isPending ? <Skeleton /> : <ProfileContent user={user} />}
```

**Rule:** Abstract when ≥ 3 call sites use the same pattern, or when the abstraction name communicates non-obvious domain logic. Not before.

---

## 8. Type Safety Shortcuts

AI takes the fastest path to "no TypeScript error" — not the correct one.

```tsx
// ❌ silences errors without fixing them
const data = response as UserData;
const handler = (x: any) => x.name;
// @ts-ignore

// ✅ type guard for runtime validation
function isUserData(x: unknown): x is UserData {
  return typeof x === 'object' && x !== null && 'id' in x && 'name' in x;
}

// ✅ schema validation at API boundaries (Zod)
const UserSchema = z.object({ id: z.number(), name: z.string() });
const user = UserSchema.parse(response); // throws with a readable error if wrong
```

**Rule:** Every `any`, `as SomeType`, and `@ts-ignore` needs an explanation comment. Without one, treat it as a deferred bug.

---

## 9. Expo Router File Placement

AI places components in `app/` because it sees route files there and assumes it's the right folder.

```
// ❌ AI-generated — UserCard becomes a route at /UserCard
app/
  index.tsx
  UserCard.tsx      ← Expo Router treats this as a screen
  useProfile.ts     ← becomes a route too

// ✅
app/
  index.tsx
  _layout.tsx
components/
  UserCard.tsx
hooks/
  useProfile.ts
```

---

## 10. What-Comments (Noise)

AI generates comments that restate what the code already says. They rot as code changes.

```tsx
// ❌ restates the code — adds noise, becomes wrong after refactor
// Fetch user data from API using the user id
const fetchUser = (id: string) => api.get(`/users/${id}`).then(r => r.data);

// ✅ no comment needed — name is self-explanatory

// ✅ comment only when WHY is non-obvious
// collapsable={false} required — New Architecture view flattening makes refs null otherwise
<View ref={cardRef} collapsable={false}>
```

---

## 11. React Hook Form — formState Proxy Misuse

AI tools read `formState` sub-properties conditionally, silently breaking subscriptions.

```tsx
// ❌ AI-generated — short-circuit prevents isValid getter from firing
const isDisabled = !formState.isDirty || !formState.isValid;

// ❌ AI-generated — Proxy fires once at declaration, not on changes
useEffect(() => { validate(errors); }, [formState.errors]);

// ✅ destructure unconditionally at component top
const { isDirty, isValid, errors } = formState;
const isDisabled = !isDirty || !isValid;
useEffect(() => { validate(errors); }, [formState]); // depend on formState, not sub-property
```

**Why it happens:** AI treats `formState` as a plain object. It's a Proxy — sub-property access is the subscription mechanism.

---

## 12. React Hook Form — `register()` on React Native TextInput

```tsx
// ❌ AI-generated from web RHF examples — doesn't work in React Native
<TextInput {...register('email')} />

// ✅ React Native requires useController
function EmailInput({ control }: { control: Control<LoginForm> }) {
  const { field, fieldState: { error } } = useController({ control, name: 'email' });
  return (
    <>
      <TextInput value={field.value} onChangeText={field.onChange} onBlur={field.onBlur} />
      {error && <Text>{error.message}</Text>}
    </>
  );
}
```

**Why it happens:** AI training data is dominated by web React examples. `register()` works via ref-spreading on web inputs; React Native TextInput works differently.

---

## 13. Zod — Type Duplication

```tsx
// ❌ AI maintains a separate interface alongside the schema — they drift apart
const LoginSchema = z.object({ email: z.email(), password: z.string().min(8) });
interface LoginForm { email: string; password: string; } // duplicate, will drift

// ✅ z.infer is the single source of truth
const LoginSchema = z.object({ email: z.email(), password: z.string().min(8) });
type LoginForm = z.infer<typeof LoginSchema>;
```

---

## 14. Zod — throw inside transform

```tsx
// ❌ throw inside transform bypasses ZodError — crashes safeParse()
const Schema = z.string().transform((val) => {
  if (!val.includes('@')) throw new Error('not an email'); // not caught as ZodError
  return val.toLowerCase();
});

// ✅ validate with refine before transform
const Schema = z.string()
  .refine((val) => val.includes('@'), 'Enter a valid email')
  .transform((val) => val.toLowerCase()); // only runs after validation passes
```

