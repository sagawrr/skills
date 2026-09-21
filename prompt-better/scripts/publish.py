#!/usr/bin/env python3
"""Bind session traces into journal papers and a book-styled volume."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pb import dump_json, ensure_home, load_json, memory_home
from retrieve import read_traces

_SCRIPTS = Path(__file__).resolve().parent
SLUG_RE = re.compile(r"[^a-z0-9]+")


def book_resources() -> Path:
    if (_SCRIPTS / "book.css").exists():
        return _SCRIPTS
    return _SCRIPTS.parent / "resources"


def constitution_file() -> Path:
    for candidate in (
        _SCRIPTS.parent / "constitution.md",
        _SCRIPTS / "constitution.md",
    ):
        if candidate.exists():
            return candidate
    return _SCRIPTS.parent / "constitution.md"

REFERENCES = [
    (
        "Zhang, Q., et al. (2025). Agentic Context Engineering: Evolving Contexts "
        "for Self-Improving Language Models. arXiv:2510.04618."
    ),
    (
        "Sumers, T., et al. (2023). Cognitive Architectures for Language Agents. "
        "arXiv:2309.02427."
    ),
    (
        "Park, J. S., et al. (2023). Generative Agents: Interactive Simulacra of "
        "Human Behavior. arXiv:2304.03442."
    ),
    (
        "Zhao, A., et al. (2023). ExpeL: LLM Agents Are Experiential Learners. "
        "arXiv:2308.10144."
    ),
    (
        "Shinn, N., et al. (2023). Reflexion: Language Agents with Verbal "
        "Reinforcement Learning. arXiv:2303.11366."
    ),
    (
        "Suzgun, M., et al. (2025). Dynamic Cheatsheet: Test-Time Learning with "
        "Adaptive Memory. arXiv:2504.07952."
    ),
    (
        "Xu, W., et al. (2025). A-Mem: Agentic Memory for LLM Agents. "
        "arXiv:2502.12110."
    ),
    (
        "Wang, Z. Z., et al. (2024). Agent Workflow Memory. arXiv:2409.07429."
    ),
]


def slugify(text: str) -> str:
    slug = SLUG_RE.sub("-", text.lower()).strip("-")
    return (slug[:72] or "session")


def esc(text: Any) -> str:
    return html.escape(str(text or ""), quote=True)


def now_label() -> str:
    return datetime.now(timezone.utc).strftime("%d %B %Y")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def group_sessions(traces: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trace in traces:
        key = str(trace.get("session") or "untitled session")
        grouped[key].append(trace)
    return grouped


def session_stats(turns: list[dict[str, Any]]) -> dict[str, Any]:
    routes = Counter(str(t.get("route") or "review") for t in turns)
    outcomes = Counter(str(t.get("outcome") or "neutral") for t in turns)
    skills = Counter(str(t.get("named_skill") or "none") for t in turns)
    return {
        "turns": len(turns),
        "routes": routes,
        "outcomes": outcomes,
        "skill": skills.most_common(1)[0][0] if skills else "none",
        "helpful": outcomes.get("helpful", 0),
        "harmful": outcomes.get("harmful", 0),
        "started": turns[0].get("ts") if turns else None,
        "ended": turns[-1].get("ts") if turns else None,
    }


def abstract_for(anchor: str, stats: dict[str, Any]) -> str:
    quoted = anchor.rstrip(".")
    return (
        f"This laboratory note records one Prompt Better session whose anchor was "
        f"“{quoted}.” {stats['turns']} classified follow-ups were routed; "
        f"{stats['helpful']} were scored helpful and {stats['harmful']} harmful "
        f"against the prior route. The note is a supporting paper for the named "
        f"skill `{stats['skill']}`: it states what performed, what drifted, and "
        f"which lived lesson the curator kept."
    )


def graph_svg(edges: dict[str, Any]) -> str:
    if not edges:
        return '<p class="muted">No associative edges yet.</p>'
    routes: list[str] = []
    reactions: list[str] = []
    parsed: list[tuple[str, str, dict[str, Any]]] = []
    for key, edge in edges.items():
        if "|" not in key:
            continue
        route, reaction = key.split("|", 1)
        parsed.append((route, reaction, edge))
        if route not in routes:
            routes.append(route)
        if reaction not in reactions:
            reactions.append(reaction)
    height = max(160, 28 * max(len(routes), len(reactions), 1) + 24)
    width = 640
    parts = [
        f'<svg class="graph" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img">'
    ]
    for i, route in enumerate(routes):
        y = 24 + i * 28
        parts.append(f'<text x="8" y="{y}">{esc(route)}</text>')
    for j, reaction in enumerate(reactions):
        y = 24 + j * 28
        parts.append(f'<text x="{width - 8}" y="{y}" text-anchor="end">{esc(reaction)}</text>')
    for route, reaction, edge in parsed:
        y1 = 20 + routes.index(route) * 28
        y2 = 20 + reactions.index(reaction) * 28
        harmful = int(edge.get("harmful") or 0)
        helpful = int(edge.get("helpful") or 0)
        stroke = "#6f2d2d" if harmful > helpful else "#241c14"
        width_n = 0.6 + 0.35 * (helpful + harmful)
        parts.append(
            f'<line x1="120" y1="{y1}" x2="{width - 200}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{width_n:.2f}" '
            f'stroke-opacity="0.7" />'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{esc(c)}</td>" for c in row)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def sheet(
    *,
    ident: str,
    running_left: str,
    running_right: str,
    folio: int,
    inner: str,
    extra_class: str = "",
) -> str:
    klass = f"sheet {extra_class}".strip()
    return f"""
