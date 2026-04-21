from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import requests
import xml.etree.ElementTree as ET
from src.state import AgentState, NewsItem

ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def arxiv_node(state: AgentState) -> dict[str, Any]:
    days = state.get("days", 2)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days + 2)  # lag buffer
    try:
        print("[arxiv] fetching papers...")
        url = (
            "http://export.arxiv.org/api/query"
            "?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG"
            "&sortBy=submittedDate&sortOrder=descending&max_results=20"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        items: list[NewsItem] = []
        for entry in root.findall("a:entry", ATOM_NS):
            pub_el = entry.find("a:published", ATOM_NS)
            title_el = entry.find("a:title", ATOM_NS)
            id_el = entry.find("a:id", ATOM_NS)
            summary_el = entry.find("a:summary", ATOM_NS)
            if pub_el is None or title_el is None or id_el is None:
                continue
            dt = datetime.fromisoformat((pub_el.text or "").replace("Z", "+00:00"))
            if dt < cutoff:
                continue
            items.append({
                "title": (title_el.text or "").strip(),
                "url": (id_el.text or "").strip(),
                "summary": (summary_el.text or "").strip()[:200] if summary_el is not None else "",
                "source": "arxiv",
                "published_at": dt.isoformat(),
            })
            if len(items) >= 5:
                break
        print(f"[arxiv] got {len(items)} papers")
        return {"arxiv_news": items}
    except Exception as e:
        print(f"[arxiv_node] error: {e}")
        return {"arxiv_news": []}
