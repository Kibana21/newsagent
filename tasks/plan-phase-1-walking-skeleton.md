# Phase 1 — Walking Skeleton

## Goal

**One real email lands in a single recipient's inbox from a single end-to-end run.** Validates four things at once:
1. Vertex AI auth via `video-key.json` works
2. LangGraph's parallel fan-out → sequential tail compiles and executes
3. Gmail SMTP delivers HTML
4. The state contract in `src/state.py` survives a real pipeline run

Insurance intelligence is **deferred** to Phase 3. The skeleton uses minimal prompts so that Phase 3 can be a pure prompt + layout upgrade without touching infrastructure.

## User Stories Covered (Minimal)

- **US-003** (partial) — Tavily node, single search
- **US-011** (minimal) — aggregate with URL dedup only
- **US-012** (minimal) — LLM curation into 2 categories
- **US-013** (minimal) — plain Markdown report
- **US-014** (partial) — single hardcoded recipient
- **US-015** — LangGraph wiring (full)
- **US-016** — CLI entrypoint (full)

## Files Created

| Path | Purpose |
|---|---|
| `src/llm.py` | Vertex AI client factory (reads `video-key.json`, returns `ChatVertexAI`) |
| `src/prompts.py` | Minimal curation + summarization prompts (upgraded in Phase 3) |
| `src/nodes/tavily_node.py` | Tavily search (single query for now) |
| `src/nodes/rss_node.py` | Minimal RSS (OpenAI blog + TechCrunch AI only) |
| `src/nodes/arxiv_node.py` | Stub — returns `[]` |
| `src/nodes/github_node.py` | Stub — returns `[]` |
| `src/nodes/hf_node.py` | Stub — returns `[]` |
| `src/nodes/hn_node.py` | Stub — returns `[]` |
| `src/nodes/reddit_node.py` | Stub — returns `[]` |
| `src/nodes/youtube_node.py` | Stub — returns `[]` |
| `src/nodes/aggregate_node.py` | Dedup by URL only (no buzz, no sent-URL filter) |
| `src/nodes/curate_node.py` | LLM call → `{business: [...], technical: [...]}` |
| `src/nodes/summarize_node.py` | Plain Markdown: `## Business` / `## Technical` |
| `src/nodes/email_node.py` | SMTP-SSL to a single hardcoded recipient |
| `src/graph.py` | `build_graph()` returns compiled `StateGraph` |
| `src/main.py` | CLI: `--query`, `--days`, `--output`; saves MD + JSON |
| `subscribers.json` | `[{"email": "kartik.nus@gmail.com", "name": "Kartik", "persona": "all"}]` |

## Design Decisions

1. **All 8 source nodes exist as files from Phase 1**, even stubs. Graph wiring stays identical from Phase 1 through Phase 5; only node bodies change. Avoids refactoring `graph.py` in every phase.
2. **Vertex AI `project_id` read from `video-key.json`**, not hardcoded. The service account JSON contains it; extracting it avoids a separate env var.
3. **Curate prompt asks for JSON with just 2 keys** (`business`, `technical`). Phase 3 upgrades to 4 keys + scoring. Kept minimal to prove the LLM round-trip works.
4. **Summarize is pure Python, no LLM call**, for now. Phase 3 introduces a second LLM call for the TL;DR and persona-specific sentences. Phase 1 just formats the curated data. This keeps the skeleton fast and cheap.
5. **Email recipient is hardcoded**, not loaded from `subscribers.json` yet. Makes debugging obvious — if the email arrives, auth + SMTP work. Phase 3 switches to `src/utils/subscribers.py`.
6. **No `state/sent_urls.json` write** in Phase 1. Avoids state contamination while iterating on the pipeline.
7. **Graph fan-out from START to 8 nodes** is already the final shape. Stubs return `[]` but they still run.

## Implementation Steps

