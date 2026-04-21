# Phase 2 — Full Ingestion Sources

## Goal

All 8 source nodes fully operational. Every typical weekday run produces non-empty results from at least 6 of 8 sources. RSS feed list expands to include MAS and IMDA (regulators). Tavily runs two searches (general + insurance-specific).

**Design invariant**: every source node returns `[]` on failure — no exception propagates. One source outage does not abort the pipeline.

## User Stories Covered

- **US-004** — Full RSS (5 feeds including MAS/IMDA)
- **US-005** — arXiv (cs.AI, cs.CL, cs.LG)
- **US-006** — GitHub trending repos
- **US-007** — HuggingFace trending models
- **US-008** — HackerNews top AI stories
- **US-009** — Reddit r/LocalLLaMA + r/MachineLearning
- **US-010** — YouTube transcripts from AI channels
- **US-003** (upgrade) — Tavily second search for insurance context

## Files Modified

| Path | Change |
|---|---|
| `src/nodes/tavily_node.py` | Add second insurance-specific search; merge results |
| `src/nodes/rss_node.py` | Expand to full `RSS_FEEDS` constant (5 feeds) |
| `src/nodes/arxiv_node.py` | Real implementation (was stub) |
| `src/nodes/github_node.py` | Real implementation (was stub) |
| `src/nodes/hf_node.py` | Real implementation (was stub) |
| `src/nodes/hn_node.py` | Real implementation (was stub) |
| `src/nodes/reddit_node.py` | Real implementation (was stub) |
| `src/nodes/youtube_node.py` | Real implementation (was stub) |

## Design Decisions

1. **Per-source item caps** prevent any single source from flooding the curator. Caps: Tavily 8, RSS 8, arXiv 5, GitHub 3, HF 3, HN 5, Reddit 10 (5 per subreddit), YouTube 2.
2. **All network I/O wrapped in `try / except Exception`** returning `[]`. The pipeline must not abort on one flaky source.
3. **Reddit uses public JSON endpoints with a user-agent header**, not PRAW. Avoids OAuth setup for a read-only use case.
4. **YouTube scraping isolated in `src/utils/youtube.py`** (new file). Two functions: `fetch_recent_video_ids(channel_id, limit)` and `fetch_transcript(video_id)`. Scraping logic is fragile; isolating it makes it replaceable when it breaks.
5. **arXiv uses a 2-day lookback buffer** beyond `state["days"]` because arXiv indexes papers with a delay. If `days=2`, query 4 days back, then filter results by timestamp.
6. **GitHub Search API with `sort=stars`** to prioritize repos that are actually getting traction. Unauthenticated rate limit is 10/min — plenty for 1 call/day.
7. **Tavily second search uses a stable template**: `f"AI insurance underwriting claims Singapore {current_year}"`. Not templated on user input.

## Implementation Steps

### 1. `src/nodes/tavily_node.py` — second search

```python
# Pseudocode
def tavily_node(state):
    q1 = f"{state['search_query']} (published in last {state['days']} days)"
    q2 = f"AI insurance underwriting claims Singapore APAC {current_year}"
    items = _search(q1, max=5) + _search(q2, max=3)
    return {"tavily_news": items}
```

### 2. `src/nodes/rss_node.py` — full feed list

Swap local `PHASE1_FEEDS` for `RSS_FEEDS` from `src/config.py`. Already includes OpenAI, TechCrunch, VentureBeat, MAS, IMDA.

### 3. `src/nodes/arxiv_node.py`

API: `http://export.arxiv.org/api/query`

```python
from datetime import datetime, timedelta, timezone
import requests
import xml.etree.ElementTree as ET

ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}

def arxiv_node(state):
    days = state.get("days", 2)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days + 2)  # lag buffer
    try:
        url = (
            "http://export.arxiv.org/api/query"
            "?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG"
            "&sortBy=submittedDate&sortOrder=descending&max_results=20"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        items = []
        for entry in root.findall("a:entry", ATOM_NS):
            published = entry.find("a:published", ATOM_NS).text
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if dt < cutoff:
                continue
            items.append({
                "title": entry.find("a:title", ATOM_NS).text.strip(),
                "url": entry.find("a:id", ATOM_NS).text.strip(),
                "summary": entry.find("a:summary", ATOM_NS).text.strip()[:200],
                "source": "arxiv",
                "published_at": dt.isoformat(),
            })
            if len(items) >= 5:
                break
        return {"arxiv_news": items}
    except Exception as e:
        print(f"[arxiv_node] error: {e}")
        return {"arxiv_news": []}
```

### 4. `src/nodes/github_node.py`

API: `https://api.github.com/search/repositories`

```python
from datetime import datetime, timedelta, timezone
import os
import requests

def github_node(state):
    days = state.get("days", 2)
    created_after = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        url = (
            "https://api.github.com/search/repositories"
            f"?q=topic:llm+OR+topic:generative-ai+created:>{created_after}"
            "&sort=stars&order=desc&per_page=3"
        )
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = []
        for repo in data.get("items", [])[:3]:
            items.append({
                "title": f"{repo['full_name']} ({repo['stargazers_count']} ⭐)",
                "url": repo["html_url"],
                "summary": (repo.get("description") or "")[:300],
                "source": "github",
                "published_at": repo.get("created_at", ""),
            })
        return {"github_news": items}
    except Exception as e:
        print(f"[github_node] error: {e}")
        return {"github_news": []}
```

