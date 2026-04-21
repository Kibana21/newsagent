from __future__ import annotations
from typing import Any
import requests
from src.state import AgentState, NewsItem

SUBS = ["LocalLLaMA", "MachineLearning"]


def reddit_node(state: AgentState) -> dict[str, Any]:
    headers = {"User-Agent": "newsagent/0.1 (by /u/aia-newsagent)"}
    items: list[NewsItem] = []
    print(f"[reddit] fetching r/{' + r/'.join(SUBS)}...")
    for sub in SUBS:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/top.json",
                params={"t": "day", "limit": "5"},
                headers=headers,
                timeout=10,
            )
            r.raise_for_status()
            for post in r.json()["data"]["children"]:
                d = post["data"]
                items.append({
                    "title": d.get("title", ""),
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                    "summary": (d.get("selftext") or "")[:400] + f"  · score {d.get('score', 0)}",
                    "source": "reddit",
                    "published_at": "",
                })
        except Exception as e:
            print(f"[reddit_node] error on r/{sub}: {e}")
    print(f"[reddit] got {len(items)} posts")
    return {"reddit_news": items}
