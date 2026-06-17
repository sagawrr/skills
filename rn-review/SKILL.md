---
name: rn-review
description: Reviews a React Native or Expo PR diff for correctness, performance, AI-era anti-patterns, and maintainability issues. Outputs inline findings with file:line citations and a severity-ranked summary. Use when asked to review a PR, audit a diff, or check code before merging. Specifically tuned for AI-generated code defects that pass visual inspection but break at runtime.
---

# React Native PR Review

Specialized review for React Native / Expo codebases. Complements the generic `/code-review` skill — run this one first when the project uses React Native.

## How to Run

```
/rn-review           # reviews current git diff (staged + unstaged)
/rn-review --fix     # applies safe mechanical fixes after review
/rn-review --comment # posts findings as inline GitHub PR comments
```

1. Get the diff: `git diff main...HEAD` (or `git diff --staged` for pre-commit)
2. Run each checklist category from `references/checklist.md` as a parallel scan
3. Cite every finding as `file.tsx:line — [SEVERITY] description`
4. Output a ranked summary: BLOCKER → HIGH → MEDIUM → INFO
5. If `--fix` flag: apply mechanical fixes (BLOCKER + HIGH only, no architectural changes)
6. If `--comment` flag: post findings as inline PR comments via GitHub MCP

## Severity Definitions

| Severity | Meaning | Block merge? |
|---|---|---|
| BLOCKER | Crashes, data loss, security, broken on New Architecture | Yes |
| HIGH | Perf regression, wrong API version, bad useEffect | Should |
| MEDIUM | Maintainability, style, suboptimal pattern | No |
| INFO | Suggestion, better alternative exists | No |

## What This Catches That Generic Review Misses

AI tools produce a specific class of defect: **code that looks correct but uses wrong library versions, removed APIs, or patterns that break silently on New Architecture**. This review is tuned for exactly those failure modes.

| AI defect | Example |
|---|---|
| Hallucinated API | `onSuccess` in `useQuery` — removed in TanStack Query v5 |
| Wrong Reanimated version | `runOnJS` — removed in Reanimated 4 |
| New Architecture breakage | Ref on flattened view → always null without `collapsable={false}` |
| Batching regression | Component relies on intermediate state that batching now eliminates |
| NativeWind v4/v5 mismatch | `jsxImportSource: 'nativewind'` in Babel config when v5 is installed |
| Deprecated FlashList prop | `estimatedItemSize` on FlashList v2 |
| Over-memoization | `useMemo`/`useCallback` added speculatively by AI with no perf evidence |
| useEffect for derived state | `useEffect(() => setState(compute(x)), [x])` — extra render, stale frame |
| Expo Router routing error | Component file placed in `app/` instead of `components/` |
| Wrong image library | `import { Image } from 'react-native'` instead of `expo-image` |

## Checklist Categories

Run these in parallel. Each is detailed in `references/checklist.md`.

1. **New Architecture correctness** — batching, refs, Fabric-safe patterns
2. **Reanimated 4** — `runOnJS`, worklet safety, animation properties
3. **API version correctness** — TanStack Query v5, FlashList v2, SDK 53–56 changes
4. **useEffect audit** — every `useEffect` in the diff needs justification
5. **List rendering** — FlashList setup, recycling, item stability
6. **Type safety** — `any`, type assertions, missing return types on exported functions
7. **Bundle impact** — barrel imports, new heavy deps, unused imports
8. **Expo Router conventions** — file placement, layout files, route structure
9. **NativeWind** — v4 vs v5 config, mobile gotchas, cascade assumptions
10. **Maintainability** — file size, component complexity, AI bloat patterns

## Output Format

```
## Review: <branch-name> → main
**N findings: B blockers, H high, M medium, I info**

### BLOCKER
- `src/screens/Feed.tsx:42` — `onSuccess` callback in `useQuery` does not exist in TanStack Query v5.
  Replace: `useMutation.onSuccess` or a `useEffect` watching `data`.

### HIGH
- `src/components/Card.tsx:18` — `ref` on `<View>` without `collapsable={false}`. New Architecture
  view flattening will make this ref always null.
  Fix: `<View ref={ref} collapsable={false}>`

- `src/screens/List.tsx:67` — `useEffect(() => setFiltered(items.filter(fn)), [items])` derives state
  inside an effect. Compute `filtered` directly during render.

### MEDIUM
- `src/hooks/useData.ts:12` — `useCallback` with empty deps on a function that doesn't close over anything.
  React Compiler handles this — remove the manual wrapper.

### INFO
- `src/components/Avatar.tsx:5` — `import { Image } from 'react-native'`. Prefer `expo-image` for
  caching, blurhash placeholder, and recyclingKey support in lists.
```

## Automated PR Comments (GitHub Actions)

```yaml
# .github/workflows/rn-review.yml
name: RN Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: anthropics/claude-code-action@v1
        with:
          prompt: |
            Run /rn-review --comment on this PR diff.
            Focus on: New Architecture correctness, Reanimated 4, API version mismatches,
            useEffect misuse, FlashList v2, type safety.
          allowed_tools: "Bash,Read,mcp__github_inline_comment__create_inline_comment"
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## References

- `references/checklist.md` — full itemized checklist for each category
- `references/ai-patterns.md` — AI-era anti-patterns with detection patterns and fixes
- Related skills: `expo-react-native` (patterns reference), `code-review` (generic review)