<article class="{klass}" id="{esc(ident)}">
  <div class="running"><span>{esc(running_left)}</span><span>{esc(running_right)}</span></div>
  {inner}
  <div class="folio">{folio}</div>
</article>
"""


def paper_markdown(
    *,
    title: str,
    anchor: str,
    stats: dict[str, Any],
    turns: list[dict[str, Any]],
    bullets: list[dict[str, Any]],
    reflections: list[dict[str, Any]],
) -> str:
    turn_lines = [
        f"| {i} | {t.get('route')} | {t.get('reaction') or '—'} | {t.get('outcome') or '—'} | {t.get('follow_up') or ''} |"
        for i, t in enumerate(turns, 1)
    ]
    bullet_lines = [
        f"- `{b.get('id')}` ({b.get('applies')} / {b.get('when')}): {b.get('lesson')} "
        f"[helpful {b.get('helpful', 0)} / harmful {b.get('harmful', 0)}]"
        for b in bullets
        if b.get("active", True)
    ] or ["- None yet."]
    return f"""# {title}

**Skill.** `{stats['skill']}`
**Turns.** {stats['turns']}
**Outcomes.** helpful {stats['helpful']} · harmful {stats['harmful']}

## Abstract

{abstract_for(anchor, stats)}

## 1. Introduction

Anchor: {anchor}

## 2. Method

Follow-ups were classified with classifier.dev on fidelity, effort, performance, and reaction. Routing followed Prompt Better. Lived bullets were retrieved by recency, importance, and relevance. The curator merged deltas; it did not rewrite SKILL.md.

## 3. Trajectory

| Turn | Route | Reaction | Outcome | Follow-up |
| --- | --- | --- | --- | --- |
{chr(10).join(turn_lines)}

## 4. Results

Lived lessons active while this session ran:

{chr(10).join(bullet_lines)}

## 5. Discussion

Helpful reactions mean the last route held the floor. Harmful execute reactions are remaining width — the user had to babysit — not a request for a smarter model. Harmful pause reactions are over-cautious facilitation. Drift is a different job.

## References

{chr(10).join(f"{i}. {ref}" for i, ref in enumerate(REFERENCES, 1))}
"""


def paper_html_inner(
    *,
    title: str,
    anchor: str,
    stats: dict[str, Any],
    turns: list[dict[str, Any]],
    bullets: list[dict[str, Any]],
    session_reflections: list[dict[str, Any]],
    chapter: str,
) -> str:
    rows = [
        [
            i,
            t.get("route") or "",
            t.get("reaction") or "—",
            t.get("outcome") or "—",
            t.get("follow_up") or "",
        ]
        for i, t in enumerate(turns, 1)
    ]
    bullet_rows = [
        [
            b.get("id"),
            b.get("applies"),
            b.get("when"),
            f"{b.get('helpful', 0)}/{b.get('harmful', 0)}",
            b.get("lesson"),
        ]
        for b in bullets
        if b.get("active", True)
    ]
    refl = ""
    if session_reflections:
        notes = " ".join(str(r.get("note") or "") for r in session_reflections)
        refl = f"<h2>Reflections</h2><p>{esc(notes)}</p>"
    discussion = (
        "Where reactions were helpful, the last route held the floor. "
        "Harmful execute reactions are remaining width — the user had to babysit — "
        "not a request for a smarter model. Harmful pause reactions are over-cautious "
        "facilitation. Drift is a different job. The better next prompt is the one "
        "that would have avoided the harmful edge without dropping the named skill."
    )
    return f"""