### 5. `src/nodes/hf_node.py`

API: `https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=3`

```python
import requests

def hf_node(state):
    try:
        r = requests.get(
            "https://huggingface.co/api/models",
            params={"sort": "trendingScore", "direction": -1, "limit": 3},
            timeout=15,
        )
        r.raise_for_status()
        items = []
        for m in r.json():
            tags = ", ".join(m.get("tags", [])[:6])
            items.append({
                "title": m["modelId"],
                "url": f"https://huggingface.co/{m['modelId']}",
                "summary": f"Tags: {tags}. Downloads: {m.get('downloads', 0)}",
                "source": "huggingface",
                "published_at": m.get("lastModified", ""),
            })
        return {"hf_news": items}
    except Exception as e:
        print(f"[hf_node] error: {e}")
        return {"hf_news": []}
```

### 6. `src/nodes/hn_node.py`

API: Firebase — `https://hacker-news.firebaseio.com/v0/`

```python
import requests
from src.config import HN_KEYWORDS

def hn_node(state):
    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        ids = r.json()[:30]
        items = []
        for sid in ids:
            s = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5).json()
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
        return {"hn_news": items}
    except Exception as e:
        print(f"[hn_node] error: {e}")
        return {"hn_news": []}
```

### 7. `src/nodes/reddit_node.py`

API: `https://www.reddit.com/r/<sub>/top.json?t=day` with user agent.

```python
import requests

SUBS = ["LocalLLaMA", "MachineLearning"]

def reddit_node(state):
    headers = {"User-Agent": "newsagent/0.1 (by /u/aia-newsagent)"}
    items = []
    for sub in SUBS:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/top.json",
                params={"t": "day", "limit": 5},
                headers=headers, timeout=10,
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
    return {"reddit_news": items}
```

### 8. `src/nodes/youtube_node.py`

Two-step scrape:
1. Fetch channel page HTML, regex-extract `"videoId":"..."` from embedded JSON, take first N.
2. For each video ID, call `YouTubeTranscriptApi.get_transcript(video_id)` and concatenate.

```python
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from src.config import YT_CHANNELS

VIDEO_ID_RE = re.compile(r'"videoId":"([a-zA-Z0-9_-]{11})"')

def fetch_recent_video_ids(channel_id: str, limit: int = 1) -> list[str]:
    try:
        r = requests.get(f"https://www.youtube.com/channel/{channel_id}/videos", timeout=15)
        ids = []
        for m in VIDEO_ID_RE.finditer(r.text):
            vid = m.group(1)
            if vid not in ids:
                ids.append(vid)
            if len(ids) >= limit:
                break
        return ids
    except Exception:
        return []

def fetch_transcript(video_id: str) -> str:
    try:
        entries = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return " ".join(e["text"] for e in entries)
    except Exception:
        return ""

def youtube_node(state):
    items = []
    for name, channel_id in YT_CHANNELS:
        for vid in fetch_recent_video_ids(channel_id, limit=1):
            transcript = fetch_transcript(vid)
            if not transcript:
                continue
            items.append({
                "title": f"{name}: latest video",
                "url": f"https://www.youtube.com/watch?v={vid}",
                "summary": transcript[:1000],
                "source": "youtube",
                "published_at": "",
            })
    return {"youtube_news": items}
```

## Verification

```bash
# End-to-end
python -m src.main --days 2

# Inspect the state dump
cat state/$(date -I)_state.json | python -c "
import json, sys
s = json.load(sys.stdin)
for k in ['tavily_news','rss_news','arxiv_news','github_news','hf_news','hn_news','reddit_news','youtube_news']:
    print(f'{k}: {len(s.get(k, []))}')"

# Expected: at least 6 of 8 show non-zero counts on a typical weekday
# Expected: no uncaught exceptions; all failures logged as "[<node>] error: ..." lines
```

## Risks / Open Items

- **arXiv Atom namespace handling**: if the feed changes namespaces, parsing breaks silently (returns `[]`). Log the exception, don't swallow it.
- **YouTube HTML scraping is fragile**: the embedded JSON schema changes 1–2x a year. When it breaks, either fix the regex or switch to the YouTube Data API v3 (PRD Open Question #4).
- **Reddit JSON endpoint may 429 without a UA header**: always send `User-Agent`.
- **GitHub rate limit**: unauthenticated = 10/min. With `GITHUB_TOKEN`, 30/min. One call/day is fine either way.
- **HuggingFace `trendingScore` field**: not officially documented; may change. If it disappears, fall back to `downloads` sort.

## Next Phase

Phase 3 enriches the curate and summarize nodes with the insurance intelligence layer. See [plan-phase-3-insurance-intelligence.md](./plan-phase-3-insurance-intelligence.md).
