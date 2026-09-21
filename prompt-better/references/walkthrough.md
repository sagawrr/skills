# Walkthrough

How the pieces fit. The skill does the work. The press binds the evidence. Neither rewrites the other.

## 1. First turn

The user names a prompt and a skill. That is the **anchor**. Prompt Better does not classify. It does the job at the named skill’s quality bar.

## 2. Every follow-up (inner loop)

`scripts/classify-turn.py` sends a redacted digest to classifier.dev:

- fidelity, effort, performance → a **route**
- reaction to `last_route` → helpful / harmful / neutral

Routes: `execute`, `deepen`, `simplify`, `repair`, `pause`, `restart`, `review`.

The agent does the work the route allows, then one teaching sentence. Vague follow-ups are not answered vaguely. Extras are named before they are built. Remaining distance on the same job (verify, evidence of done) is width, not drift.

## 3. Memory

| Layer | File | Role |
| --- | --- | --- |
| Working | `working.json` | Current anchor, last route, `used_ids` |
| Episodic | `traces.jsonl` | Turns, `prev_ts` |
| Semantic | `lived.json`, `notes/pb-*.md` | Itemized lessons, greppable |
| Session header | `one-pager.md` | Dated recap and index |
| Procedural | `SKILL.md`, `constitution.md` | Frozen policy |
| Associative | `graph.json` | Route → reaction counts |
| Reflection | `reflections.jsonl` | Every 8 turns, counts only |

Home: `~/Library/Application Support/prompt-better/` (`PROMPT_BETTER_HOME` overrides). Never committed.

## 4. Outer loop (self-heal)

The next user message is ground truth, not classifier confidence.

After the same `(prior_route, reaction)` pair lands three times, the curator inserts a lived bullet. Retrieval returns a few on-route lessons. SKILL.md is never rewritten. Inspect with `python3 scripts/inspect.py`. Publish only if they ask.

## 5. The press (separate app)

The Mac app is not this skill. It lives in `prompt-better-press` (sibling of the skills repo). It **reads** the memory home and **prints** a book. It does not classify, and it does not heal.

```bash
python3 scripts/publish.py
cd ../prompt-better-press && make app && make run
```

## 6. What each surface is for

| Surface | Use |
| --- | --- |
| `SKILL.md` | What the agent does this turn |
| `constitution.md` | What heal and retrieval cannot override |
| `examples.md` | Route illustrations |
| `references/self-heal.md` | Papers and memory map |
| `scripts/classify-turn.py` | Inner + outer loop |
| `scripts/inspect.py` | CLI snapshot |
| `scripts/publish.py` | Bind papers (optional; not required to route) |

## 7. Attribution

| User behavior | Means | Not |
| --- | --- | --- |
| Confirms stay / split | Route was right | |
| Restates after a plausible diff | Last turn failed the floor; remaining width | Need a smarter model |
| Corrects the artifact | Work miss | Routing failure |
| `just do it` after pause | Over-cautious facilitation | |
| Ignores the teaching note | Voice failure | Need a longer lecture |
