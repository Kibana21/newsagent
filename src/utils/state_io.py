from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

PATH = Path("state/sent_urls.json")


def load_sent_urls() -> list[dict[str, Any]]:
    if not PATH.exists():
        return []
    try:
        return json.loads(PATH.read_text())  # type: ignore[no-any-return]
    except Exception:
        return []


def prune_sent_urls(entries: list[dict[str, Any]], days: int = 30) -> list[dict[str, Any]]:
    cutoff = date.today() - timedelta(days=days)
    kept = []
    for e in entries:
        try:
            if date.fromisoformat(e["sent_at"]) >= cutoff:
                kept.append(e)
        except Exception:
            continue
    return kept


def save_sent_urls(entries: list[dict[str, Any]]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    pruned = prune_sent_urls(entries, days=30)
    PATH.write_text(json.dumps(pruned, indent=2))


def recent_urls(days: int = 7) -> set[str]:
    cutoff = date.today() - timedelta(days=days)
    seen: set[str] = set()
    for e in load_sent_urls():
        try:
            if date.fromisoformat(e["sent_at"]) >= cutoff:
                seen.add(e["url"].rstrip("/").lower())
        except Exception:
            continue
    return seen
