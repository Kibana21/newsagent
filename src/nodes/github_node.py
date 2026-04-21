from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Any
import requests
from src.state import AgentState, NewsItem


def _search_repos(query: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": "2"}
    r = requests.get(
        "https://api.github.com/search/repositories",
        params=params,  # type: ignore[arg-type]
        headers=headers,
        timeout=15,
    )
    r.raise_for_status()
    return list(r.json().get("items", []))[:2]


def github_node(state: AgentState) -> dict[str, Any]:
    days = state.get("days", 2)
    pushed_after = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        print("[github] searching repos...")
        # Two separate queries — GitHub rejects topic:x OR topic:y with date qualifiers
        repos = (
            _search_repos(f"topic:llm pushed:>{pushed_after}", headers)
            + _search_repos(f"topic:generative-ai pushed:>{pushed_after}", headers)
        )
        seen: set[str] = set()
        items: list[NewsItem] = []
        for repo in repos:
            if repo["html_url"] in seen:
                continue
            seen.add(repo["html_url"])
            items.append({
                "title": f"{repo['full_name']} ({repo['stargazers_count']} stars)",
                "url": repo["html_url"],
                "summary": (repo.get("description") or "")[:300],
                "source": "github",
                "published_at": repo.get("pushed_at", ""),
            })
            if len(items) >= 3:
                break
        print(f"[github] got {len(items)} repos")
        return {"github_news": items}
    except Exception as e:
        print(f"[github_node] error: {e}")
        return {"github_news": []}