<p class="kicker">Chapter {esc(chapter)} · Laboratory note</p>
<h1>{esc(title)}</h1>
<p class="subtitle">A supporting paper for <em>{esc(stats['skill'])}</em></p>
<p class="meta">{esc(stats.get('started') or '')} — {esc(stats.get('ended') or '')} · {stats['turns']} turns</p>
<p class="abstract">{esc(abstract_for(anchor, stats))}</p>
<p class="keywords"><strong>Keywords.</strong> {esc(', '.join(stats['routes'].keys()) or 'unrouted')}; attribution; lived playbook</p>
<h2>1. Introduction</h2>
<p>The session opened with this anchor:</p>
<blockquote>{esc(anchor)}</blockquote>
<h2>2. Method</h2>
<p>Each follow-up was classified with classifier.dev on four dimensions: fidelity to the anchor, effort required, whether the last action performed, and the user’s reaction to the prior route. Routing used the Prompt Better table. Curation was deterministic. Constitution.md was not rewritten.</p>
<h2>3. Trajectory</h2>
{table(["Turn", "Route", "Reaction", "Outcome", "Follow-up"], rows)}
<h2>4. Results</h2>
<p>Helpful {stats['helpful']} · Harmful {stats['harmful']} · Neutral {stats['outcomes'].get('neutral', 0)}.</p>
{table(["Id", "Applies", "When", "H/H", "Lesson"], bullet_rows) if bullet_rows else '<p class="muted">No lived bullets yet.</p>'}
{refl}
<h2>5. Discussion</h2>
<p>{esc(discussion)}</p>
"""


def bibliography_inner() -> str:
    items = "".join(f"<li>{esc(ref)}</li>" for ref in REFERENCES)
    return f"""
<p class="kicker">Apparatus</p>
<h1>References</h1>
<p class="subtitle">The papers this press is built from, not a literature review of the user’s domain.</p>
<ol class="refs">{items}</ol>
"""


def copy_resources(book_dir: Path) -> None:
    book_dir.mkdir(parents=True, exist_ok=True)
    for name in ("book.css", "book.js"):
        src = book_resources() / name
        if src.exists():
            shutil.copy2(src, book_dir / name)


def roman(n: int) -> str:
    table = [
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out = ""
    rest = n
    for value, glyph in table:
        while rest >= value:
            out += glyph
            rest -= value
    return out or "I"


def publish(home: Path) -> dict[str, Any]:
    home = ensure_home(home)
    traces = read_traces(home, limit=4000)
    graph = load_json(home / "graph.json", {"edges": {}, "turns": 0, "nodes": {}})
    lived = load_json(home / "lived.json", {"bullets": []})
    reflections = load_jsonl(home / "reflections.jsonl")
    bullets = lived.get("bullets") or []
    sessions = group_sessions(traces)
    book_dir = home / "book"
    papers_dir = home / "papers"
    book_dir.mkdir(parents=True, exist_ok=True)
    papers_dir.mkdir(parents=True, exist_ok=True)
    copy_resources(book_dir)

    folio = 1
    sheets: list[str] = []
    toc: list[tuple[str, str]] = []
    catalog: list[dict[str, Any]] = []

    cover = f"""
<div class="cover">
  <div>
    <p class="kicker">Prompt Better Press</p>
    <h1>Laboratory Notes</h1>
    <p class="subtitle">Session papers from classified follow-ups, lived lessons, and associative traces.</p>
    <p class="meta">Printed {esc(now_label())} · {len(sessions)} session{'' if len(sessions) == 1 else 's'} · {len(traces)} turns</p>
  </div>
  <p class="ornament">* * *</p>
  <p>The loop is the skill. This book is the press. Traces remain the source of truth.</p>
</div>
"""
    sheets.append(
        sheet(
            ident="cover",
            running_left="Prompt Better",
            running_right="Laboratory Notes",
            folio=folio,
            inner=cover,
            extra_class="cover-sheet",
        )
    )
    toc.append(("cover", "Title page"))
    folio += 1

    constitution = constitution_file()
    constitution_text = (
        constitution.read_text(encoding="utf-8")
        if constitution.exists()
        else "Constitution unavailable."
    )
    cons_paras = "".join(
        f"<p>{esc(line)}</p>"
        for line in constitution_text.splitlines()
        if line.strip() and not line.startswith("#")
    )
    sheets.append(
        sheet(
            ident="constitution",
            running_left="Prompt Better",
            running_right="Front matter",
            folio=folio,
            inner=f'<p class="kicker">Front matter</p><h1>Constitution</h1><p class="subtitle">These rules cannot be rewritten by heal.</p>{cons_paras}',
        )
    )
    toc.append(("constitution", "Constitution"))
    folio += 1

    atlas_inner = f"""
