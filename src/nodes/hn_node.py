from __future__ import annotations
from typing import Any
import requests
from src.config import HN_KEYWORDS
from src.state import AgentState, NewsItem


def hn_node(state: AgentState) -> dict[str, Any]:
    try:
        print("[hackernews] fetching top stories...")
        r = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        )
        r.raise_for_status()
        ids = r.json()[:30]
        items: list[NewsItem] = []
        for sid in ids:
            s = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5
            ).json()
            title = (s.get("title") or "").lower()
            if not any(k in title for k in HN_KEYWORDS):
                continue
            items.append({
                "title": s.get("title", ""),
                "url": s.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                "summary": f"HN score {s.get('score', 0)} · {s.get('descendants', 0)} comments",
                "source": "hackernews",
                "published_at": "",
            })
            if len(items) >= 5:
                break
        print(f"[hackernews] got {len(items)} stories")
        return {"hn_news": items}
    except Exception as e:
        print(f"[hn_node] error: {e}")
        return {"hn_news": []}
