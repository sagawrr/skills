---
name: rn-review
description: Reviews a React Native or Expo PR diff for code-level correctness, performance anti-patterns, and AI-era defects. Outputs findings ranked by severity with file:line citations. Use when asked to review a PR, audit a diff, or check code before merging. Specifically tuned for patterns that look correct but break at runtime on New Architecture or under wrong library versions.
---

# React Native PR Review

Specialized code review for React Native / Expo. Run this before or instead of a generic code review when the project uses React Native.

## Reference Loading

**Before starting the review**, read `package.json` and load only the relevant reference sections:

| If `package.json` contains… | Load these checklist sections |
|---|---|
| `react-hook-form` | checklist §11 (RHF + Zod) |
| `reanimated` | checklist §2 (Reanimated 4) |
| `nativewind` | checklist §9 (NativeWind) |
| `@tanstack/react-query` | checklist §3 API version items |
| `@shopify/flash-list` | checklist §5 (List Rendering) |

Always load: checklist §1 (New Architecture), §4 (useEffect), §6 (Type Safety), §7 (Bundle), §8 (Expo Router), §10 (AI Bloat).

Load `references/ai-patterns.md` only if the diff shows clear AI-generated patterns (god components, speculative memoization, what-comments) or for first-time review of an AI-heavy codebase.

---

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

Start with a one-line verdict, then counts, then findings grouped by severity. Example:

```
## RN Review — shipping risk: HIGH · 1 BLOCKER · 2 HIGH · 1 MEDIUM

### BLOCKER
- `src/screens/Feed.tsx:42` — `onSuccess` in `useQuery` removed in TanStack Query v5.
  Fix: move to `useMutation.onSuccess` or a `useEffect` watching `data`.

### HIGH
- `src/components/Card.tsx:18` — `<View ref={cardRef}>` without `collapsable={false}`.
  New Architecture view flattening makes this ref always null.
  Fix: `<View ref={cardRef} collapsable={false}>`

- `src/screens/Home.tsx:55` — `useEffect(() => setFiltered(items.filter(fn)), [items])`.
  Derives state in an effect. Compute `filtered` during render instead.

### MEDIUM
- `src/hooks/useData.ts:12` — `useCallback` with empty deps. React Compiler handles this — remove.
```

**Shipping risk** = BLOCKED (any BLOCKER) · HIGH (any HIGH) · MEDIUM (MEDIUMs only) · CLEAN (INFO only or none).

Omit severity levels with zero findings. Skip INFO unless it's the only finding.

## References

- `references/checklist.md` — full itemized checklist per category
- `references/ai-patterns.md` — AI-era defect patterns with "why it happens" explanations
- Related: `expo-react-native` skill (authoritative patterns reference)
