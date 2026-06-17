# RN Review Checklist

For each category: scan the diff, cite file:line, assign severity.

---

## 1. New Architecture Correctness

**BLOCKER if violated:**

- [ ] Any `<View ref={...}>` without `collapsable={false}` → view flattening makes the ref always null
- [ ] Component relies on intermediate `setState` values between renders → auto-batching silently drops them

**HIGH if violated:**

- [ ] `findNodeHandle()` called anywhere → removed in Fabric
- [ ] `UIManager` legacy bridge APIs → not available without interop layer
- [ ] `shadow*` style props (`shadowColor`, `shadowRadius`, etc.) → ignored on New Architecture; use `boxShadow`
- [ ] `elevation` prop for shadows → use `boxShadow`

**Check pattern:**
```bash
git diff main...HEAD | grep -n "findNodeHandle\|UIManager\|shadowColor\|shadowRadius\|shadowOpacity\|shadowOffset\|elevation"
```

---

## 2. Reanimated 4

**BLOCKER:**

- [ ] `runOnJS` used anywhere → removed in Reanimated 4, causes crash
- [ ] `useAnimatedStyle` return contains `width`/`height`/`top`/`left`/`margin`/`padding` → layout recalculation every frame

**HIGH:**

- [ ] `Animated.ScrollView` replaced with plain `ScrollView` when `useAnimatedScrollHandler` is attached
- [ ] `useAnimatedReaction` used for derived values → should be `useDerivedValue`
- [ ] No `cancelAnimation()` before starting a new animation on the same shared value
- [ ] Worklet closure captures object references → should capture only primitives

**Check pattern:**
```bash
git diff main...HEAD | grep -n "runOnJS\|useAnimatedReaction"
```

---

## 3. API Version Correctness

**BLOCKER (AI hallucination — these APIs no longer exist):**

- [ ] `onSuccess` / `onError` / `onSettled` as options to `useQuery` → removed in TanStack Query v5; use `useMutation` callbacks or `useEffect` watching `data`
- [ ] `cacheTime` in TanStack Query → renamed to `gcTime` in v5
- [ ] `FlashList` with `estimatedItemSize` → deprecated in v2, no longer used
- [ ] `expo-av` for audio/video → split into `expo-audio` + `expo-video` in SDK 55

**HIGH:**

- [ ] `import { Image } from 'react-native'` → use `expo-image`
- [ ] `SafeAreaView` from `react-native` → use `react-native-safe-area-context`
- [ ] `TouchableOpacity` / `TouchableHighlight` → use `Pressable`
- [ ] `AsyncStorage` from `@react-native-async-storage` for secrets → use `expo-secure-store`
- [ ] `@react-navigation/*` imports on SDK 56+ → move to `expo-router` entry points

**Check pattern:**
```bash
git diff main...HEAD | grep -n "onSuccess.*useQuery\|cacheTime\|estimatedItemSize\|from 'expo-av'\|from 'react-native'.*Image\|TouchableOpacity\|TouchableHighlight"
```

---

## 4. useEffect Audit

Every `useEffect` in the diff requires justification. Fail if:

**BLOCKER:**

- [ ] `useEffect` with no external system involved at all — look for: `useEffect(() => setState(...), [dep])` — this derives state in an effect
- [ ] `useEffect` fires a side effect triggered by user action (e.g., analytics on `submitted` state change) — should be in the event handler

**HIGH:**

- [ ] `useEffect` with no cleanup for subscriptions, timers, or listeners
- [ ] `useEffect` doing data fetch → should be `useQuery`
- [ ] Stale closure: state/prop used inside `useEffect` but not in dependency array

**Check pattern:**
```bash
git diff main...HEAD | grep -A5 "useEffect" | grep -E "setState|setData|dispatch"
```

---

## 5. List Rendering

**HIGH:**

