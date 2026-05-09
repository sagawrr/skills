---
name: write-better-error-messages
description: Draft, rewrite, audit, and systematize product error messages so they explain what happened, avoid blame and jargon, reassure users, provide a clear recovery path, and expose cases that need engineering or product investigation. Use when asked to improve error copy, empty/error states, validation messages, toast alerts, form errors, API failure messages, fallback "something went wrong" messages, customer-facing incident copy, or product guidelines for error handling.
---

# Write Better Error Messages

## Overview

Use error messages as product recovery tools. Based on Wix UX's "When life gives you lemons, write better error messages": good errors explain what happened, why if known, what is safe, what to do next, and where to go if the user cannot recover. Treat error handling as shared product, engineering, design, data, support, and UX writing work.

## Operating Loop

1. Gather only the context needed to write truthfully.
2. Classify the current issue: generic, unclear, blameful, jargon-heavy, dead-end, or wrong tone.
3. Decide whether copy can fix it or whether product/engineering must map causes, impact, recovery, or instrumentation.
4. Rewrite with the helpful-error structure.
5. Return improved copy plus follow-ups for anything copy cannot responsibly solve.

## Context Needed

Before rewriting, look for or ask for:

- Trigger: What condition causes it?
- User goal: What was the user trying to do?
- Impact: What did or did not happen?
- Safety: Were changes, money, orders, messages, or data saved, queued, rolled back, or lost?
- Recovery: Can the user retry, edit input, reconnect, refresh, wait, contact support, or take another path?
- Ownership: Is it validation, permissions, connectivity, payment, third-party integration, backend failure, rate limit, or unknown fallback?
- Priority: How often does it happen, and does it block the flow?

If the cause is unknown, do not invent one. Write a truthful fallback and recommend mapping or instrumentation.

## Bad Patterns

Flag messages with these problems:

- Cutesy tone in a high-stakes moment: "Oops!", "Uh oh!", "Yikes!"
- Technical jargon: "fetch failed", "credentials denied", "500", "unprocessable entity", "timeout exception"
- Blame: "You entered the wrong...", "Your account caused...", "Stripe is not responding"
- Generic wording when the system knows more: "Something went wrong"
- False certainty: claiming the issue is fixed by retrying when it might persist
- Dead ends: no next step, contact path, or alternative
- Missing reassurance: leaving users unsure whether work, money, orders, or data were affected
- Unclear explanations: words are present, but the user still cannot tell what happened

## Helpful Structure

Use this order unless the product surface has strong local conventions:

1. State what happened in user language.
2. Explain why, only as specifically as the product can truthfully support.
3. Reassure the user about what was not affected, when known.
4. Give the best next action.
5. Provide a way out if the user cannot fix it.

Compact formula:

```text
We couldn't [complete user goal] because [plain-language reason]. [Safety reassurance.] [Specific next step or support path.]
```

Common patterns:

```text
System-side:
We couldn't [complete action] because of an issue on our end. [Safety reassurance.] Try again in a few minutes, or contact support if this keeps happening.

Validation:
[Field/value] needs [specific requirement]. [Example or correction.]

Permission:
You do not have permission to [action]. Ask an admin to update your access, or switch to an account with permission.

Integration:
We're having trouble connecting to [service]. Reconnect your account or try again later.
```

Avoid third-party blame such as "[service] isn't responding." Prefer "We're having trouble connecting to..."

## Tone Rules

- Be calm, direct, and respectful.
- Match severity. Avoid playful language for payments, publishing, data loss, account access, health, legal, or income-impacting workflows.
- Do not over-apologize. One apology can fit severe or unrecoverable situations, but clarity matters more.
- Use "please" sparingly for high-friction asks, support handoffs, or cases the product cannot resolve for the user.
- Focus on the problem and recovery, not on the user's mistake.
- Prefer active, concrete verbs: "Check", "Reconnect", "Try again", "Contact support".

## Audit Output

For audits, use a concise table:

| Current message | Issue | Better message | Follow-up |
| --- | --- | --- | --- |
| Something went wrong | Generic; no recovery | We couldn't save your changes because of an issue on our end. Your draft is still saved. Try again in a few minutes. | Confirm draft state and add retry tracking. |

Use `Follow-up` for instrumentation, support routing, UI changes, missing state knowledge, or cases where copy depends on engineering investigation.

For single-message rewrites, return:

```text
Better message: ...
Why: ...
Follow-up: ...
```

## Prioritize

When auditing many errors, rank first by flow-blocking severity, frequency, trust impact, known cause hidden behind generic copy, and cross-functional effort needed. Trust-impacting errors include money, publishing, orders, user data, access, compliance, or safety.

Recommend a one-month post-launch review for new products or flows that currently rely on generic fallback messages.

## Ask When Needed

Use these when copy cannot be responsibly written from available context:

- What exact condition triggers this message?
- Is the user's work saved, partially saved, queued, or discarded?
- Can the user fix this themselves?
- Is retrying useful, and after how long?
- Is this a user-side, system-side, permission, validation, or integration issue?
- Can we split this generic error into more specific cases?
- How often does this happen, and where in the flow?
- What support path should users use if it persists?

## Final Check

Before finalizing, confirm:

- The message answers "what happened?"
- It answers "why?" when known.
- It avoids jargon, blame, and cute tone.
- It gives a realistic next step.
- It reassures users where possible.
- It includes a way out for unrecoverable or recurring failures.
- It identifies product, data, or engineering work when copy alone is not enough.
