from __future__ import annotations
from datetime import date
from typing import Any
from src.state import AgentState
from src.utils.state_io import load_sent_urls, save_sent_urls

RAW_INDEX_MARKER = "<details>"


def _strip_raw_index(md: str) -> str:
    idx = md.find(RAW_INDEX_MARKER)
    return md[:idx].rstrip() if idx >= 0 else md


def _write_sent_urls(state: AgentState) -> None:
    entries = load_sent_urls()
    today = date.today().isoformat()
    curated = list(state.get("curated_news") or [])  # type: ignore[arg-type]
    for item in curated:
        url = (item.get("url") or "").strip().rstrip("/").lower()
        if not url:
            continue
        entries.append({
            "url": url,
            "sent_at": today,
            "title": item.get("title", ""),
            "buzz_score": item.get("buzz_score", 1),
            "insurance_score": item.get("insurance_score", 1),
        })
    save_sent_urls(entries)


def email_node(state: AgentState) -> dict[str, Any]:
    # SMTP delivery disabled — report saved to reports/ by main.py.
    # Still write sent_urls so dedup works on subsequent runs.
    print("[email] writing sent_urls.json...")
    _write_sent_urls(state)
    print("[email] done — report saved to reports/, sent_urls updated")
    return {"email_log": {"status": "skipped", "subscribers_found": 0, "emails_sent": 0, "errors": []}}
