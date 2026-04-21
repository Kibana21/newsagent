# Phase 0 — Scaffold

## Goal

Project imports cleanly. `mypy` passes. No runtime behavior yet. This phase creates the skeleton that Phase 1 populates with logic.

## User Stories Covered

- **US-001** — Set up project scaffold and dependencies
- **US-002** — Define shared AgentState schema

## Files Created

| Path | Purpose |
|---|---|
| `requirements.txt` | Pinned dependencies |
| `pyproject.toml` | pytest, mypy, coverage config |
| `.env.example` | Required env vars with descriptions |
| `README.md` | 10-step local setup (overwrites the stub) |
| `src/__init__.py` | Package marker (empty) |
| `src/nodes/__init__.py` | Package marker (empty) |
| `src/utils/__init__.py` | Package marker (empty) |
| `src/state.py` | `AgentState`, `NewsItem`, `CategorizedNews`, `EmailLog` TypedDicts |
| `src/config.py` | Module-level constants (feeds, keywords, competitor insurers) |

`reports/` and `state/` directories are **not** created now — they're created at runtime by `main.py` to avoid polluting a clean checkout.

## Design Decisions

1. **`TypedDict(total=False)` everywhere** — LangGraph merges partial dicts; requiring all fields would force every node to return the full state. Optional fields let nodes return only what they contribute.
2. **Separate `NewsItem` TypedDict** — every source node produces items with the same shape. Encodes the contract once.
3. **`insurance_score`, `competitor`, `regulatory` included in `NewsItem` from Phase 0** — avoids a schema migration in Phase 3. Set to defaults (`1`, `False`, `False`) until Phase 3 populates them.
4. **Constants live in `src/config.py`, not scattered** — a single place to edit RSS feeds, YouTube channels, insurance keywords, competitor names. Matches the PRD's explicit requirement.
5. **No `pyproject.toml` build metadata** — not building a wheel, just configuring tools. Keeps the file minimal.

## Implementation Steps

