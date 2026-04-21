from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import feedparser
from src.config import RSS_FEEDS
from src.state import AgentState, NewsItem


def rss_node(state: AgentState) -> dict[str, Any]:
    days = state.get("days", 2)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items: list[NewsItem] = []
    print(f"[rss] fetching {len(RSS_FEEDS)} feeds...")
    for name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    dt = datetime(pub[0], pub[1], pub[2], pub[3], pub[4], pub[5], tzinfo=timezone.utc)
                    if dt < cutoff:
                        continue
                    published_iso = dt.isoformat()
                else:
                    published_iso = ""
                items.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:500],
                    "source": "rss",
                    "published_at": published_iso,
                })
        except Exception as e:
            print(f"[rss_node] error on {name}: {e}")
    print(f"[rss] got {len(items[:8])} items")
    return {"rss_news": items[:8]}
