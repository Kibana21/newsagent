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
        queries = [
            # General AI
            f"{query} (published in the last {days} days)",
            f"generative AI enterprise news breakthroughs {year}",
            # Singapore financial sector AI
            f"DBS OCBC UOB Singapore bank AI artificial intelligence {year}",
            f"Prudential Great Eastern Singapore insurance AI digital transformation {year}",
            f"Singapore MAS IMDA AI regulation fintech insurtech {year}",
            # APAC competitive landscape
            f"APAC financial services AI deployment case study {year}",
        ]
        items: list[NewsItem] = []
        for q in queries:
            items.extend(_search(tool, q, max_results=4))
        print(f"[tavily] got {len(items)} items")
        return {"tavily_news": items}
    except Exception as e:
        print(f"[tavily_node] error: {e}")
        return {"tavily_news": []}
