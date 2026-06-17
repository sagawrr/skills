# RN Review Checklist

For each category: scan the diff, cite `file:line`, assign severity.

---

## 1. New Architecture

**BLOCKER:**
- `<View ref={...}>` without `collapsable={false}` — view flattening makes the ref always null
- Component relies on intermediate state values between two `setState` calls — auto-batching drops them

**HIGH:**
- `shadow*` style props (`shadowColor`, `shadowRadius`, `shadowOpacity`, `shadowOffset`) — silently ignored on New Architecture; use `boxShadow`
- `elevation` prop used for shadows — use `boxShadow`
- `findNodeHandle()` — not available in Fabric

**Check:** Look for `ref=` on `View` components, `shadowColor`, `elevation`, `findNodeHandle`.

---

## 2. Reanimated 4

**HIGH:**
- `useAnimatedStyle` returns `width`, `height`, `top`, `left`, `margin`, or `padding` — triggers native layout recalculation every frame; animate `transform` + `opacity` only
- `useAnimatedScrollHandler` attached to a plain `<ScrollView>` — must be `<Animated.ScrollView>`
- `useAnimatedReaction` used to derive a value — should be `useDerivedValue` (lower overhead)
- No `cancelAnimation(sv)` before starting a new animation on the same shared value — causes fighting animations

**MEDIUM:**
- `runOnJS` used in new code — still works but `scheduleOnRN` is the preferred modern form
- Worklet closure captures an object reference — should capture only primitives to avoid UI thread memory waste

---

## 3. API Version Correctness

**BLOCKER (confirmed API removals):**
- `useQuery({ onSuccess, onError, onSettled })` — these callbacks were removed from `useQuery` in TanStack Query v5; they still exist on `useMutation`
- `useQuery({ cacheTime })` — renamed to `gcTime` in TanStack Query v5
- `estimatedItemSize` on `<FlashList>` — deprecated in v2; remove it
- `import { Audio } from 'expo-av'` / `import { Video } from 'expo-av'` — split into `expo-audio` and `expo-video` in SDK 55

**HIGH:**
- `import { Image } from 'react-native'` — use `expo-image`
- `import { SafeAreaView } from 'react-native'` — use `react-native-safe-area-context`
- `TouchableOpacity` or `TouchableHighlight` — use `Pressable`
- `import ... from '@react-navigation/native'` on SDK 56+ — use `expo-router` entry points

---

## 4. useEffect Audit

Every `useEffect` in the diff needs a justification. Fail if:

**BLOCKER:**
- `useEffect(() => setState(...), [dep])` — derives state in an effect; compute during render
- `useEffect` that fires analytics, navigation, or other side effects triggered by a user action — belongs in the event handler

**HIGH:**
- `useEffect` doing a data fetch — should be `useQuery`
- Subscription/listener/timer in `useEffect` with no cleanup return
- `useEffect` with state or prop used inside the body but missing from the dependency array

---

## 5. List Rendering

**HIGH:**
- `<ScrollView>` with a `.map()` of items — use `FlashList` for any list > 20 items
- `renderItem={({ item }) => <Component />}` as an inline arrow function — unstable reference defeats recycling; hoist the component
- `keyExtractor={(_, index) => index.toString()}` — never use index; breaks recycler identity
- `expo-image` inside list items without `recyclingKey` — stale image on fast scroll

**MEDIUM:**
- `getItemType` missing on a list with multiple item shapes — separate recycler pools not used

---

## 6. Type Safety

**HIGH:**
- New `: any` annotation — silences type errors that could be runtime crashes
- `as SomeType` type assertion without a comment explaining why it's safe
- Exported function with no return type annotation
- `// @ts-ignore` or `// @ts-expect-error` without an explanation comment

**MEDIUM:**
- Non-null assertion `!` on a value that is legitimately nullable
- `unknown` returned where a proper type could be inferred

---

## 7. Bundle Impact

**HIGH:**
- Barrel import where a direct path exists: `import { fn } from 'large-lib'` → `import fn from 'large-lib/fn'`
- `Platform.OS` in a build-time conditional — use `process.env.EXPO_OS` so Metro tree-shakes the dead platform branch

**MEDIUM:**
- Unused imports in changed files
- New dependency added without any size consideration — check if functionality already exists in an installed package

---

## 8. Expo Router

**BLOCKER:**
- Component, hook, or utility file placed directly in `app/` — Expo Router treats every file in `app/` as a route
- New route group directory without a `_layout.tsx` file

**HIGH:**
- Route file uses PascalCase or camelCase filename — must be kebab-case
- `useNavigation()` from `@react-navigation/native` used in SDK 56+ project — use `useRouter()` from `expo-router`
- Custom header rendered in screen body JSX — use `Stack.Screen options={{ title, headerRight }}` instead

**MEDIUM:**
- Deep relative imports from route files (`../../components`) — use path aliases (`@/components`)

---

## 9. NativeWind

**BLOCKER (v4/v5 mismatch in config — code impact):**
- `jsxImportSource: 'nativewind'` in Babel config when NativeWind v5 is installed — styles stop applying
- `'nativewind/babel'` in Babel presets when NativeWind v5 is installed — must be removed

**HIGH:**
- Color class on `<View>` intended to color child text — doesn't cascade; apply to `<Text>` directly
- `dark:` class without a corresponding light variant — light mode is unstyled
- `hover:` class on `<View>` or `<Text>` — only `Pressable` and `TextInput` support hover events
- `import { useColorScheme } from 'react-native'` — must import from `'nativewind'` to get `setColorScheme`

**MEDIUM:**
- Flex layout with no explicit `flex-direction` — RN default is `column`, not `row`

---

## 10. AI Bloat & Maintainability

**HIGH:**
- File > 300 lines (excluding tests) — split into focused modules
- Component > 150 lines of JSX — extract sub-components
- Component contains both data-fetching logic and detailed render JSX — separate into a data hook + pure component

**MEDIUM:**
- `useMemo` or `useCallback` added with no profiler evidence or explanation comment — React Compiler handles these; remove unless justified
- `useState` holding a value that could be derived from another state or prop — compute during render
- Abstraction (HOC, util function) that is used exactly once — inline it; single-use abstractions add indirection with no benefit
- Comment explains *what* the code does (restates the code) — remove; only explain *why* when non-obvious
- Magic number in a style value (`width: 327`) without a named constant or design token
- Boolean prop names that read as verbs: `doFetch`, `handleOpen` — prefer `isFetching`, `isOpen`
