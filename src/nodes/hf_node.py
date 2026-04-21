from __future__ import annotations
from typing import Any
import requests
from src.state import AgentState, NewsItem


def hf_node(state: AgentState) -> dict[str, Any]:
    try:
        print("[huggingface] fetching trending models...")
        r = requests.get(
            "https://huggingface.co/api/models",
            params={"sort": "trendingScore", "direction": "-1", "limit": "3"},
            timeout=15,
        )
        r.raise_for_status()
        items: list[NewsItem] = []
        for m in r.json():
            tags = ", ".join(m.get("tags", [])[:6])
            items.append({
                "title": m["modelId"],
                "url": f"https://huggingface.co/{m['modelId']}",
                "summary": f"Tags: {tags}. Downloads: {m.get('downloads', 0)}",
                "source": "huggingface",
                "published_at": m.get("lastModified", ""),
            })
        print(f"[huggingface] got {len(items)} models")
        return {"hf_news": items}
    except Exception as e:
        print(f"[hf_node] error: {e}")
        return {"hf_news": []}
