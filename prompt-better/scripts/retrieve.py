"""Retrieve lived bullets and optionally score a count-based reflection."""

from __future__ import annotations

import json
import math
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORD_RE = re.compile(r"[a-z0-9]+")
DECAY_PER_HOUR = 0.995
REFLECT_EVERY = 8
BULLET_K = 2
BULLET_K_STRESS = 3
TRACE_TAIL = 400

OPPOSITES: dict[tuple[str, str], tuple[str, str]] = {
    ("pause", "asked to just do it"): ("pause", "confirmed the last route"),
    ("pause", "rejected the route"): ("pause", "confirmed the last route"),
    ("pause", "confirmed the last route"): ("pause", "asked to just do it"),
    ("restart", "asked to just do it"): ("restart", "confirmed the last route"),
    ("restart", "confirmed the last route"): ("restart", "asked to just do it"),
    ("deepen", "asked to just do it"): ("deepen", "continued the work"),
    ("deepen", "continued the work"): ("deepen", "asked to just do it"),
    ("execute", "repeated the same ask"): ("execute", "continued the work"),
    ("execute", "corrected the work"): ("execute", "continued the work"),
    ("execute", "continued the work"): ("execute", "corrected the work"),
    ("repair", "repeated the same ask"): ("repair", "confirmed the last route"),
    ("repair", "confirmed the last route"): ("repair", "repeated the same ask"),
}


def tokenize(text: str) -> set[str]:
    return {w for w in WORD_RE.findall(text.lower()) if len(w) > 2}


def jaccard(left: str, right: str) -> float:
    a, b = tokenize(left), tokenize(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def hours_since(iso: str, now: datetime | None = None) -> float:
    if not iso:
        return 10_000.0
    stamp = iso.replace("Z", "+00:00")
    try:
        then = datetime.fromisoformat(stamp)
    except ValueError:
        return 10_000.0
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - then).total_seconds() / 3600.0)


def recency_score(iso: str) -> float:
    return DECAY_PER_HOUR ** hours_since(iso)


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = p + z2 / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def should_deactivate(helpful: int, harmful: int) -> bool:
    n = helpful + harmful
    if n >= 5 and wilson_lower(helpful, n) < 0.25:
        return True
    return harmful >= max(helpful * 2, 4) and helpful < 2


def read_traces(home: Path, limit: int = TRACE_TAIL) -> list[dict[str, Any]]:
    path = home / "traces.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        lines = deque(handle, maxlen=limit)
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def retrieve_bullets(
    bullets: list[dict[str, Any]],
    *,
    route: str,
    skill: str,
    follow_up: str,
    k: int = BULLET_K,
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for bullet in bullets:
        if not bullet.get("active", True):
            continue
        helpful = int(bullet.get("helpful") or 0)
        harmful = int(bullet.get("harmful") or 0)
        evidence = list(bullet.get("evidence") or [])
        last = evidence[-1] if evidence else str(bullet.get("valid_at") or "")
        recency = recency_score(last)
        n = helpful + harmful
        importance = (helpful - harmful) / n if n else 0.0
        importance = (importance + 1) / 2
        relevance = 0.0
        if bullet.get("applies") == route:
            relevance += 0.7
        if skill and bullet.get("skill") in {skill, None, "none"}:
            relevance += 0.1
        relevance += 0.2 * jaccard(str(bullet.get("lesson") or ""), follow_up)
        aliases = [str(a) for a in (bullet.get("aliases") or [])]
        if aliases:
            blob = " ".join(aliases)
            relevance += 0.15 * jaccard(blob, follow_up)
            lowered = follow_up.lower()
            hits = sum(1 for alias in aliases if alias.lower() in lowered)
            if hits:
                relevance += min(0.8, 0.4 * hits)
        if relevance < 0.5:
            continue
        score = recency + importance + relevance
        ranked.append((score, bullet))
    ranked.sort(key=lambda item: item[0], reverse=True)
    picked = [b for _, b in ranked[:k]]
    ids = {b["id"] for b in picked}
    linked: list[dict[str, Any]] = []
    by_id = {b["id"]: b for b in bullets if b.get("active", True)}
    for bullet in picked:
        for link in bullet.get("links") or []:
            other = by_id.get(link)
            if other and other["id"] not in ids:
                linked.append(other)
                ids.add(other["id"])
    return picked + linked[:1]


def bullet_budget(route: str) -> int:
    if route in {"pause", "repair", "restart"}:
        return BULLET_K_STRESS
    return BULLET_K


def competing_ids(bullets: list[dict[str, Any]], route: str, reaction: str | None) -> list[str]:
    if not reaction:
        return []
    opposite = OPPOSITES.get((route, reaction))
    if not opposite:
        return []
    applies, when = opposite
    return [
        str(b["id"])
        for b in bullets
        if b.get("active", True)
        and b.get("applies") == applies
        and b.get("when") == when
    ]


def maybe_reflect(
    *,
    turns: int,
    edges: dict[str, Any],
    ts: str,
) -> dict[str, Any] | None:
    if turns <= 0 or turns % REFLECT_EVERY != 0:
        return None
    ranked = []
    for key, edge in edges.items():
        harmful = int(edge.get("harmful") or 0)
        helpful = int(edge.get("helpful") or 0)
        ranked.append((harmful, helpful, key, edge))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    worst = ranked[0]
    best = max(ranked, key=lambda row: row[1])
    return {
        "ts": ts,
        "turns": turns,
        "watch": worst[2],
        "watch_harmful": worst[0],
        "watch_helpful": worst[1],
        "keep": best[2],
        "keep_helpful": best[1],
        "note": (
            f"Across {turns} turns, `{worst[2]}` is the most harmful edge "
            f"({worst[0]} harmful / {worst[1]} helpful). "
            f"`{best[2]}` is the most confirmed ({best[1]} helpful)."
            + (
                " Floor miss: close remaining width; do not pause on verification."
                if str(worst[2]).startswith("execute|")
                else (
                    " Over-cautious pause, not a request to go wider."
                    if str(worst[2]).startswith("pause|")
                    else ""
                )
            )
        ),
    }
