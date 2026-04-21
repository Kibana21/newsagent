# PRD: Gen AI News Agent

## Introduction

The Gen AI News Agent is an automated intelligence pipeline that ingests GenAI news daily from eight parallel sources (web search, RSS, arXiv, GitHub, HuggingFace, HackerNews, Reddit, YouTube), uses Gemini 2.5 Flash to curate and categorize content into three audience personas, generates persona-specific Markdown reports, and distributes them via email to subscribers. It runs on a daily GitHub Actions schedule and requires no manual intervention.

The reference implementation (by shubhamshardul-work) exists as a working prototype. This PRD defines requirements for building a clean, production-quality version in this repository — with better configurability, observability, testability, and maintainability.

---

## Goals

- Ingest GenAI news from 8 heterogeneous sources in parallel with a configurable lookback window
- Curate and deduplicate content using an LLM, removing off-topic or stale items
- Categorize curated news into three personas: Business, Technical, Research
- Generate rich, persona-specific Markdown reports with source attribution and a raw intelligence index
- Deliver reports via email (SMTP/Gmail) to a managed subscriber list
- Run fully automated on a daily cron schedule via GitHub Actions
- Expose a CLI for local/manual execution with configurable query, lookback days, and output path
- Be testable per-node in isolation without requiring live API credentials

---

## User Stories

### US-001: Set up project scaffold and dependencies
**Description:** As a developer, I need a clean project structure with dependency management so that the codebase is maintainable and reproducible.

**Acceptance Criteria:**
- [ ] `pyproject.toml` or `requirements.txt` with pinned versions for all dependencies
- [ ] `.env.example` listing all required environment variables with descriptions
- [ ] `src/` layout with `state.py`, `nodes.py`, `graph.py`, `main.py`
- [ ] `reports/` and `state/` directories created at runtime (not committed)
- [ ] `README.md` documents local setup in under 10 steps

---

### US-002: Define shared AgentState schema
**Description:** As a developer, I need a typed, well-documented state object so that all nodes share a consistent data contract.

**Acceptance Criteria:**
- [ ] `AgentState` defined as a `TypedDict` (total=False) in `src/state.py`
- [ ] Fields: `search_query` (str), `days` (int), `tavily_news`, `rss_news`, `arxiv_news`, `github_news`, `hf_news`, `hn_news`, `reddit_news`, `youtube_news` (all `List[dict]`), `raw_news` (List[dict]), `curated_news` (List[dict]), `categorized_news` (dict with keys `business`, `technical`, `research`), `final_report` (str), `email_log` (dict)
- [ ] Each news item dict has consistent keys: `title` (str), `url` (str), `summary` (str), `source` (str)
- [ ] Mypy or Pyright passes with no errors on `state.py`

---

### US-003: Implement Tavily web search node
**Description:** As a user, I want the agent to fetch real-time GenAI news from the web so that breaking news is always captured.

**Acceptance Criteria:**
- [ ] `tavily_node(state: AgentState) -> dict` in `src/nodes.py`
- [ ] Uses `TAVILY_API_KEY` from environment; raises `EnvironmentError` if missing
- [ ] Appends recency constraint to query (e.g., "published in last N days")
- [ ] Returns up to 5 results; each item has `title`, `url`, `summary`, `source="tavily"`
- [ ] Empty list returned (not exception) on API failure
- [ ] Unit-testable by mocking the Tavily client

---

### US-004: Implement RSS feed ingestion node
**Description:** As a user, I want the agent to pull from curated RSS feeds so that major publisher news (OpenAI, TechCrunch, VentureBeat) is included.

**Acceptance Criteria:**
- [ ] `rss_node(state: AgentState) -> dict` fetches from at minimum 3 hardcoded feeds
- [ ] Feed list is configurable via a constant (easy to add/remove feeds without logic changes)
- [ ] Filters articles older than `state["days"]` using publication date
- [ ] Strips HTML tags from descriptions
- [ ] Returns up to 5 most recent items across all feeds; `source="rss"`
- [ ] Returns empty list (not exception) if all feeds fail

---