1. Write `src/llm.py` — Vertex AI factory.
2. Write `src/prompts.py` — minimal curate prompt template.
3. Write each of the 8 source node files (Tavily + minimal RSS + 6 stubs).
4. Write `src/nodes/aggregate_node.py` with URL-based dedup.
5. Write `src/nodes/curate_node.py` — LLM call, JSON parse, 2-key output.
6. Write `src/nodes/summarize_node.py` — pure Python Markdown formatter.
7. Write `src/nodes/email_node.py` — SMTP-SSL single recipient.
8. Write `src/graph.py` — wire the 12-node graph.
9. Write `src/main.py` — CLI + env validation + write `reports/` and `state/` dumps.
10. Create `subscribers.json` at project root with your email.
11. Run and verify (see [Verification](#verification)).

## Code Sketches

### `src/llm.py`

```python
from __future__ import annotations
import json
import os
from functools import lru_cache
from google.oauth2 import service_account
from langchain_google_vertexai import ChatVertexAI
from src.config import VERTEX_LOCATION, VERTEX_MODEL

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


@lru_cache(maxsize=1)
def _credentials_and_project() -> tuple:
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.isfile(creds_path):
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS must point to the service account JSON "
            f"(got: {creds_path!r})"
        )
    with open(creds_path) as f:
        project_id = json.load(f)["project_id"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return creds, project_id


def get_llm(temperature: float = 0.2) -> ChatVertexAI:
    creds, project_id = _credentials_and_project()
    return ChatVertexAI(
        model=VERTEX_MODEL,
        credentials=creds,
        project=project_id,
        location=VERTEX_LOCATION,
        temperature=temperature,
    )
```

### `src/nodes/tavily_node.py`

```python
from __future__ import annotations
import os
from typing import Any
from langchain_tavily import TavilySearch
from src.state import AgentState, NewsItem


def tavily_node(state: AgentState) -> dict[str, Any]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY must be set")
    query = state.get("search_query", "")
    days = state.get("days", 2)
    try:
        tool = TavilySearch(api_key=api_key, max_results=5)
        q = f"{query} (published in the last {days} days)"
        results = tool.invoke({"query": q})
        items: list[NewsItem] = []
        for r in results.get("results", []):
            items.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "summary": r.get("content", "")[:500],
                "source": "tavily",
                "published_at": r.get("published_date", ""),
            })
        return {"tavily_news": items}
    except Exception as e:
        print(f"[tavily_node] error: {e}")
        return {"tavily_news": []}
```

### `src/nodes/rss_node.py` (minimal Phase 1 version)

```python
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import feedparser
from src.state import AgentState, NewsItem

# Phase 1: only OpenAI blog + TechCrunch AI. Phase 2 expands to MAS/IMDA/VentureBeat.
PHASE1_FEEDS = [
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
]


def rss_node(state: AgentState) -> dict[str, Any]:
    days = state.get("days", 2)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items: list[NewsItem] = []
    for name, url in PHASE1_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    dt = datetime(*pub[:6], tzinfo=timezone.utc)
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
    return {"rss_news": items[:8]}
```

### Stub source node (same shape for `arxiv`, `github`, `hf`, `hn`, `reddit`, `youtube`)

```python
# src/nodes/arxiv_node.py
from src.state import AgentState
def arxiv_node(state: AgentState) -> dict:
    return {"arxiv_news": []}
```

### `src/nodes/aggregate_node.py` (minimal Phase 1 version)

```python
from __future__ import annotations
from typing import Any
from src.state import AgentState


def aggregate_node(state: AgentState) -> dict[str, Any]:
    raw: list[dict] = []
    for field in ("tavily_news", "rss_news", "arxiv_news", "github_news",
                  "hf_news", "hn_news", "reddit_news", "youtube_news"):
        raw.extend(state.get(field, []))

    # URL dedup, case-insensitive, strip trailing slash
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in raw:
        url = item.get("url", "").strip().rstrip("/").lower()
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(item)

    print(f"[aggregate] raw={len(raw)} deduped={len(deduped)}")
    return {"raw_news": deduped, "buzz_scores": {}}
```

### `src/prompts.py` (Phase 1 minimal)

```python
CURATE_PROMPT_MINIMAL = """You are filtering GenAI news for a professional newsletter.

Given the JSON list below, return ONLY a JSON object with two keys:
- "business": items about corporate news, funding, product launches
- "technical": items about models, tools, open-source releases

Drop items that are off-topic or older than a week.

Input items:
{items_json}

Return JSON only, no prose.
"""
```

### `src/nodes/curate_node.py` (minimal)

```python
from __future__ import annotations
import json
from typing import Any
from src.llm import get_llm
from src.prompts import CURATE_PROMPT_MINIMAL
from src.state import AgentState


def curate_node(state: AgentState) -> dict[str, Any]:
    raw = state.get("raw_news", [])
    if not raw:
        return {"curated_news": [], "categorized_news": {"business": [], "technical": []}}
    llm = get_llm(temperature=0.1)
    prompt = CURATE_PROMPT_MINIMAL.format(items_json=json.dumps(raw)[:12000])
    resp = llm.invoke(prompt)
    text = resp.content if hasattr(resp, "content") else str(resp)
    # Strip ```json fences if present
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(text)
    categorized = {
        "business": data.get("business", []),
        "technical": data.get("technical", []),
    }
    flat = categorized["business"] + categorized["technical"]
    return {"curated_news": flat, "categorized_news": categorized}
```

### `src/nodes/summarize_node.py` (plain Markdown, no LLM)

```python
from __future__ import annotations
from typing import Any
from src.state import AgentState


def summarize_node(state: AgentState) -> dict[str, Any]:
    cat = state.get("categorized_news", {})
    lines = ["# GenAI News Daily Digest", ""]
    for label, key in [("Business", "business"), ("Technical", "technical")]:
        items = cat.get(key, [])
        if not items:
            continue
        lines.append(f"## {label}")
        lines.append("")
        for item in items:
            title = item.get("title", "(no title)")
            url = item.get("url", "#")
            summary = item.get("summary", "")[:300]
            lines.append(f"- **[{title}]({url})** — {summary}")
        lines.append("")
    return {"final_report": "\n".join(lines)}
```

### `src/nodes/email_node.py` (Phase 1 single recipient)

```python
from __future__ import annotations
import os
import smtplib
from email.message import EmailMessage
from typing import Any
import markdown as md
from src.config import SMTP_HOST, SMTP_PORT
from src.state import AgentState

PHASE1_RECIPIENT = "kartik.nus@gmail.com"


def email_node(state: AgentState) -> dict[str, Any]:
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not password:
        return {"email_log": {"status": "failed", "errors": ["Missing GMAIL_USER / GMAIL_APP_PASSWORD"]}}
    body_md = state.get("final_report", "")
    body_html = md.markdown(body_md)

    msg = EmailMessage()
    msg["Subject"] = "GenAI Daily Digest — Phase 1 Skeleton"
    msg["From"] = user
    msg["To"] = PHASE1_RECIPIENT
    msg.set_content(body_md)
    msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
            s.login(user, password)
            s.send_message(msg)
        return {"email_log": {"status": "success", "subscribers_found": 1, "emails_sent": 1, "errors": []}}
    except Exception as e:
        return {"email_log": {"status": "failed", "errors": [str(e)], "subscribers_found": 1, "emails_sent": 0}}
```

### `src/graph.py`

```python
from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.tavily_node import tavily_node
from src.nodes.rss_node import rss_node
from src.nodes.arxiv_node import arxiv_node
from src.nodes.github_node import github_node
from src.nodes.hf_node import hf_node
from src.nodes.hn_node import hn_node
from src.nodes.reddit_node import reddit_node
from src.nodes.youtube_node import youtube_node
from src.nodes.aggregate_node import aggregate_node
from src.nodes.curate_node import curate_node
from src.nodes.summarize_node import summarize_node
from src.nodes.email_node import email_node


def build_graph():
    g = StateGraph(AgentState)

    fetchers = [
        ("tavily", tavily_node),
        ("rss", rss_node),
        ("arxiv", arxiv_node),
        ("github", github_node),
        ("hf", hf_node),
        ("hn", hn_node),
        ("reddit", reddit_node),
        ("youtube", youtube_node),
    ]
    for name, fn in fetchers:
        g.add_node(name, fn)

    g.add_node("aggregate", aggregate_node)
    g.add_node("curate", curate_node)
    g.add_node("summarize", summarize_node)
    g.add_node("email", email_node)

    for name, _ in fetchers:
        g.add_edge(START, name)
        g.add_edge(name, "aggregate")

    g.add_edge("aggregate", "curate")
    g.add_edge("curate", "summarize")
    g.add_edge("summarize", "email")
    g.add_edge("email", END)

    return g.compile()
```

### `src/main.py`

```python
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from src.graph import build_graph


def validate_env() -> None:
    required = ["GOOGLE_APPLICATION_CREDENTIALS", "TAVILY_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    creds = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    if not Path(creds).is_file():
        print(f"ERROR: GOOGLE_APPLICATION_CREDENTIALS points to {creds} but file does not exist", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--query", default="latest breakthroughs, releases, and news in Generative AI")
    p.add_argument("--days", type=int, default=2)
    p.add_argument("--output", default="reports")
    p.add_argument("--mode", default="daily", choices=["daily", "monthly"])
    args = p.parse_args()

    validate_env()

    Path(args.output).mkdir(parents=True, exist_ok=True)
    Path("state").mkdir(parents=True, exist_ok=True)

    graph = build_graph()
    final_state = graph.invoke({
        "search_query": args.query,
        "days": args.days,
        "mode": args.mode,
    })

    today = date.today().isoformat()
    (Path(args.output) / f"{today}_report.md").write_text(final_state.get("final_report", ""))
    (Path("state") / f"{today}_state.json").write_text(json.dumps(final_state, indent=2, default=str))
    print(f"Done. Email log: {final_state.get('email_log')}")


if __name__ == "__main__":
    main()
```

## Verification

```bash
# Full end-to-end run
python -m src.main --days 2

# Expected stdout (example):
# [aggregate] raw=8 deduped=7
# Done. Email log: {'status': 'success', 'subscribers_found': 1, 'emails_sent': 1, 'errors': []}

# Email arrives in kartik.nus@gmail.com inbox
# Subject: "GenAI Daily Digest — Phase 1 Skeleton"
# Body contains "## Business" and "## Technical" sections

# Files produced
ls reports/   # → YYYY-MM-DD_report.md
ls state/     # → YYYY-MM-DD_state.json

cat state/$(date -I)_state.json | jq '.categorized_news | keys'
# → ["business", "technical"]
```

## Risks / Open Items

- **Vertex AI region**: `us-central1` is the default; if the GCP project doesn't have Gemini enabled in that region, the call will fail. Surface the actual error clearly in the LLM factory.
- **Tavily response shape**: `TavilySearch` sometimes returns a list directly instead of `{"results": [...]}`. Defensively handle both.
- **LLM JSON parsing**: the first-shot prompt may produce fenced code blocks or surrounding prose. Phase 1 uses a simple strip; Phase 3 introduces retry.
- **Gmail SMTP quota**: dev accounts occasionally trip rate limits. If 2–3 consecutive sends fail, the App Password may have been rotated or rate-limited.
- **No sent_urls filter**: Phase 1 runs can re-send the same stories. That's intentional while iterating.

## Next Phase

Phase 2 replaces each stub with a real source. See [plan-phase-2-ingestion-sources.md](./plan-phase-2-ingestion-sources.md).
