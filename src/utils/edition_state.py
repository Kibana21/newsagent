from __future__ import annotations
import json
from pathlib import Path
from typing import Any

LAST_EDITION_PATH = Path("state/last_edition.json")


def save_last_edition(edition_date: str, top_url: str, top_headline: str) -> None:
    LAST_EDITION_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_EDITION_PATH.write_text(json.dumps({
        "date": edition_date,
        "top_url": top_url,
        "top_headline": top_headline,
    }, indent=2))


def load_last_edition() -> dict[str, Any] | None:
    if not LAST_EDITION_PATH.exists():
        return None
    try:
        return json.loads(LAST_EDITION_PATH.read_text())  # type: ignore[no-any-return]
    except Exception:
        return None