### US-005: Implement arXiv research papers node
**Description:** As a researcher persona subscriber, I want recent AI research papers included so that academic breakthroughs are surfaced daily.

**Acceptance Criteria:**
- [ ] `arxiv_node(state: AgentState) -> dict` queries cs.AI, cs.CL, cs.LG categories
- [ ] Filters papers using ISO timestamp against `state["days"]` lookback
- [ ] Handles arXiv's typical 2-day publication lag (queries with extra buffer)
- [ ] Summary truncated to 200 characters; `source="arxiv"`
- [ ] Returns up to 5 results; empty list on failure

---

### US-006: Implement GitHub trending repositories node
**Description:** As a technical persona subscriber, I want trending AI repos included so that new open-source tools are surfaced.

**Acceptance Criteria:**
- [ ] `github_node(state: AgentState) -> dict` uses GitHub Search API (unauthenticated or with `GITHUB_TOKEN`)
- [ ] Searches repos with topics `llm` or `generative-ai` created in last N days, sorted by stars
- [ ] Returns up to 3 results; title includes star count; `source="github"`
- [ ] Returns empty list on API error or rate limit

---

### US-007: Implement HuggingFace trending models node
**Description:** As a technical persona subscriber, I want trending HuggingFace models included so that newly released models are highlighted.

**Acceptance Criteria:**
- [ ] `hf_node(state: AgentState) -> dict` calls HuggingFace Models API sorted by trending score
- [ ] Returns up to 3 models with tags (up to 6), download count, and model card URL
- [ ] `source="huggingface"`; returns empty list on failure

---

### US-008: Implement HackerNews node
**Description:** As a business and technical persona subscriber, I want top HN AI stories included so that community-validated discussions are surfaced.

**Acceptance Criteria:**
- [ ] `hn_node(state: AgentState) -> dict` fetches top 30 story IDs from HN Firebase API
- [ ] Filters by keyword list: `["ai", "llm", "gpt", "gemini", "claude", "openai", "anthropic", "mistral", "langchain", "agent"]`
- [ ] Keyword list is a module-level constant (easy to extend)
- [ ] Returns up to 5 stories; includes HN score and comment count in summary; `source="hackernews"`
- [ ] Returns empty list on failure

---

### US-009: Implement Reddit node
**Description:** As a technical persona subscriber, I want top Reddit AI posts included so that practitioner discussions from r/LocalLLaMA and r/MachineLearning are captured.

**Acceptance Criteria:**
- [ ] `reddit_node(state: AgentState) -> dict` fetches top daily posts from r/LocalLLaMA and r/MachineLearning
- [ ] Returns up to 5 posts per subreddit; includes score and up to 400 chars of post text
- [ ] `source="reddit"`; returns empty list on failure

---

### US-010: Implement YouTube transcript node
**Description:** As a technical persona subscriber, I want recent YouTube AI video transcripts included so that key video insights are surfaced without watching.

**Acceptance Criteria:**
- [ ] `youtube_node(state: AgentState) -> dict` scrapes latest video IDs from 2+ hardcoded AI channels
- [ ] Channel list is a module-level constant (easy to extend)
- [ ] Fetches captions via `youtube-transcript-api`; uses first 1000 chars
- [ ] `source="youtube"`; returns empty list when transcripts unavailable or scraping fails

---

### US-011: Implement aggregation node
**Description:** As a developer, I need a node that merges all source outputs into a single list so that downstream curation has a unified input.

**Acceptance Criteria:**
- [ ] `aggregate_node(state: AgentState) -> dict` concatenates all 8 `*_news` lists into `raw_news`
- [ ] Deduplicates by URL (case-insensitive); preserves first occurrence
- [ ] Logs item count per source to stdout
- [ ] Returns `{"raw_news": [...]}`

---

### US-012: Implement LLM curation node
**Description:** As a subscriber, I want irrelevant or stale articles filtered out by AI so that only high-signal content reaches me.

