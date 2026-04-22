from __future__ import annotations
from typing import Any
from src.state import AgentState
from src.utils.text import title_similarity
from src.utils.state_io import recent_urls


def aggregate_node(state: AgentState) -> dict[str, Any]:
    raw: list[dict[str, Any]] = []
    per_source: dict[str, int] = {}
    for field in ("rss_news", "arxiv_news", "github_news",
                  "hf_news", "hn_news", "reddit_news", "youtube_news"):
        items: list[Any] = list(state.get(field) or [])  # type: ignore[arg-type, call-overload]
        per_source[field.replace("_news", "")] = len(items)
        raw.extend(items)

    # URL dedup
    seen_urls: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in raw:
        u = (item.get("url") or "").strip().rstrip("/").lower()
        if not u or u in seen_urls:
            continue
        seen_urls.add(u)
        deduped.append(item)

    # Filter against rolling 7-day sent_urls window
    recent = recent_urls(days=7)
    filtered = [i for i in deduped if (i.get("url") or "").strip().rstrip("/").lower() not in recent]

    # Buzz scoring: count near-duplicate titles (title_similarity >= 0.9)
    buzz: dict[str, int] = {}
    for i, item in enumerate(filtered):
        t_i = item.get("title", "")
        count = sum(
            1 for j, other in enumerate(filtered)
            if i != j and len(t_i) >= 20 and title_similarity(t_i, other.get("title", "")) >= 0.9
        ) + 1
        buzz[item.get("url", "")] = count
        item["buzz_score"] = count

    print(f"[aggregate] per_source={per_source} raw={len(raw)} deduped={len(deduped)} after_filter={len(filtered)}")
    return {"raw_news": filtered, "buzz_scores": buzz}
