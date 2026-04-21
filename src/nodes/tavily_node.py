from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Any
from langchain_tavily import TavilySearch
from src.state import AgentState, NewsItem


def _search(tool: TavilySearch, query: str, max_results: int) -> list[NewsItem]:
    results = tool.invoke({"query": query})
    if isinstance(results, list):
        raw = results
    else:
        raw = results.get("results", [])
    items: list[NewsItem] = []
    for r in raw[:max_results]:
        items.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "summary": r.get("content", "")[:500],
            "source": "tavily",
            "published_at": r.get("published_date", ""),
        })
    return items


def tavily_node(state: AgentState) -> dict[str, Any]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY must be set")
    query = state.get("search_query", "")
    days = state.get("days", 2)
    year = datetime.now(timezone.utc).year
    try:
        print("[tavily] searching...")
        tool = TavilySearch(api_key=api_key, max_results=8)
        q1 = f"{query} (published in the last {days} days)"
        q2 = f"AI insurance underwriting claims Singapore APAC {year}"
        items = _search(tool, q1, max_results=5) + _search(tool, q2, max_results=3)
        print(f"[tavily] got {len(items)} items")
        return {"tavily_news": items}
    except Exception as e:
        print(f"[tavily_node] error: {e}")
        return {"tavily_news": []}
