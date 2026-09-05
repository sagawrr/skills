![Skills banner](banner.jpg)

# Skills

[![skills.sh](https://skills.sh/b/sagawrr/skills)](https://skills.sh/sagawrr/skills)

Each skill is a focused instruction set that helps an AI agent do one kind of work better — less repeated setup, sharper judgment, and more consistent results across tools and agent environments.

## Install

Install all skills:

```bash
npx skills add sagawrr/skills
```

Install one skill:

```bash
npx skills add sagawrr/skills --skill expo-react-native
```

## Skills

### React Native & Expo

| Skill | Purpose |
| --- | --- |
| [`expo-react-native`](expo-react-native/SKILL.md) | Hardened code patterns for Expo and React Native — state, animations, lists, forms, and styling. Covers useEffect replacements, Zustand, TanStack Query, Reanimated, FlashList, NativeWind, React Hook Form + Zod, and New Architecture gotchas. |
| [`rn-review`](rn-review/SKILL.md) | PR review skill for React Native — scans diffs for broken APIs, New Architecture breakage, AI-generated anti-patterns, and maintainability issues. Run with `/rn-review` before merging. |

### Remote Dev Previews

| Skill | Purpose |
| --- | --- |
| [`k16-preview`](k16-preview/SKILL.md) | Run, browse, or share dev-server previews on a headless Linux box (via herdr) — LAN URL, off-LAN ssh tunnel, or an ephemeral public link via Cloudflare quick tunnels. Idempotent managed start, DNS-fallback verification, and clean teardown so nothing stays exposed. |

### Writing & Communication

| Skill | Purpose |
| --- | --- |
| [`write-better-error-messages`](write-better-error-messages/SKILL.md) | Write and review useful product error messages that explain what happened, provide a recovery path, and avoid blame or jargon. |