**Acceptance Criteria:**
- [ ] `curate_node(state: AgentState) -> dict` sends `raw_news` to Gemini 2.5 Flash
- [ ] Prompt instructs the model to: (1) remove off-topic/stale items, (2) categorize remainder into `business`, `technical`, `research`
- [ ] Response parsed as JSON `{"business": [...], "technical": [...], "research": [...]}` with retry on parse failure (up to 2 retries)
- [ ] Validates all three keys exist; raises `ValueError` if response is malformed after retries
- [ ] Also returns flat `curated_news` list (union of all three categories)
- [ ] Uses `GOOGLE_API_KEY` from environment; raises `EnvironmentError` if missing

---

### US-013: Implement report generation node
**Description:** As a subscriber, I want a readable, well-formatted Markdown report so that I can quickly scan the day's most important GenAI news.

**Acceptance Criteria:**
- [ ] `summarize_node(state: AgentState) -> dict` sends categorized news to Gemini 2.5 Flash (temperature=0.2)
- [ ] Report contains three sections: Business & Strategy, Architects & Developers, Research Frontiers — each only rendered if non-empty
- [ ] Each article formatted as bold hyperlink + 2–3 sentence insight
- [ ] Appends collapsible "Raw Intelligence Index" via HTML `<details>` tag with per-source tables
- [ ] Returns `{"final_report": "...markdown string..."}`

---

### US-014: Implement email distribution node
**Description:** As a subscriber, I want the report delivered to my inbox automatically so that I don't need to visit any website.

**Acceptance Criteria:**
- [ ] `email_node(state: AgentState) -> dict` loads subscribers from two sources in priority order: (1) Google Sheets CSV export URL (if `GOOGLE_SHEET_URL` env var set), (2) local `subscribers.json` fallback
- [ ] Deduplicates and validates emails (basic format check)
- [ ] Strips raw intelligence index section from email body (HTML-incompatible collapsible)
- [ ] Converts Markdown to HTML with inline CSS (readable in Gmail)
- [ ] Adds compact source summary table (source name + item count)
- [ ] Sends via SMTP-SSL using `GMAIL_USER` and `GMAIL_APP_PASSWORD` env vars; sender added as BCC
- [ ] Returns `{"email_log": {"status": "success"|"failed", "subscribers_found": N, "emails_sent": N, "errors": [...]}}`
- [ ] Gracefully logs and continues if individual email send fails; does not abort entire run

---

### US-015: Build LangGraph pipeline
**Description:** As a developer, I need the nodes wired into a LangGraph graph so that the workflow executes correctly with parallel ingestion and sequential processing.

**Acceptance Criteria:**
- [ ] `build_graph()` in `src/graph.py` returns a compiled `StateGraph`
- [ ] All 8 fetch nodes connected from `START` (parallel fan-out)
- [ ] All 8 fetch nodes connect to `aggregate` node (fan-in)
- [ ] Sequential path: `aggregate → curate → summarize → email → END`
- [ ] Graph compiles without errors; `graph.get_graph().draw_mermaid()` produces valid output

---

### US-016: Build CLI entrypoint
**Description:** As a developer or operator, I want a CLI to trigger the agent locally so that I can test, backfill, or manually run a report.

**Acceptance Criteria:**
- [ ] `main.py` accepts `--query` (default: "latest breakthroughs, releases, and news in Generative AI"), `--days` (default: 2), `--output` (default: `reports/`)
- [ ] Validates `GOOGLE_API_KEY` and `TAVILY_API_KEY` at startup; prints actionable error and exits if missing
- [ ] Creates `reports/` and `state/` directories if absent
- [ ] Saves Markdown report to `reports/YYYY-MM-DD_report.md`
- [ ] Saves full JSON state to `state/YYYY-MM-DD_state.json` (with `default=str` serializer for non-JSON types)
- [ ] Prints success summary to stdout on completion

---

### US-017: Configure GitHub Actions for daily automation
**Description:** As an operator, I want the agent to run daily without manual intervention so that subscribers receive fresh reports automatically.

