#!/usr/bin/env python3
"""Classify a follow-up, record the trace, and heal the lived playbook."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pb import run_turn


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        "Pass JSON on stdin with anchor, skill, last_action, "
                        "follow_up. Include last_route and last_note after the first follow-up."
                    ),
                    "route": "review",
                }
            )
        )
        return 1
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("stdin must be a JSON object")
        print(json.dumps(run_turn(payload), ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 — agent needs any failure as JSON
        print(json.dumps({"ok": False, "error": str(exc), "route": "review"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
