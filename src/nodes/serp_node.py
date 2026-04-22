from __future__ import annotations
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from src.config import get_serp_query_packs
from src.state import AgentState, NewsItem


def _fetch_pack(pack_name: str, queries: list[str], key: str, days: int) -> list[NewsItem]:
    from serpapi import GoogleSearch  # type: ignore[import-untyped]

    items: list[NewsItem] = []
    tbs = f"qdr:d{days}"
    for q in queries:
        try:
            params: dict[str, str] = {
                "q": q, "tbm": "nws", "num": "8",
                "tbs": tbs, "api_key": key,
            }
            results: list[dict[str, Any]] = (
                GoogleSearch(params).get_dict().get("news_results") or []
            )
            if not results:
                # Fall back to web search if no news results
                params.pop("tbm")
                results = GoogleSearch(params).get_dict().get("organic_results") or []
            for r in results[:8]:
                title = str(r.get("title") or "").strip()
                url = str(r.get("link") or r.get("url") or "").strip()
                if not title or not url:
                    continue
                item: NewsItem = {
                    "title": title,
                    "url": url,
                    "summary": str(r.get("snippet") or r.get("description") or "")[:500],
                    "source": "serp",
                    "published_at": str(r.get("date") or ""),
                    "topic_pack": pack_name,
                }
                items.append(item)
        except Exception as e:
            print(f"[serp] pack={pack_name} query='{q}' failed: {e}")
    return items


def serp_node(state: AgentState) -> dict[str, Any]:
    key = os.environ.get("SERPAPI_KEY", "")
    if not key:
        print("[serp] SERPAPI_KEY not set — skipping")
        return {"serp_news": []}

    days = int(state.get("days") or 2)
    all_items: list[NewsItem] = []

    query_packs = get_serp_query_packs()
    print(f"[serp] fetching {len(query_packs)} query packs in parallel...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {
            ex.submit(_fetch_pack, name, queries, key, days): name
            for name, queries in query_packs.items()
        }
        for future in as_completed(futures):
            pack_name = futures[future]
            try:
                results = future.result()
                all_items.extend(results)
                print(f"[serp] pack={pack_name} → {len(results)} items")
            except Exception as e:
                print(f"[serp] pack={pack_name} error: {e}")

    print(f"[serp] total raw items: {len(all_items)}")
    return {"serp_news": all_items}
