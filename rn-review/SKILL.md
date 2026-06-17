---
name: rn-review
description: Reviews a React Native or Expo PR diff for code-level correctness, performance anti-patterns, and AI-era defects. Outputs findings ranked by severity with file:line citations. Use when asked to review a PR, audit a diff, or check code before merging. Specifically tuned for patterns that look correct but break at runtime on New Architecture or under wrong library versions.
---

# React Native PR Review

Specialized code review for React Native / Expo. Run this before or instead of a generic code review when the project uses React Native.

## How to Run

```
/rn-review           # reviews current git diff
/rn-review --fix     # applies safe mechanical fixes (BLOCKER + HIGH)
```

1. Get the diff: `git diff main...HEAD`
2. Scan each checklist category from `references/checklist.md` against the diff
3. Cite every finding as `path/file.tsx:line — [SEVERITY] description + fix`
4. Output ranked summary: BLOCKER → HIGH → MEDIUM → INFO

## Severity

| Level | Meaning | Example |
|---|---|---|
| BLOCKER | Runtime crash, data loss, broken on New Architecture | `onSuccess` in `useQuery` v5 |
| HIGH | Silent regression, wrong API, perf degradation | ref without `collapsable={false}` |
| MEDIUM | Maintainability, suboptimal pattern | speculative `useMemo` |
| INFO | Better alternative exists | suggest `scheduleOnRN` over `runOnJS` |

## Why This Isn't Generic Review

AI tools produce a specific class of defect: code that looks correct but uses removed APIs, wrong library versions, or patterns that silently break on New Architecture. Generic review misses these because they require knowing the exact version boundary.

| AI-introduced defect | Failure mode |
|---|---|
| `onSuccess` in `useQuery` | Removed in TanStack Query v5 — silently ignored |
| `estimatedItemSize` on FlashList | Deprecated in v2 — no error, just ignored |
| Ref without `collapsable={false}` | New Architecture view flattening → ref is always null |
| `useEffect` for derived state | Extra render cycle, stale frame on state update |
| `jsxImportSource: 'nativewind'` in Babel | Breaks NativeWind v5 — styles stop applying |
| Speculative `useMemo`/`useCallback` | Adds noise; React Compiler handles these now |
| Component file in `app/` directory | Expo Router treats it as a route — 404 or wrong screen |
| `shadow*` / `elevation` props | Silently ignored on New Architecture |

## Checklist Categories (run in parallel)

Each category is detailed in `references/checklist.md`:

1. **New Architecture** — batching, refs, shadow props, Fabric APIs
2. **Reanimated 4** — animated properties, scroll handler, worklet safety
3. **API version correctness** — TanStack Query v5, FlashList v2, SDK 55+ changes
4. **useEffect audit** — every `useEffect` needs a justification
5. **List rendering** — FlashList setup, recycling keys, item stability
6. **Type safety** — `any`, type assertions, missing return types
7. **Bundle** — barrel imports, `Platform.OS` vs `process.env.EXPO_OS`
8. **Expo Router** — file placement, layout files, navigation API
9. **NativeWind** — v4/v5 mismatch, cascade assumptions, dark mode
10. **AI bloat** — over-abstraction, god components, comment noise, speculative memoization

## Output Template

```
## RN Review — <N> findings

### BLOCKER
- `src/screens/Feed.tsx:42` — `onSuccess` in `useQuery` is removed in TanStack Query v5.
  Move to `useMutation.onSuccess` or a `useEffect` watching `data`.

### HIGH  
- `src/components/Card.tsx:18` — `<View ref={cardRef}>` without `collapsable={false}`.
  New Architecture view flattening will make this ref always null.
  Fix: `<View ref={cardRef} collapsable={false}>`

- `src/screens/Home.tsx:55` — `useEffect(() => setFiltered(items.filter(fn)), [items])`.
  Derives state inside an effect. Compute `filtered` during render instead.

### MEDIUM
- `src/hooks/useData.ts:12` — `useCallback` with empty deps on a non-closuring function.
  React Compiler handles this — remove the manual wrapper.

### INFO
- `src/components/Avatar.tsx:5` — `import { Image } from 'react-native'`.
  Prefer `expo-image` for recyclingKey support inside FlashList.
```

## References

- `references/checklist.md` — full itemized checklist per category
- `references/ai-patterns.md` — AI-era defect patterns with detection and fixes
- Related: `expo-react-native` skill (authoritative patterns reference)
