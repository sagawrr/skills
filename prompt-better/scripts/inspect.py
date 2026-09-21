#!/usr/bin/env python3
"""Print working memory, graph, reflections, and the lived playbook."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pb import load_json, memory_home, render_lived
from retrieve import read_traces


def main() -> int:
    home = memory_home()
    graph = load_json(home / "graph.json", {})
    lived = load_json(home / "lived.json", {"bullets": []})
    working = load_json(home / "working.json", {})
    traces = read_traces(home, limit=8)
    print(f"memory_home: {home}")
    print(f"turns: {graph.get('turns', 0)}")
    if working:
        print(
            "working: "
            + json.dumps(
                {
                    "session": working.get("session"),
                    "last_route": working.get("last_route"),
                    "used_ids": working.get("used_ids"),
                },
                ensure_ascii=False,
            )
        )
    print("edges:")
    for key, edge in sorted((graph.get("edges") or {}).items()):
        print(
            f"  {key}: helpful={edge.get('helpful', 0)} "
            f"harmful={edge.get('harmful', 0)} neutral={edge.get('neutral', 0)}"
        )
    print(f"recent_traces: {len(traces)}")
    pager = home / "one-pager.md"
    if pager.exists():
        print(f"one_pager: {pager}")
    notes = home / "notes"
    if notes.is_dir():
        print(f"notes: {len(list(notes.glob('pb-*.md')))} files")
    book = home / "book" / "index.html"
    if book.exists():
        print(f"book: {book}")
    print()
    print(render_lived(lived), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
