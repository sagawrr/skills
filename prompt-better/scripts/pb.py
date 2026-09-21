"""Shared classify, memory, and heal logic for prompt-better."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from retrieve import (
    bullet_budget,
    competing_ids,
    maybe_reflect,
    retrieve_bullets,
    should_deactivate,
)

ENDPOINT = "https://classifier.dev/v1/classify"
USER_AGENT = "prompt-better/1.0 (sagawrr/skills)"
CONFIDENT = 0.8
MAX_ANCHOR = 800
MAX_ACTION = 400
MAX_FOLLOW = 800
MAX_NOTE = 240
MAX_BULLETS = 24
ADD_THRESHOLD = 3
MAX_EVIDENCE = 8
SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|bearer|authorization)\b\s*[:=]\s*\S+"
)
WIDTH_ASK_RE = re.compile(
    r"(?i)("
    r"did you (check|test|verify|run|look)|"
    r"does it (work|pass)|"
    r"did it (work|pass)|"
    r"still (broken|wrong|not|missing|says)|"
    r"you stopped|"
    r"babysit|"
    r"is it done|"
    r"show (me )?(it|that) working|"
    r"you didn't (check|test|verify)"
    r")"
)

ROUTE_DIMENSIONS = {
    "fidelity": {
        "labels": [
            "faithful to original",
            "useful refinement",
            "silent drift",
            "scope escalation",
            "new task",
        ],
        "instructions": (
            "Compare FOLLOW-UP to ANCHOR. Faithful: same goal, including yes keep going. "
            "Useful refinement: a specific in-scope addition, including 'did you check' / "
            "verify remaining distance on the same job. Silent drift: a related-sounding "
            "change that is not the asked job, such as restyling while the job is copy. "
            "Scope escalation: the job grows to extra systems or large extra scope. "
            "New task: a different job. Verification of the asked job is not drift."
        ),
    },
    "effort": {
        "labels": [
            "execute fully",
            "deepen the work",
            "simplify the work",
            "pause and confirm",
            "restart clean",
        ],
        "instructions": (
            "Execute fully for a specific in-scope ask or a clear yes keep going. "
            "Deepen the work for vague asks such as fix it or make it better so the reply "
            "is not cheap. Simplify when the follow-up is bloated. Pause and confirm for "
            "scope escalation (extra systems, restyles), not for tests of the asked job. "
            "Restart clean for a new task."
        ),
    },
    "performance": {
        "labels": [
            "working well",
            "partially working",
            "not performing",
            "too little evidence",
        ],
        "instructions": (
            "Judge LAST ACTION against ANCHOR. Working well means it advanced the asked job "
            "or correctly parked extra scope. Not performing means it missed the asked job, "
            "or shipped a plausible diff that still needed a babysit (FOLLOW-UP asks whether "
            "it was checked, tested, or finished). Parking extras is not a miss. "
            "Too little evidence if LAST ACTION is missing."
        ),
    },
}

REACTION_DIMENSION = {
    "reaction": {
        "labels": [
            "confirmed the last route",
            "continued the work",
            "corrected the work",
            "rejected the route",
            "asked to just do it",
            "repeated the same ask",
            "started a new job",
            "too little evidence",
        ],
        "instructions": (
            "Judge FOLLOW-UP against LAST ROUTE only. "
            "Confirmed the last route: they accept the decision (stay, split, or re-anchor). "
            "Continued the work: a normal next in-scope ask, not a complaint. "
            "Corrected the work: last output missed the job. "
            "Rejected the route: they disagree with pause, restart, or deepen as a decision. "
            "Asked to just do it: skip confirmation and teaching, execute. "
            "Repeated the same ask: restating because it was not done, including "
            "'did you check' after execute — remaining width, not a new job. "
            "Started a new job: discarded the old job. "
            "Too little evidence if this cannot be judged."
        ),
    }
}

HELPFUL_PAIRS = {
    ("pause", "confirmed the last route"),
    ("restart", "confirmed the last route"),
    ("execute", "continued the work"),
    ("execute", "confirmed the last route"),
    ("deepen", "continued the work"),
    ("repair", "continued the work"),
    ("repair", "confirmed the last route"),
    ("simplify", "continued the work"),
}

HARMFUL_PAIRS = {
    ("pause", "asked to just do it"),
    ("pause", "rejected the route"),
    ("restart", "asked to just do it"),
    ("restart", "rejected the route"),
    ("deepen", "asked to just do it"),
    ("execute", "repeated the same ask"),
    ("execute", "corrected the work"),
    ("execute", "rejected the route"),
    ("repair", "repeated the same ask"),
}

LESSONS: dict[tuple[str, str], str] = {
    ("pause", "asked to just do it"): (
        "Pause was over-cautious for this user. If the extra ask stays on the same "
        "surface as the anchor, execute that slice and skip the confirm."
    ),
    ("pause", "rejected the route"): (
        "Naming extras is landing as a blocker. Do the in-scope work in the same turn "
        "and park the rest in one sentence, without waiting."
    ),
    ("pause", "confirmed the last route"): (
        "Pause was the right facilitation. Keep naming extras before building them."
    ),
    ("restart", "asked to just do it"): (
        "Restart confirm is friction. If they already replaced the job, re-anchor and "
        "execute in the same turn."
    ),
    ("restart", "rejected the route"): (
        "They wanted the new job mixed in. Still do not mix; start the new job as the "
        "anchor and say the old one is parked."
    ),
    ("restart", "confirmed the last route"): (
        "Clean re-anchor is working. Keep refusing to mix two jobs."
    ),
    ("deepen", "asked to just do it"): (
        "The teaching note is noise. Raise quality silently and keep the facilitator "
        "line to one short contrast, or drop it."
    ),
    ("deepen", "continued the work"): (
        "Deepen then a specific follow-up is a healthy pattern. Keep refusing to match "
        "vague with vague."
    ),
    ("execute", "repeated the same ask"): (
        "Last execute did not perform. The user had to intervene. Treat a restated "
        "ask as repair, close remaining distance on the same job, and do not start "
        "another execute pass."
    ),
    ("execute", "corrected the work"): (
        "Activity was not progress. A plausible diff that still needed a babysit "
        "failed the floor. Check the anchor and verify before shipping."
    ),
    ("execute", "rejected the route"): (
        "Execute was the wrong call. Re-read fidelity: this may have been drift or a "
        "new task that should have paused."
    ),
    ("execute", "continued the work"): (
        "On-track execute is performing. Keep the facilitator note to one sentence."
    ),
    ("repair", "repeated the same ask"): (
        "Repair still missed. Stop restyling around the miss; do the asked artifact. "
        "Name the signal that led the last turn astray (skipped verify, dropped skill)."
    ),
    ("repair", "confirmed the last route"): (
        "Calling out a miss and fixing it is landing. Keep naming busy vs performing."
    ),
    ("simplify", "continued the work"): (
        "Cutting extras is landing. Keep executing only the asked job."
    ),
}

ALIASES: dict[tuple[str, str], list[str]] = {
    ("pause", "asked to just do it"): [
        "just do it",
        "skip confirm",
        "over-cautious",
        "while you're here",
        "also rebuild",
    ],
    ("pause", "rejected the route"): [
        "don't ask",
        "stop pausing",
        "just ship",
        "blocker",
    ],
    ("pause", "confirmed the last route"): [
        "stay on the anchor",
        "split it",
        "name extras",
        "scope escalation",
    ],
    ("restart", "asked to just do it"): [
        "ignore that",
        "instead",
        "new job",
        "skip restart confirm",
    ],
    ("restart", "rejected the route"): [
        "also do both",
        "mix the jobs",
        "don't mix",
    ],
    ("restart", "confirmed the last route"): [
        "new task",
        "re-anchor",
        "clean restart",
    ],
    ("deepen", "asked to just do it"): [
        "ok whatever",
        "just ship it",
        "skip the lecture",
        "make it better",
    ],
    ("deepen", "continued the work"): [
        "vague",
        "fix it",
        "name the gap",
    ],
    ("execute", "repeated the same ask"): [
        "still not done",
        "do it again",
        "same ask",
        "repair not execute",
        "babysit",
        "you stopped",
    ],
    ("execute", "corrected the work"): [
        "that's not what I asked",
        "busy not performing",
        "missed the job",
    ],
    ("execute", "rejected the route"): [
        "wrong call",
        "should have paused",
        "drift",
    ],
    ("execute", "continued the work"): [
        "on-track",
        "keep going",
        "one sentence",
    ],
    ("repair", "repeated the same ask"): [
        "still missed",
        "stop restyling",
        "asked artifact",
        "led it astray",
        "skipped verify",
    ],
    ("repair", "confirmed the last route"): [
        "calling out a miss",
        "busy vs performing",
    ],
    ("simplify", "continued the work"): [
        "cut extras",
        "only the asked job",
    ],
}


def clip(text: str, limit: int) -> str:
    text = SECRET_RE.sub("[redacted]", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def memory_home() -> Path:
    override = os.environ.get("PROMPT_BETTER_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "prompt-better"
    return Path.home() / ".local" / "share" / "prompt-better"


def ensure_home(home: Path | None = None) -> Path:
    path = home or memory_home()
    path.mkdir(parents=True, exist_ok=True)
    return path


def digest(payload: dict[str, Any]) -> str:
    skill = clip(str(payload.get("skill") or "none"), 80)
    anchor = clip(str(payload.get("anchor") or ""), MAX_ANCHOR)
    last_action = clip(str(payload.get("last_action") or ""), MAX_ACTION)
    follow_up = clip(str(payload.get("follow_up") or ""), MAX_FOLLOW)
    last_route = clip(str(payload.get("last_route") or ""), 40)
    last_note = clip(str(payload.get("last_note") or ""), MAX_NOTE)
    if not follow_up:
        raise ValueError("follow_up is required")
    lines = [
        f"ANCHOR: {anchor or '(missing)'}",
        f"SKILL: {skill}",
        f"LAST ACTION: {last_action or '(none)'}",
    ]
    if last_route:
        lines.append(f"LAST ROUTE: {last_route}")
    if last_note:
        lines.append(f"LAST NOTE: {last_note}")
    lines.append(f"FOLLOW-UP: {follow_up}")
    lines.append(
        "RULE: remaining distance on the same job (check, test, verify, still broken) "
        "is width, not drift. Extra systems and restyles are drift."
    )
    return "\n".join(lines)


def confident_label(field: dict[str, Any] | None) -> str | None:
    if not field:
        return None
    confidence = field.get("confidence")
    label = field.get("label")
    if label in {None, "too little evidence"}:
        return None
    if confidence is None or confidence < CONFIDENT:
        return None
    return str(label)


def route_for(dims: dict[str, Any]) -> tuple[str, str]:
    fidelity = confident_label(dims.get("fidelity"))
    effort = confident_label(dims.get("effort"))
    performance = confident_label(dims.get("performance"))

    if performance == "not performing":
        return "repair", "Last action missed the anchor."
    if fidelity == "new task" or effort == "restart clean":
        return "restart", "Follow-up is a different job."
    if (
        fidelity in {"scope escalation", "silent drift"}
        or effort == "pause and confirm"
    ):
        return "pause", "Follow-up grows or redirects the job."
    if effort == "deepen the work":
        return "deepen", "Follow-up is too vague for a cheap reply."
    if effort == "simplify the work":
        return "simplify", "Follow-up is bloated; stay on the anchor."
    if effort == "execute fully" or fidelity in {
        "faithful to original",
        "useful refinement",
    }:
        return "execute", "Follow-up stays on the asked job."
    return "review", "Classifier was unsure; judge locally with the same labels."


def width_ask(follow_up: str) -> bool:
    return bool(WIDTH_ASK_RE.search(follow_up or ""))


def apply_reaction_override(
    route: str,
    reason: str,
    prior_route: str | None,
    reaction: str | None,
    follow_up: str = "",
) -> tuple[str, str, str | None]:
    if (
        width_ask(follow_up)
        and prior_route in {"execute", "deepen", "repair"}
        and reaction in {None, "continued the work", "confirmed the last route"}
    ):
        reaction = "repeated the same ask"
    if reaction == "repeated the same ask" or reaction == "corrected the work":
        return "repair", "They said the last output missed the job.", reaction
    if reaction == "asked to just do it" and prior_route in {
        "pause",
        "restart",
        "deepen",
    }:
        return "execute", "They rejected confirmation; do the parked ask.", reaction
    if reaction == "rejected the route" and prior_route == "pause":
        return (
            "execute",
            "They rejected the pause; do the work without waiting.",
            reaction,
        )
    return route, reason, reaction


def outcome_for(prior_route: str | None, reaction: str | None) -> str | None:
    if not prior_route or not reaction:
        return None
    pair = (prior_route, reaction)
    if pair in HELPFUL_PAIRS:
        return "helpful"
    if pair in HARMFUL_PAIRS:
        return "harmful"
    return "neutral"


def classify(text: str, include_reaction: bool) -> dict[str, Any]:
    dimensions = dict(ROUTE_DIMENSIONS)
    if include_reaction:
        dimensions.update(REACTION_DIMENSION)
    body = json.dumps(
        {"items": [text], "dimensions": dimensions},
        ensure_ascii=False,
    ).encode()
    last_error: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "content-type": "application/json",
                "user-agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            last_error = exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if exc.code in {429, 502, 503} and attempt < 2:
                wait = 2.0
                if retry_after:
                    try:
                        wait = min(max(float(retry_after), 1.0), 20.0)
                    except ValueError:
                        pass
                time.sleep(wait)
                continue
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"classifier.dev HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2.0)
                continue
            raise RuntimeError(f"classifier.dev unreachable: {exc}") from exc
    raise RuntimeError(f"classifier.dev failed: {last_error}")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)


def compact_dims(dims: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {"label": field.get("label"), "confidence": field.get("confidence")}
        for name, field in dims.items()
        if name != "reaction"
    }


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_trace(home: Path, trace: dict[str, Any]) -> None:
    append_jsonl(home / "traces.jsonl", trace)


def update_graph(
    home: Path,
    *,
    route: str,
    prior_route: str | None,
    reaction: str | None,
    outcome: str | None,
    ts: str,
) -> dict[str, Any]:
    path = home / "graph.json"
    graph = load_json(
        path,
        {"updated_at": ts, "turns": 0, "nodes": {}, "edges": {}},
    )
    graph["updated_at"] = ts
    graph["turns"] = int(graph.get("turns") or 0) + 1
    nodes: dict[str, Any] = graph.setdefault("nodes", {})
    route_key = f"route:{route}"
    nodes.setdefault(route_key, {"kind": "route", "count": 0})
    nodes[route_key]["count"] += 1
    if prior_route and reaction and outcome:
        prior_key = f"route:{prior_route}"
        nodes.setdefault(prior_key, {"kind": "route", "count": 0})
        react_key = f"reaction:{reaction}"
        nodes.setdefault(react_key, {"kind": "reaction", "count": 0})
        nodes[react_key]["count"] += 1
        edge_key = f"{prior_route}|{reaction}"
        edges: dict[str, Any] = graph.setdefault("edges", {})
        edge = edges.setdefault(
            edge_key,
            {"helpful": 0, "harmful": 0, "neutral": 0, "last_at": ts},
        )
        edge[outcome] = int(edge.get(outcome) or 0) + 1
        edge["last_at"] = ts
    dump_json(path, graph)
    return graph


def render_lived(lived: dict[str, Any]) -> str:
    lines = [
        "# Lived playbook",
        "",
        "Apply these on top of SKILL.md. Do not summarize them away. "
        "Do not rewrite constitution.md from here. Memory is read-only for the agent.",
        "",
    ]
    active = [b for b in lived.get("bullets", []) if b.get("active", True)]
    if not active:
        lines.append("No lived bullets yet. Keep routing from SKILL.md.")
        lines.append("")
        return "\n".join(lines)
    for bullet in active:
        aliases = ", ".join(str(a) for a in (bullet.get("aliases") or []))
        links = " ".join(f"[[{link}]]" for link in (bullet.get("links") or []))
        lines.append(f"- [[{bullet['id']}]] type: lesson")
        lines.append(
            f"  applies: `{bullet['applies']}` after `{bullet['when']}` "
            f"(helpful {bullet.get('helpful', 0)} / harmful {bullet.get('harmful', 0)})"
        )
        if aliases:
            lines.append(f"  aliases: {aliases}")
        lines.append(f"  {bullet['lesson']}")
        if links:
            lines.append(f"  related: {links}")
        lines.append("")
    return "\n".join(lines)


def write_notes(home: Path, lived: dict[str, Any]) -> None:
    notes = home / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    keep: set[str] = set()
    for bullet in lived.get("bullets", []):
        ident = str(bullet.get("id") or "")
        if not ident:
            continue
        keep.add(ident)
        aliases = bullet.get("aliases") or []
        alias_line = ", ".join(str(a) for a in aliases)
        links = " ".join(f"[[{link}]]" for link in (bullet.get("links") or []))
        stated = str(bullet.get("valid_at") or "")[:10]
        invalid = bullet.get("invalid_at")
        body = [
            "---",
            f"id: {ident}",
            "type: lesson",
            f"applies: {bullet.get('applies')}",
            f"when: {bullet.get('when')}",
            f"aliases: [{alias_line}]",
            f"active: {str(bullet.get('active', True)).lower()}",
            "---",
            "",
            f"- **Lesson:** {bullet.get('lesson')}",
            f"- **Stated:** {stated}",
            f"- **Helpful / harmful:** {bullet.get('helpful', 0)} / {bullet.get('harmful', 0)}",
        ]
        if links:
            body.append(f"- **Related:** {links}")
        corrections = list(bullet.get("corrections") or [])
        if invalid and not corrections:
            body.append(f"- **Dated correction:** invalidated {str(invalid)[:10]}")
        for correction in corrections:
            note = clip(str(correction.get("note") or ""), 160)
            when = str(correction.get("ts") or "")[:10]
            if note:
                body.append(f"- **Dated correction:** {when} — {note}")
        body.append("")
        (notes / f"{ident}.md").write_text("\n".join(body), encoding="utf-8")
    for leftover in notes.glob("pb-*.md"):
        if leftover.stem not in keep:
            leftover.unlink()


def persist_lived(home: Path, lived: dict[str, Any]) -> None:
    for bullet in lived.get("bullets", []):
        if bullet.get("aliases"):
            continue
        key = (str(bullet.get("applies") or ""), str(bullet.get("when") or ""))
        aliases = ALIASES.get(key)
        if aliases:
            bullet["aliases"] = list(aliases)
    dump_json(home / "lived.json", lived)
    (home / "lived.md").write_text(render_lived(lived), encoding="utf-8")
    write_notes(home, lived)


def write_one_pager(
    home: Path,
    *,
    session: str,
    route: str,
    ts: str,
    graph: dict[str, Any],
    lived: dict[str, Any],
) -> str:
    edges = graph.get("edges") or {}
    ranked = sorted(
        edges.items(),
        key=lambda item: int((item[1] or {}).get("harmful") or 0),
        reverse=True,
    )
    autonomy = "No autonomy signal yet. Follow SKILL.md."
    if ranked:
        key, edge = ranked[0]
        harmful = int(edge.get("harmful") or 0)
        helpful = int(edge.get("helpful") or 0)
        prior = key.split("|", 1)[0] if "|" in key else ""
        if harmful > helpful:
            if prior == "execute":
                autonomy = (
                    f"This user restates after `{key}` ({harmful} harmful / {helpful} helpful). "
                    "Close remaining distance on the same job before they babysit. "
                    "Verification is width, not drift."
                )
            elif prior == "repair":
                autonomy = (
                    f"Repair still misses on `{key}` ({harmful} harmful / {helpful} helpful). "
                    "Do the asked artifact; a plausible diff is not done."
                )
            else:
                autonomy = (
                    f"This user often rejects `{key}` ({harmful} harmful / {helpful} helpful). "
                    "Prefer doing the in-scope slice without extra confirmation."
                )
        elif helpful:
            autonomy = (
                f"This user often confirms `{key}` ({helpful} helpful). "
                "Keep the facilitation that earned it."
            )
    active = [b for b in lived.get("bullets", []) if b.get("active", True)]
    index_lines = []
    for bullet in active[:12]:
        aliases = ", ".join(str(a) for a in (bullet.get("aliases") or [])[:4])
        extra = f" — {aliases}" if aliases else ""
        index_lines.append(
            f"- [[{bullet['id']}]] `{bullet.get('applies')}` / `{bullet.get('when')}`{extra}"
        )
    if not index_lines:
        index_lines.append("- (empty) grep `notes/` after lessons exist.")
    text = "\n".join(
        [
            "# One-pager",
            "",
            f"Printed {ts}. If this date is old, treat it as a hint, not gospel.",
            "",
            "## Autonomy",
            autonomy,
            "",
            "## Recap",
            f"- Session: {session or '(none)'}",
            f"- Last route this turn: `{route}`",
            f"- Turns recorded: {graph.get('turns', 0)}",
            "",
            "## Index",
            *index_lines,
            "",
            "Memory is read-only. Do not edit `notes/` or `lived.json` by hand.",
            "",
        ]
    )
    (home / "one-pager.md").write_text(text, encoding="utf-8")
    return autonomy


def heal(
    home: Path,
    *,
    prior_route: str | None,
    reaction: str | None,
    outcome: str | None,
    ts: str,
) -> list[dict[str, Any]]:
    if not prior_route or not reaction or outcome not in {"helpful", "harmful"}:
        return []
    path = home / "lived.json"
    lived = load_json(path, {"bullets": [], "next_id": 1})
    bullets: list[dict[str, Any]] = lived.setdefault("bullets", [])
    ops: list[dict[str, Any]] = []
    existing = next(
        (
            b
            for b in bullets
            if b.get("applies") == prior_route and b.get("when") == reaction
        ),
        None,
    )
    graph = load_json(home / "graph.json", {})
    edge = (graph.get("edges") or {}).get(f"{prior_route}|{reaction}") or {}
    helpful = int(edge.get("helpful") or 0)
    harmful = int(edge.get("harmful") or 0)
    edge_total = helpful + harmful

    if existing:
        existing["helpful"] = helpful
        existing["harmful"] = harmful
        evidence = list(existing.get("evidence") or [])
        evidence.append(ts)
        existing["evidence"] = evidence[-MAX_EVIDENCE:]
        existing["active"] = not should_deactivate(helpful, harmful)
        if not existing.get("aliases"):
            existing["aliases"] = list(ALIASES.get((prior_route, reaction), []))
        if not existing["active"] and not existing.get("invalid_at"):
            existing["invalid_at"] = ts
            existing.setdefault("corrections", []).append(
                {"ts": ts, "note": f"Invalidated after {harmful} harmful / {helpful} helpful."}
            )
            ops.append({"op": "correct", "id": existing["id"]})
        else:
            ops.append({"op": "update", "id": existing["id"], "outcome": outcome})
    elif edge_total >= ADD_THRESHOLD and (prior_route, reaction) in LESSONS:
        ident = f"pb-{int(lived.get('next_id') or 1):04d}"
        lived["next_id"] = int(lived.get("next_id") or 1) + 1
        links = [
            str(b["id"])
            for b in bullets
            if b.get("active", True) and b.get("applies") == prior_route
        ]
        bullet = {
            "id": ident,
            "applies": prior_route,
            "when": reaction,
            "lesson": LESSONS[(prior_route, reaction)],
            "helpful": helpful,
            "harmful": harmful,
            "used_helpful": 0,
            "used_harmful": 0,
            "active": True,
            "valid_at": ts,
            "invalid_at": None,
            "evidence": [ts],
            "links": links,
            "aliases": list(ALIASES.get((prior_route, reaction), [])),
            "corrections": [],
        }
        for other in bullets:
            if other.get("id") in links:
                other.setdefault("links", [])
                if ident not in other["links"]:
                    other["links"].append(ident)
        bullets.append(bullet)
        ops.append({"op": "add", "id": ident, "lesson": bullet["lesson"]})

    active = [b for b in bullets if b.get("active", True)]
    if len(active) > MAX_BULLETS:
        ranked = sorted(
            active,
            key=lambda b: (
                int(b.get("helpful") or 0) - int(b.get("harmful") or 0),
                int(b.get("helpful") or 0),
            ),
        )
        for victim in ranked[: len(active) - MAX_BULLETS]:
            victim["active"] = False
            victim["invalid_at"] = ts
            victim.setdefault("corrections", []).append(
                {"ts": ts, "note": "Pruned to keep the playbook under 24 active lessons."}
            )
            ops.append({"op": "prune", "id": victim["id"]})

    if ops:
        persist_lived(home, lived)
        with (home / "heal-log.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps({"ts": ts, "ops": ops}, ensure_ascii=False) + "\n"
            )
    return ops


def hydrate(payload: dict[str, Any], home: Path) -> dict[str, Any]:
    working = load_json(home / "working.json", {})
    session = clip(str(payload.get("session") or payload.get("anchor") or ""), 80)
    filled = dict(payload)
    if working.get("session") == session:
        if not filled.get("last_route") and working.get("last_route"):
            filled["last_route"] = working["last_route"]
        if not filled.get("last_note") and working.get("last_note"):
            filled["last_note"] = working["last_note"]
        if not filled.get("used_ids") and working.get("used_ids"):
            filled["used_ids"] = working["used_ids"]
        if not filled.get("skill") and working.get("skill"):
            filled["skill"] = working["skill"]
        if not filled.get("anchor") and working.get("anchor"):
            filled["anchor"] = working["anchor"]
    filled["_prev_ts"] = working.get("ts") if working.get("session") == session else None
    return filled


def credit_used(
    home: Path,
    used_ids: list[str],
    outcome: str | None,
    ts: str,
) -> None:
    if not used_ids or outcome not in {"helpful", "harmful"}:
        return
    path = home / "lived.json"
    lived = load_json(path, {"bullets": []})
    changed = False
    for bullet in lived.get("bullets", []):
        if bullet.get("id") not in used_ids:
            continue
        key = "used_helpful" if outcome == "helpful" else "used_harmful"
        bullet[key] = int(bullet.get(key) or 0) + 1
        changed = True
    if changed:
        persist_lived(home, lived)


def save_working(home: Path, working: dict[str, Any]) -> None:
    dump_json(home / "working.json", working)


def compact_bullet(bullet: dict[str, Any], competing: bool = False) -> dict[str, Any]:
    row = {"id": bullet["id"], "lesson": bullet["lesson"]}
    if competing:
        row["competing"] = True
    return row


def omit_empty(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None or value == [] or value == "" or value == {}:
            continue
        if isinstance(value, dict):
            nested = omit_empty(value)
            if nested:
                out[key] = nested
            continue
        out[key] = value
    return out


def run_turn(payload: dict[str, Any]) -> dict[str, Any]:
    home = ensure_home()
    payload = hydrate(payload, home)
    text = digest(payload)
    prior_route = clip(str(payload.get("last_route") or ""), 40) or None
    response = classify(text, include_reaction=bool(prior_route))
    dims = response["results"][0]["dimensions"]
    route, reason = route_for(dims)
    reaction_field = dims.get("reaction")
    reaction = confident_label(reaction_field)
    follow_up = clip(str(payload.get("follow_up") or ""), MAX_FOLLOW)
    route, reason, reaction = apply_reaction_override(
        route, reason, prior_route, reaction, follow_up
    )
    outcome = outcome_for(prior_route, reaction)
    ts = now_iso()
    named_skill = clip(str(payload.get("skill") or "none"), 80)
    session = clip(str(payload.get("session") or payload.get("anchor") or ""), 80)
    used_ids = payload.get("used_ids") or []
    if isinstance(used_ids, str):
        used_ids = [used_ids]
    credit_used(home, [str(i) for i in used_ids], outcome, ts)
    append_trace(
        home,
        {
            "ts": ts,
            "prev_ts": payload.get("_prev_ts"),
            "session": session,
            "named_skill": named_skill,
            "anchor_head": clip(str(payload.get("anchor") or ""), 120),
            "follow_up": follow_up,
            "route": route,
            "prior_route": prior_route,
            "reaction": reaction,
            "outcome": outcome,
        },
    )
    graph = update_graph(
        home,
        route=route,
        prior_route=prior_route,
        reaction=reaction,
        outcome=outcome,
        ts=ts,
    )
    healed = heal(
        home,
        prior_route=prior_route,
        reaction=reaction,
        outcome=outcome,
        ts=ts,
    )
    lived = load_json(home / "lived.json", {"bullets": []})
    bullets = lived.get("bullets", [])
    apply_now = retrieve_bullets(
        bullets,
        route=route,
        skill=named_skill,
        follow_up=follow_up,
        k=bullet_budget(route),
    )
    compete = set(competing_ids(bullets, prior_route or route, reaction))
    reflection = maybe_reflect(
        turns=int(graph.get("turns") or 0),
        edges=graph.get("edges") or {},
        ts=ts,
    )
    if reflection:
        append_jsonl(home / "reflections.jsonl", reflection)
    apply_ids = [str(b["id"]) for b in apply_now]
    write_one_pager(
        home,
        session=session,
        route=route,
        ts=ts,
        graph=graph,
        lived=lived,
    )
    save_working(
        home,
        {
            "ts": ts,
            "session": session,
            "anchor": clip(str(payload.get("anchor") or ""), MAX_ANCHOR),
            "skill": named_skill,
            "last_route": route,
            "last_note": "",
            "used_ids": apply_ids,
        },
    )
    packed: dict[str, Any] = {
        "ok": True,
        "route": route,
        "reason": reason,
        "reaction": {
            "label": (reaction_field or {}).get("label") if reaction_field else None,
            "confidence": (reaction_field or {}).get("confidence")
            if reaction_field
            else None,
            "outcome": outcome,
        },
        "lived": [compact_bullet(b, competing=b["id"] in compete) for b in apply_now],
        "reflection": reflection,
        "healed": healed,
        "pass_next": {
            "last_route": route,
            "used_ids": apply_ids,
            "session": session,
        },
    }
    if route == "review":
        packed["dimensions"] = compact_dims(dims)
    return omit_empty(packed)