**Acceptance Criteria:**
- [ ] `.github/workflows/daily_news.yml` triggers on `schedule: cron: '30 2 * * *'` (8:00 AM IST = 02:30 UTC)
- [ ] Workflow also triggerable via `workflow_dispatch` for manual runs
- [ ] All required secrets (`GOOGLE_API_KEY`, `TAVILY_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`) documented in workflow file comments
- [ ] Workflow installs dependencies from `requirements.txt`, runs `python main.py`, and uploads `reports/` as artifact
- [ ] Workflow fails fast and surfaces error logs on node failure

---

### US-018: Write unit tests for all nodes
**Description:** As a developer, I want each node tested in isolation so that regressions are caught without live API calls.

**Acceptance Criteria:**
- [ ] `tests/` directory with one test file per node
- [ ] All external API clients mocked (no live calls in CI)
- [ ] Tests cover: happy path (valid response), empty response (API returns nothing), failure path (API exception → empty list returned)
- [ ] `pytest` runs cleanly with no failures
- [ ] Test coverage ≥ 80% for `src/nodes.py`

---

## Functional Requirements

- FR-1: The system must ingest news from exactly 8 sources: Tavily, RSS, arXiv, GitHub, HuggingFace, HackerNews, Reddit, YouTube
- FR-2: All 8 ingestion nodes must execute in parallel (LangGraph fan-out from START)
- FR-3: Each ingestion node must return an empty list (not raise) on API failure, so one source outage does not abort the pipeline
- FR-4: Aggregation must deduplicate items by URL before passing to curation
- FR-5: Curation must use Gemini 2.5 Flash and categorize items into exactly three keys: `business`, `technical`, `research`
- FR-6: Report generation must only render a persona section if that section has at least one item
- FR-7: Email distribution must load subscribers from Google Sheets first, falling back to `subscribers.json`
- FR-8: The pipeline must complete without human intervention when all API credentials are valid
- FR-9: All required API keys must be configurable via environment variables; no keys hardcoded in source
- FR-10: The system must produce two output artifacts per run: a Markdown report and a full JSON state dump

---

## Non-Goals

- No web dashboard or UI for reading reports
- No real-time or streaming news (batch daily only)
- No per-subscriber content personalization (all subscribers receive the same report)
- No user authentication, login, or subscription management UI
- No NLP deduplication (URL-based dedup only)
- No support for LLM providers other than Google Gemini
- No multi-language support (English only)
- No historical trend analysis or cross-day comparisons
- No retry/backoff for email delivery failures beyond a single attempt per recipient

---

## Technical Considerations

- **Framework**: LangGraph for orchestration; `TypedDict` for state; no Pydantic models in the pipeline hot path (avoids version conflicts)
- **LLM**: `langchain-google-genai` with `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` for both curation and summarization
- **Dependency pinning**: All packages should be pinned with compatible version ranges to avoid `pydantic<2.10.0` class of breakage
- **Secrets**: All credentials via environment variables; use `python-dotenv` for local dev, GitHub Actions secrets for CI
- **Parallelism**: LangGraph natively parallelizes nodes connected from START; no explicit threading needed
- **YouTube scraping**: HTML scraping is fragile; scraping logic should be isolated in a helper function for easy replacement
- **arXiv lag**: Query with a 2-day buffer beyond `state["days"]` to account for arXiv's indexing delay
- **Gmail SMTP**: Use `smtplib.SMTP_SSL` on port 465; requires a Gmail App Password (not account password)

---

## Success Metrics

- Pipeline runs end-to-end in under 5 minutes on GitHub Actions
- At least 6 of 8 sources return non-empty results on a typical run
- Generated report contains at least 10 unique curated items across the three personas
- Email delivery success rate ≥ 95% across runs (measured via `email_log`)
- Zero manual interventions required for 30 consecutive daily runs after initial setup

---

## Open Questions

1. Should the GitHub Pages deployment (hosting reports publicly) be in scope for v1, or deferred?
2. Should `subscribers.json` support metadata per subscriber (e.g., name, preferred persona) for future personalization?
3. Should there be a hard cap on total `raw_news` items sent to the LLM (to control token cost), and if so, what is the cap?
4. Should the YouTube node be replaced with a YouTube Data API v3 call for reliability, given HTML scraping brittleness?
5. Should failed runs notify an admin email rather than silently failing in GitHub Actions?
