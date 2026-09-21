# Prompt Better examples

Each example assumes the first turn already ran. Anchor is captured. The follow-up is classified, then handled.

## On-track refinement → `execute`

**Anchor:** Add empty-state copy to checkout when the cart is empty.
**Last action:** Wrote three empty-state variants.
**Follow-up:** Also mention that saved drafts are still in the cart.

Do the copy change. One sentence: that constraint stayed inside the original job.

Weak version of the same ask: `make it better` — that would have been `deepen`.

## Vague follow-up → `deepen`

**Follow-up:** `fix it` / `make it better` / `continue` with no target.

Do not reply in kind. Re-read the anchor, raise quality, ship a complete pass.

Teach: "`make it better` usually gets a cheap pass. Name the gap: `The empty state still doesn't say whether the draft cart was kept.`"

## Silent drift → `pause`

**Follow-up:** While you are here, restyle the checkout button and rewrite the heading font.

The job is copy. Restyle is adjacent-sounding and off-goal. Do not do it unless they confirm a goal change.

Teach: "Related work is still a different job. Ask for the copy fix, then open styling as its own prompt."

## Scope escalation → `pause`

**Follow-up:** Also rebuild payments, auth, and the cart reducer.

Name the jump. Finish any remaining empty-state copy. Do not start the rebuild.

Offer three paths: stay on the anchor, split into a new task, or explicitly replace the goal.

## Last turn did not perform → `repair`

**Last action:** Refactored unrelated button styles and did not change empty-state copy.
**Follow-up:** The empty state still says Something went wrong.

Fix the empty state. Say that last turn was activity, not progress.

## Width vs drift

**Anchor:** Empty-state copy, then show it working.
**Follow-up:** The copy is in. Did you check the empty cart?

That is remaining width on the same job (`repair` or keep `execute`), not a new surface. Verify. Do not pause.

**Not the same:** While you are here, restyle the checkout button. That is drift. Pause.

## Additive new task → `restart` then pause

**Follow-up:** Can you also add a dark mode toggle to settings?

Do not mix. Dark mode is not a follow-up. Ask them to split it.

## Replaced job → `restart` then execute

**Follow-up:** Ignore that. Write a SQL migration for user roles.

They discarded the anchor. Re-anchor to the migration and do it in the same turn.

## Outer loop (self-heal)

The next user message is scored as a reaction to `last_route`. After the same pair lands three times, a lived bullet is added. Next time that route fires, the script returns it in `lived` and you obey it.

**Pattern:** `pause` then `just do it`, three times.

Lived bullet: if the extra ask stays on the same surface as the anchor, execute that slice and skip the confirm.

**Pattern:** `execute` then the user restates the same ask.

Lived bullet: treat the restatement as `repair`. Last execute did not perform.

Inspect with `python3 scripts/inspect.py`. Publish only if they asked.

Pass `used_ids` from `lived` on the next classify call.
