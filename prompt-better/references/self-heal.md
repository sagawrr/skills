# Self-heal

The inner loop fixes this turn. The outer loop rewrites the playbook when the same user behavior repeats. That is Argyris's double-loop learning: change the rules, not only the next action.

## The press is separate

A Graphiti-style knowledge graph sitting in another process cannot change the next reply. The loop stays in the skill. The Mac book **reads** traces, **binds** each session as a supporting paper, and **prints** a volume: constitution, atlas, lived index, chapters, references. It does not classify, and it does not heal.

```bash
python3 scripts/publish.py
open "$HOME/Library/Application Support/prompt-better/book/index.html"
```

Papers: `papers/{slug}.md` and `.html`. The Mac reader is a separate app (`prompt-better-press`), not part of this skill. Alignment of every surface: [walkthrough.md](walkthrough.md).

## Papers this loop is built from

| Paper | What we took | What we refused |
| --- | --- | --- |
| [ACE](https://arxiv.org/abs/2510.04618) (Zhang et al., 2025) | Generator / Reflector / Curator; itemized bullets; helpful/harmful; grow-and-refine; never rewrite the whole prompt | LLM curator. Deltas merge in Python. |
| [CoALA](https://arxiv.org/abs/2309.02427) (Sumers et al., 2023) | Working, episodic, semantic, procedural memory | A new cognitive-architecture product. |
| [Generative Agents](https://arxiv.org/abs/2304.03442) (Park et al., 2023) | Retrieval = recency + importance + relevance; periodic reflections | LLM importance scores. Importance is helpful−harmful. Reflections are count-based. |
| [ExpeL](https://arxiv.org/abs/2308.10144) (Zhao et al., 2023) | Insights as lived bullets; ADD/upvote/downvote via the graph | Embedding store; injecting similar sessions into the turn |
| [Reflexion](https://arxiv.org/abs/2303.11366) (Shinn et al., 2023) | Verbal lesson from a failure signal, stored for later trials | Retrying the same task in a hidden loop. The user's next message is the signal. |
| [Dynamic Cheatsheet](https://arxiv.org/abs/2504.07952) (Suzgun et al., 2025) | Cumulative strategies retrieved for this route | LLM-curated cheatsheet rewrites (ACE showed those collapse). |
| [A-MEM](https://arxiv.org/abs/2502.12110) (Xu et al., 2025) | Atomic notes, links, evolution when a new note arrives | LLM keyword/tag generation. Links are same-route bullets. |
| [AWM](https://arxiv.org/abs/2409.07429) (Wang et al., 2024) | Reusable routines induced from trajectories | A second LLM that invents workflows. Route sequences stay in traces. |

Psychology: Tulving (episodic vs semantic), Argyris (double loop), Weiner/Kelley (attribution), Ericsson (deliberate practice), Goodhart (do not treat confidence as success).

## Memory map

| Memory | File |
| --- | --- |
| Working | `working.json` — current anchor, last route, `used_ids` |
| Episodic | `traces.jsonl` — turns, linked by `prev_ts` |
| Semantic | `lived.json` / `lived.md` / `notes/pb-*.md` — bullets, greppable |
| Procedural | `SKILL.md` + `constitution.md` — frozen policy |
| Session header | `one-pager.md` — dated recap and index (stale is a hint) |
| Associative | `graph.json` — route → reaction counts |
| Reflections | `reflections.jsonl` — every 8 turns, count-based |

On macOS: `~/Library/Application Support/prompt-better/` (override `PROMPT_BETTER_HOME`). Never commit it.

Derived press output in that same home: `book/index.html`, `papers/*.md`, `catalog.json`.

## When a bullet appears

After the same `(prior_route, reaction)` pair happens 3 times, the curator inserts the matching lesson and links it to other bullets on that route. Later hits sync counters from the graph. A bullet deactivates when Wilson's lower bound on helpful rate drops below 0.25 (n≥5), or when `harmful ≥ 2× helpful` with `helpful < 2`. Cap is 24 active bullets. Deactivated bullets get `invalid_at` (Zep-style validity window).

ACE Generator highlighting: pass last turn's `used_ids`. Helpful/harmful reactions increment `used_helpful` / `used_harmful` on those bullets.

## Retrieval this turn

Lived bullets are ranked by recency, importance, and relevance to this follow-up, including alias hits (`just do it` → pause). At most two return on a healthy execute, three on pause/repair/restart. Constitution still wins.

## What the agent does with `lived`

Obey those lessons on this turn. Do not paraphrase them into a shorter rule. That is how context collapse starts. Constitution still wins.

## Instinct (Shah, 2026) — what we borrowed

[Dhravya Shah's reverse-engineering of Instinct](https://x.com/DhravyaShah/status/2101745550752428340) is personal-agent memory: git markdown, a profile, grep via aliases, a background writer. Prompt Better is procedural memory for *how this user routes work*, not who they are.

| Took | Left |
| --- | --- |
| Answering agent is read-only; curator writes | Life-context identity profile |
| Greppable markdown notes with aliases (`notes/pb-*.md`) | Vector / BM25 search, supermemory |
| One-pager (autonomy + recap + index), dated so stale copies are not trusted | 24-hour cron, git history as the store |
| Dated corrections when a lesson is invalidated | Daily/weekly personal timelines |
| Wiki-style `[[id]]` links | Todo board, channel style prefs |

We already had the better half of Instinct's scorecard: procedural / skill memory. Aliases exist so `just do it` hits the pause lesson without embeddings.

## Floor vs ceiling (Browne, 2026) — what we borrowed

[Theo Browne's reply to Cramer](https://x.com/theo/status/2101062549722841452) is that Fable/Astra are not "smarter code." They are less dumb for longer: a higher **floor** on wide prompts. Prompt Better already scores performing vs busy. The borrow is the width/drift split, not model shopping.

| Took | Left |
| --- | --- |
| Floor over ceiling: a babysit, dropped skill, or unread `revert` is the miss | Which model to buy; token cost vs salary |
| Width = remaining distance on the same anchor (verify, evidence of done) | Overnight Ralph loops, "stop naming files", 4-hour unattended runs as a goal |
| If later turns shrink a wide job, that is a floor miss (`repair`), not a successful execute | Treating every small Jira follow-up as a prompt that must get wider |