<p class="kicker">Atlas</p>
<h1>Associative graph</h1>
<p class="subtitle">Route to reaction. Oxblood lines lean harmful; ink lines lean helpful.</p>
{graph_svg(graph.get("edges") or {})}
{table(
    ["Edge", "Helpful", "Harmful", "Neutral"],
    [
        [key, edge.get("helpful", 0), edge.get("harmful", 0), edge.get("neutral", 0)]
        for key, edge in sorted((graph.get("edges") or {}).items())
    ],
)}
"""
    sheets.append(
        sheet(
            ident="atlas",
            running_left="Prompt Better",
            running_right="Atlas",
            folio=folio,
            inner=atlas_inner,
        )
    )
    toc.append(("atlas", "Atlas"))
    folio += 1

    index_rows = [
        [
            b.get("id"),
            b.get("applies"),
            b.get("when"),
            f"{b.get('helpful', 0)}/{b.get('harmful', 0)}",
            "active" if b.get("active", True) else "invalid",
            b.get("lesson"),
        ]
        for b in bullets
    ]
    sheets.append(
        sheet(
            ident="lessons",
            running_left="Prompt Better",
            running_right="Index of lessons",
            folio=folio,
            inner=(
                '<p class="kicker">Index</p><h1>Lived playbook</h1>'
                '<p class="subtitle">Semantic memory. Do not summarize these into a shorter rule.</p>'
                + (
                    table(["Id", "Applies", "When", "H/H", "State", "Lesson"], index_rows)
                    if index_rows
                    else '<p class="muted">No lived bullets yet.</p>'
                )
            ),
        )
    )
    toc.append(("lessons", "Index of lessons"))
    folio += 1

    for index, (session, turns) in enumerate(sessions.items(), 1):
        stats = session_stats(turns)
        title = session if len(session) < 88 else session[:85] + "…"
        slug = slugify(session)
        chapter = roman(index)
        inner = paper_html_inner(
            title=title,
            anchor=str(turns[0].get("anchor_head") or session),
            stats=stats,
            turns=turns,
            bullets=bullets,
            session_reflections=reflections,
            chapter=chapter,
        )
        ident = f"session-{slug}"
        sheets.append(
            sheet(
                ident=ident,
                running_left="Laboratory Notes",
                running_right=f"Ch. {chapter}",
                folio=folio,
                inner=inner,
            )
        )
        toc.append((ident, f"Ch. {chapter}. {title}"))
        md = paper_markdown(
            title=title,
            anchor=str(turns[0].get("anchor_head") or session),
            stats=stats,
            turns=turns,
            bullets=bullets,
            reflections=reflections,
        )
        (papers_dir / f"{slug}.md").write_text(md, encoding="utf-8")
        standalone = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="../book/book.css" />
</head>
<body style="display:block;background:var(--paper)">
{sheet(ident=ident, running_left="Laboratory Notes", running_right="Paper", folio=1, inner=inner)}
</body>
</html>
"""
        (papers_dir / f"{slug}.html").write_text(standalone, encoding="utf-8")
        catalog.append(
            {
                "id": ident,
                "slug": slug,
                "title": title,
                "skill": stats["skill"],
                "turns": stats["turns"],
                "helpful": stats["helpful"],
                "harmful": stats["harmful"],
                "markdown": str(papers_dir / f"{slug}.md"),
                "html": str(papers_dir / f"{slug}.html"),
            }
        )
        folio += 1

    sheets.append(
        sheet(
            ident="references",
            running_left="Prompt Better",
            running_right="References",
            folio=folio,
            inner=bibliography_inner(),
        )
    )
    toc.append(("references", "References"))

    spine_bits = ['<p class="brand">Prompt Better Press</p>']
    for ident, label in toc:
        spine_bits.append(f'<a href="#{esc(ident)}">{esc(label)}</a>')
    book = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Prompt Better · Laboratory Notes</title>
  <link rel="stylesheet" href="book.css" />
</head>
<body>
  <nav class="spine">{''.join(spine_bits)}</nav>
  <div class="stack">
    {''.join(sheets)}
  </div>
  <script src="book.js"></script>
</body>
</html>
"""
    (book_dir / "index.html").write_text(book, encoding="utf-8")
    dump_json(home / "catalog.json", {"printed": now_label(), "sessions": catalog})
    return {
        "ok": True,
        "book": str(book_dir / "index.html"),
        "papers": len(catalog),
        "sessions": catalog,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Prompt Better sessions as papers.")
    parser.add_argument("--out", help="Override memory home.")
    args = parser.parse_args()
    home = Path(args.out).expanduser() if args.out else memory_home()
    result = publish(home)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
