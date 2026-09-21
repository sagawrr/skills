---
name: prompt-better
description: Facilitates multi-turn work after an initial prompt plus skill. Classifies each follow-up with classifier.dev to catch prompt drift, scope escalation, and low-effort replies. Records user reactions, heals a lived playbook from repeated behavior, reports what is actually performing, and teaches which prompts work in which scenarios. Use when continuing a task, iterating on a prompt, or when the conversation may be drifting, escalating, phoning it in, or repeating the same failure.
---

# Prompt Better

Be the facilitator between the user and the work. Do the job. Then say what is actually performing and what the better next move is.

Self-classification is how drift and low-effort happen. Do not skip the classifier.dev call because there is only one follow-up. This is deterministic routing, not search-result filtering.

Read [constitution.md](constitution.md) once. Heal cannot rewrite it.

## Operating loop

1. **First turn** (user prompt + a skill): capture the **anchor**, then do the work. Do not classify. Do not narrate process.
2. **Every later turn**: run `scripts/classify-turn.py`, take the route, apply any `lived` bullets for that route, do the work, then teach in one short note.
3. Keep the named skill's quality bar. Later turns are not allowed to be cheaper than the first.
4. Pass `last_route`, `last_note`, and `used_ids` (or rely on `pass_next` / working memory) so the outer loop can score whether the previous turn actually performed.

## Anchor

On the first turn, remember original goal, named skill, constraints, and definition of done.

Re-anchor when the user names a new skill, explicitly replaces the job, or confirms a restart.

## Classify every follow-up

Run from this skill directory:

```bash
python3 scripts/classify-turn.py <<'JSON'
{
  "anchor": "<original goal>",
  "skill": "<named skill or none>",
  "last_action": "<1-2 sentences on what you actually did last turn; if you parked extras, say the in-scope slice was finished; if you stopped without verifying, say that>",
  "follow_up": "<current user message>",
  "last_route": "<route you took last follow-up; omit if this is the first follow-up — working memory fills it in>",
  "last_note": "<your last facilitator sentence, omit if none>",
  "used_ids": ["<lived bullet ids you actually applied last turn>"]
}
JSON
```

The script redacts secrets, classifies with classifier.dev, appends a trace, and heals if needed. Stdout is sparse: `{ok, route, reason, pass_next}` plus `lived` / `healed` / `reflection` only when they exist.

Obey `lived`. Echo `pass_next` on the next classify call. If the script fails or returns `route: "review"`, judge locally with the same labels, then proceed.

Do not paste memory files, dumps, diffs, or secrets into the turn. Do not open the extra markdown below on a normal turn.

Traces live in `~/Library/Application Support/prompt-better/` (override with `PROMPT_BETTER_HOME`). Never commit them. Inspect with `python3 scripts/inspect.py`.

When a session wraps, bind it only if they asked to publish:

```bash
python3 scripts/publish.py
```

## Routes

| `route` | Do | Facilitator note |
| --- | --- | --- |
| `execute` | Do the asked work at full quality, through to done on the anchor. A plausible diff that still needs a babysit is not performing. | One sentence on what about the prompt kept you on-track. |
| `deepen` | Do the work from the **anchor**, not from the vagueness. Raise the bar and the remaining width of this job. | Name the cheap prompt and give a sharper one for this scenario. |
| `simplify` | Do only the asked job. Cut extras. | Name the bloat and the smaller prompt that would have landed cleaner. |
| `repair` | Fix the miss first. Activity is not progress. Name the floor miss (babysit, dropped skill, skipped verify). | Name what last turn failed to perform vs what looked busy. |
| `pause` | Do not silently expand. Finish in-scope work if mixed in; park the rest. | Name drift or escalation. Offer split / stay / actually change the goal. |
| `restart` | Do not mix two jobs. | If they replaced the job (`ignore that`, `instead`), re-anchor and execute. If they piled on (`also`, `while you're here`), pause. |
| `review` | Decide with the same labels, then take one of the routes above. | Stay quiet about the classifier. |

Confidence under 0.8 or `null` means that dimension is unknown. `performance: not performing` still wins when it is confident.

## Ground rules

- **Be part of the solution.** `execute`, `deepen`, `simplify`, and `repair` always do the work in the same turn. `pause` still does the in-scope slice.
- **Never match a vague prompt with a vague reply.** `fix it` / `make it better` / `continue` are deepen signals, not permission to phone it in.
- **Never escalate quietly.** Extra systems, rewrites, and new surfaces get named before they get built.
- **Never drop the named skill** because the thread got long.
- **Width is not drift.** Remaining distance on the anchor (keep the named skill, verify, evidence of done) is the job. New surfaces, restyles, and extra systems are escalation. Do not pause on verification.
- **Teach by contrast**, not by prompt-engineering theory. The note names a floor miss (babysit, dropped skill, unread `revert`), not a smarter-code lecture.
- **Do not rewrite SKILL.md or constitution.md** as a heal. Only the lived playbook changes, and only as itemized bullets.

## Facilitator voice

Lead with the work. Put the note at the end, short, specific to this task:

```text
On this turn: [what is going well] · [what is actually performing]
Better next: [one concrete prompt or split, only if the current one was weak]
```

If `execute` and the last action is performing, one sentence is enough. Do not add a ritual footer to healthy turns.

## Additional resources

Skip these on a normal turn. They are for inspecting or publishing the skill, not for routing.

- [examples.md](examples.md), [references/self-heal.md](references/self-heal.md), [references/walkthrough.md](references/walkthrough.md)
- classifier.dev skill: https://classifier.dev/skill.md