- [ ] `ScrollView` rendering a `.map()` of more than ~20 items → use `FlashList`
- [ ] `FlatList` when New Architecture is enabled → prefer `FlashList` v2
- [ ] `renderItem` prop is an inline arrow function: `renderItem={({ item }) => <Row />}` — unstable reference, defeats recycling
- [ ] `keyExtractor` uses index: `(_, index) => index.toString()` — breaks recycler identity
- [ ] `expo-image` inside list items without `recyclingKey` → stale image on fast scroll

**MEDIUM:**

- [ ] `getItemType` missing on heterogeneous lists → separate recycler pools not used

---

## 6. Type Safety

**HIGH:**

- [ ] New `any` type added in diff — each one silences type errors that could be runtime crashes
- [ ] `as SomeType` type assertion without a comment explaining why it's safe
- [ ] Exported function with no return type annotation
- [ ] `// @ts-ignore` or `// @ts-expect-error` added without explanation comment

**MEDIUM:**

- [ ] Optional chaining `?.` used where the value is guaranteed non-null (masks bugs)
- [ ] Non-null assertion `!` used on a value that is legitimately nullable

**Check pattern:**
```bash
git diff main...HEAD | grep -n ": any\|as [A-Z]\|@ts-ignore\|@ts-expect-error"
```

---

## 7. Bundle Impact

**HIGH:**

- [ ] New barrel import: `import { A, B, C } from 'large-library'` where a direct path exists
- [ ] New heavy dependency added (`package.json` diff) without size justification
- [ ] `Platform.OS` used in a conditional that could be `process.env.EXPO_OS` (prevents tree-shaking)

**MEDIUM:**

- [ ] Unused imports in changed files
- [ ] Dynamic `require()` that prevents static analysis

---

## 8. Expo Router Conventions

**BLOCKER:**

- [ ] Component file placed directly in `app/` directory → only route files belong in `app/`
- [ ] No `_layout.tsx` in a new route group directory

**HIGH:**

- [ ] Route file uses `PascalCase` filename → must be kebab-case
- [ ] New screen uses `useNavigation()` from `@react-navigation/native` on SDK 56+ → use `useRouter()` from `expo-router`
- [ ] Custom header component rendered inside screen body → use `Stack.Screen options={{ title }}` instead

**MEDIUM:**

- [ ] Deep relative imports from route files (e.g., `../../components`) → use path aliases (`@/components`)

---

## 9. NativeWind

**BLOCKER (v4/v5 mismatch):**

- [ ] `jsxImportSource: 'nativewind'` in `babel.config.js` when NativeWind v5 is installed → must be removed
- [ ] `'nativewind/babel'` in Babel presets when NativeWind v5 is installed → must be removed

**HIGH:**

- [ ] `className` applied to a `<View>` to set text color → text color doesn't cascade to children; apply to `<Text>` directly
- [ ] `dark:` class without corresponding light variant → e.g., `dark:text-white` alone (light is unstyled)
- [ ] `hover:` class on `<View>` or `<Text>` → requires `onHoverIn`/`onHoverOut`; only `Pressable` + `TextInput` support it
- [ ] `import { useColorScheme } from 'react-native'` → must be from `'nativewind'` to get `setColorScheme`

**MEDIUM:**

- [ ] Flex layout without explicit direction set → RN default is `column`, web default is `row`; always explicit

---

## 10. Maintainability & AI Bloat

**HIGH:**

- [ ] File exceeds 300 lines (excluding tests) → split into smaller modules
- [ ] Component exceeds 150 lines of JSX → extract sub-components
- [ ] Prop drilling more than 2 levels deep for the same value → use context or state management

**MEDIUM:**

- [ ] `useMemo`/`useCallback` added with no profiler evidence or comment explaining the bottleneck → remove; React Compiler handles most cases
- [ ] State that can be derived from other state/props stored in `useState` → compute during render
- [ ] Boolean prop names that don't read as adjectives: `doFetch`, `handleOpen` → prefer `isFetching`, `isOpen`
- [ ] Comment explains WHAT the code does (restates code) → remove; comments should explain WHY
- [ ] Abstraction for a pattern used only once → inline it; premature abstraction is the most common AI bloat
- [ ] Magic numbers without named constants in styling (`width: 327`) → extract to a design token or constant