1. Write `requirements.txt` with pinned versions (see master plan).
2. Write `pyproject.toml` with `[tool.pytest.ini_options]`, `[tool.mypy]`, `[tool.coverage.*]` sections.
3. Write `.env.example` with all required env vars + inline comments.
4. Rewrite `README.md` to a 10-step local setup.
5. Create `src/`, `src/nodes/`, `src/utils/` with empty `__init__.py` files.
6. Write `src/state.py` with the four TypedDicts.
7. Write `src/config.py` with all module-level constants.
8. `pip install -r requirements.txt` inside `.venv`.
9. Verify with the commands in [Verification](#verification).

## Code Sketches

### `src/state.py`

```python
from __future__ import annotations
from typing import Dict, List, TypedDict


class NewsItem(TypedDict, total=False):
    title: str
    url: str
    summary: str
    source: str            # "tavily" | "rss" | "arxiv" | "github" | "huggingface" | "hackernews" | "reddit" | "youtube"
    published_at: str      # ISO 8601
    insurance_score: int   # 1 (low) | 2 (medium) | 3 (high); default 1 until Phase 3
    competitor: bool       # default False until Phase 3
    regulatory: bool       # default False until Phase 3
    buzz_score: int        # count of sources the item appeared in; default 1 until Phase 3


class CategorizedNews(TypedDict, total=False):
    business: List[NewsItem]
    technical: List[NewsItem]
    research: List[NewsItem]
    insurtech: List[NewsItem]


class EmailLog(TypedDict, total=False):
    status: str            # "success" | "failed"
    subscribers_found: int
    emails_sent: int
    errors: List[str]


class AgentState(TypedDict, total=False):
    search_query: str
    days: int

    tavily_news: List[NewsItem]
    rss_news: List[NewsItem]
    arxiv_news: List[NewsItem]
    github_news: List[NewsItem]
    hf_news: List[NewsItem]
    hn_news: List[NewsItem]
    reddit_news: List[NewsItem]
    youtube_news: List[NewsItem]

    raw_news: List[NewsItem]
    buzz_scores: Dict[str, int]
    curated_news: List[NewsItem]
    categorized_news: CategorizedNews

    final_report: str
    email_log: EmailLog
    mode: str              # "daily" | "monthly"
```

### `src/config.py`

```python
# RSS feeds — expanded in Phase 2 to include MAS and IMDA newsrooms
RSS_FEEDS = [
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("MAS Newsroom", "https://www.mas.gov.sg/news/rss"),
    ("IMDA Newsroom", "https://www.imda.gov.sg/news-and-events/rss"),
]

# YouTube channels — list of (name, channel_id)
YT_CHANNELS = [
    ("AI Explained", "UCNJ1Ymd5yFuUPqieoHgHS9Q"),
    ("Yannic Kilcher", "UCZHmQk67mSJgfCCTn7xBfew"),
]

# HackerNews keyword filter
HN_KEYWORDS = [
    "ai", "llm", "gpt", "gemini", "claude", "openai", "anthropic",
    "mistral", "langchain", "agent",
    "insurance", "fintech", "underwriting",
]

# Insurance keywords — used by the curation prompt and HN filter
INSURANCE_KEYWORDS = [
    "insurance", "underwriting", "claims", "actuarial", "reinsurance",
    "insurtech", "life insurance", "MAS", "IMDA", "finserv", "financial services",
]

# Competitor insurers — flagged with competitor=True in curation
COMPETITOR_INSURERS = [
    "Prudential", "Great Eastern", "Manulife", "FWD",
    "Allianz", "AXA", "Sun Life", "Zurich",
]

# Regulators — flagged with regulatory=True in curation
REGULATORS = ["MAS", "HKIA", "OJK", "IMDA"]

# Vertex AI config
VERTEX_LOCATION = "us-central1"
VERTEX_MODEL = "gemini-2.5-flash"

# Gmail SMTP
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
```

### `requirements.txt`

See master plan § Dependency Pinning.

### `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v"

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
check_untyped_defs = true
ignore_missing_imports = true
files = ["src"]

[tool.coverage.run]
source = ["src"]
omit = ["src/__init__.py", "src/**/__init__.py"]

[tool.coverage.report]
show_missing = true
skip_covered = false
```

### `.env.example`

```
# Vertex AI (Gemini) — path to GCP service account JSON
GOOGLE_APPLICATION_CREDENTIALS=./video-key.json

# Tavily web search
TAVILY_API_KEY=

# Gmail SMTP — use a Google App Password (not account password)
# Create one at https://myaccount.google.com/apppasswords
GMAIL_USER=
GMAIL_APP_PASSWORD=

# Optional
GOOGLE_SHEET_URL=
GITHUB_TOKEN=
```

### `README.md`

```markdown
# Gen AI News Agent — AIA Singapore Edition

Automated daily GenAI intelligence digest. See `tasks/prd-gen-ai-news-agent.md` for the full PRD.

## Setup

1. Clone the repo and `cd` into it.
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Place GCP service account JSON at `./video-key.json`.
5. `cp .env.example .env` and fill in `TAVILY_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`.
6. Create `subscribers.json`: `[{"email": "you@example.com", "name": "You", "persona": "all"}]`
7. Manual test: `python -m src.main --days 2`
8. Check inbox + `reports/YYYY-MM-DD_report.md`.
9. Start the scheduler: `python scheduler.py` (daily 08:00 Asia/Singapore).
10. Run tests: `pytest`.
```

## Verification

```bash
# Installation succeeds
pip install -r requirements.txt

# Imports work
python -c "from src.state import AgentState, NewsItem, CategorizedNews, EmailLog; print('OK')"
python -c "from src.config import RSS_FEEDS, INSURANCE_KEYWORDS, COMPETITOR_INSURERS; print('OK')"

# mypy passes
mypy src/
```

Expected: all three commands exit 0. `mypy` reports 0 errors.

## Risks / Open Items

- **Dependency resolution conflicts**: LangChain's rapid release cadence occasionally breaks `pydantic` compat. If `pip install` reports conflicts on the pinned versions, relax `~=` to `>=X.Y,<X.(Y+1)` on whichever package the resolver flags; do not unpin `pydantic`.
- **`.venv` interpreter is 3.12**: mypy's `python_version = "3.12"` must match, otherwise it'll complain about PEP 604 `X | Y` union syntax.

## Next Phase

Phase 1 depends on `src/state.py` and `src/config.py`. See [plan-phase-1-walking-skeleton.md](./plan-phase-1-walking-skeleton.md).
