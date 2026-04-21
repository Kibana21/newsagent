# PRD: Gen AI News Agent — AIA Singapore Edition

## Introduction

The Gen AI News Agent is an automated intelligence pipeline that ingests GenAI news daily from eight parallel sources (web search, RSS, arXiv, GitHub, HuggingFace, HackerNews, Reddit, YouTube), uses Gemini 2.5 Flash to curate, categorize, and enrich content, then delivers a beautifully formatted email digest to subscribers.

The digest is designed for two distinct audiences at AIA Singapore:
- **Business readers** — leaders and strategy teams who need to know what GenAI means for the insurance industry, what competitors are doing, and what regulators are signalling, without wading through technical detail
- **Tech readers** — engineers and data scientists who want models, tools, open-source releases, and research papers with enough depth to act on immediately

Every email is structured so both audiences get full value from the same send. The pipeline runs on a daily GitHub Actions schedule at 8:00 AM SGT and requires no manual intervention.

The reference implementation (by shubhamshardul-work) exists as a working prototype. This PRD defines requirements for a clean, production-quality version with better configurability, observability, testability, and an insurance-industry lens.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| **Language** | Python 3.11+ | Broad AI/ML ecosystem, async support |
| **Orchestration** | LangGraph | Native parallel fan-out, typed state, built-in retry |
| **LLM** | Google Gemini 2.5 Flash via `langchain-google-genai` | Fast, cheap, large context window for bulk curation |
| **GCP Auth** | Service account JSON (`video-key.json`) via `google-auth` | Authenticates to Vertex AI / Gemini without an API key |
| **Scheduling** | APScheduler (`apscheduler`) | Cron-style scheduling inside a long-running Python process; no external infra needed |
| **Web search** | Tavily API via `langchain-tavily` | Purpose-built for LLM pipelines, returns pre-summarised content |
| **RSS parsing** | `feedparser` | Battle-tested, handles malformed feeds gracefully |
| **HTTP client** | `requests` | Simple sync calls for GitHub, HuggingFace, HN, Reddit APIs |
| **Email delivery** | `smtplib` (stdlib) + `email` (stdlib) | No extra deps; SMTP-SSL to Gmail on port 465 |
| **Markdown → HTML** | `markdown` (Python) | Converts report to inline-CSS HTML for Gmail |
| **YouTube transcripts** | `youtube-transcript-api` | Retrieves captions without YouTube Data API quota |
| **State persistence** | Plain JSON files in `state/` | Zero-infra, human-readable, easy to inspect |
| **Env management** | `python-dotenv` | Loads `.env` for local runs |
| **Testing** | `pytest` + `unittest.mock` | Node-level isolation without live API calls |
| **Dependency management** | `requirements.txt` with pinned versions | Reproducible installs |

### Runtime Model

```
python scheduler.py          # starts the long-running process
       │
       └── APScheduler (cron: 08:00 SGT daily)
              │
              └── python main.py   # executes the full LangGraph pipeline
                     │
                     ├── [parallel] tavily_node
                     ├── [parallel] rss_node
                     ├── [parallel] arxiv_node
                     ├── [parallel] github_node
                     ├── [parallel] hf_node
                     ├── [parallel] hn_node
                     ├── [parallel] reddit_node
                     └── [parallel] youtube_node
                            │
                            └── aggregate_node → curate_node → summarize_node → email_node
```

`scheduler.py` is the only long-running process. `main.py` can also be invoked directly for manual/test runs. No Docker, no GitHub Actions, no cloud infra required.

---

## Goals

- Ingest GenAI news from 8 heterogeneous sources in parallel with a configurable lookback window
- Curate and deduplicate content using an LLM, removing off-topic or stale items
- Categorize curated news into **four** audience sections: Business & Strategy, Tech & Engineering, Research Frontiers, InsurTech & AIA Relevance
- Surface insurance-specific intelligence: competitor moves, MAS/APAC regulatory signals, and use-case applicability scores
- Generate a richly formatted HTML email that is scannable in 2 minutes and deep-readable in 10
- Deliver to a managed subscriber list via Gmail SMTP daily
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
- [ ] Source news fields: `tavily_news`, `rss_news`, `arxiv_news`, `github_news`, `hf_news`, `hn_news`, `reddit_news`, `youtube_news` (all `List[dict]`)
- [ ] Processing fields: `search_query` (str), `days` (int), `raw_news` (List[dict]), `curated_news` (List[dict]), `categorized_news` (dict with keys `business`, `technical`, `research`, `insurtech`), `buzz_scores` (dict mapping url → int), `sent_urls` (List[str]), `final_report` (str), `email_log` (dict)
- [ ] Each news item dict has consistent keys: `title` (str), `url` (str), `summary` (str), `source` (str), `published_at` (str ISO8601), `insurance_score` (int 1–3, default 1)
- [ ] Mypy or Pyright passes with no errors on `state.py`

---

### US-003: Implement Tavily web search node
**Description:** As a user, I want the agent to fetch real-time GenAI news from the web so that breaking news is always captured.

**Acceptance Criteria:**
- [ ] `tavily_node(state: AgentState) -> dict` in `src/nodes.py`
- [ ] Uses `TAVILY_API_KEY` from environment; raises `EnvironmentError` if missing
- [ ] Runs two searches in sequence: (1) general GenAI query, (2) insurance-specific query e.g. "AI insurance underwriting claims Singapore {year}"
- [ ] Returns up to 8 results total; each item has `title`, `url`, `summary`, `source="tavily"`, `published_at`
- [ ] Empty list returned (not exception) on API failure
- [ ] Unit-testable by mocking the Tavily client

---

### US-004: Implement RSS feed ingestion node
**Description:** As a user, I want the agent to pull from curated RSS feeds so that major publisher and regulator news is included.

**Acceptance Criteria:**
- [ ] `rss_node(state: AgentState) -> dict` fetches from at minimum 5 hardcoded feeds
- [ ] Feed list must include: OpenAI blog, TechCrunch AI, VentureBeat AI, MAS (Monetary Authority of Singapore) newsroom, IMDA Singapore newsroom
- [ ] Feed list is a module-level constant (easy to add/remove without logic changes)
- [ ] Filters articles older than `state["days"]` using publication date
- [ ] Strips HTML tags from descriptions
- [ ] Returns up to 8 most recent items across all feeds; `source="rss"`
- [ ] Returns empty list (not exception) if all feeds fail

---

### US-005: Implement arXiv research papers node
**Description:** As a researcher or tech subscriber, I want recent AI research papers included so that academic breakthroughs are surfaced daily.

**Acceptance Criteria:**
- [ ] `arxiv_node(state: AgentState) -> dict` queries cs.AI, cs.CL, cs.LG categories
- [ ] Filters papers using ISO timestamp against `state["days"]` lookback with 2-day arXiv lag buffer
- [ ] Summary truncated to 200 characters; `source="arxiv"`
- [ ] Returns up to 5 results; empty list on failure

---

### US-006: Implement GitHub trending repositories node
**Description:** As a tech subscriber, I want trending AI repos included so that new open-source tools are surfaced.

**Acceptance Criteria:**
- [ ] `github_node(state: AgentState) -> dict` uses GitHub Search API (unauthenticated or with `GITHUB_TOKEN`)
- [ ] Searches repos with topics `llm` or `generative-ai` created in last N days, sorted by stars
- [ ] Returns up to 3 results; title includes star count; `source="github"`
- [ ] Returns empty list on API error or rate limit

---

### US-007: Implement HuggingFace trending models node
**Description:** As a tech subscriber, I want trending HuggingFace models included so that newly released models are highlighted.

**Acceptance Criteria:**
- [ ] `hf_node(state: AgentState) -> dict` calls HuggingFace Models API sorted by trending score
- [ ] Returns up to 3 models with tags (up to 6), download count, and model card URL
- [ ] `source="huggingface"`; returns empty list on failure

---

### US-008: Implement HackerNews node
**Description:** As a business and tech subscriber, I want top HN AI stories included so that community-validated discussions are surfaced.

**Acceptance Criteria:**
- [ ] `hn_node(state: AgentState) -> dict` fetches top 30 story IDs from HN Firebase API
- [ ] Filters by keyword list: `["ai", "llm", "gpt", "gemini", "claude", "openai", "anthropic", "mistral", "langchain", "agent", "insurance", "fintech", "underwriting"]`
- [ ] Keyword list is a module-level constant (easy to extend)
- [ ] Returns up to 5 stories; includes HN score and comment count in summary; `source="hackernews"`
- [ ] Returns empty list on failure

---

### US-009: Implement Reddit node
**Description:** As a tech subscriber, I want top Reddit AI posts included so that practitioner discussions are captured.

**Acceptance Criteria:**
- [ ] `reddit_node(state: AgentState) -> dict` fetches top daily posts from r/LocalLLaMA and r/MachineLearning
- [ ] Returns up to 5 posts per subreddit; includes score and up to 400 chars of post text
- [ ] `source="reddit"`; returns empty list on failure

---

### US-010: Implement YouTube transcript node
**Description:** As a tech subscriber, I want recent YouTube AI video transcripts included so that key video insights are surfaced without watching.

**Acceptance Criteria:**
- [ ] `youtube_node(state: AgentState) -> dict` scrapes latest video IDs from 2+ hardcoded AI channels
- [ ] Channel list is a module-level constant (easy to extend)
- [ ] Fetches captions via `youtube-transcript-api`; uses first 1000 chars
- [ ] `source="youtube"`; returns empty list when transcripts unavailable or scraping fails

---

### US-011: Implement aggregation node with buzz scoring and no-repeat filter
**Description:** As a developer, I need a node that merges all source outputs, scores cross-source buzz, and filters previously sent stories so that downstream curation is clean and non-repetitive.

**Acceptance Criteria:**
- [ ] `aggregate_node(state: AgentState) -> dict` concatenates all 8 `*_news` lists into `raw_news`
- [ ] Deduplicates by URL (case-insensitive, strip trailing slashes); preserves first occurrence
- [ ] Computes `buzz_scores`: count how many distinct sources contain the same story (matched by URL or title similarity ≥ 90%); stores as `{url: count}` dict
- [ ] Loads `state/sent_urls.json` (rolling 7-day log); removes any `raw_news` item whose URL appears in that log
- [ ] Logs item count per source and total after dedup/filter to stdout
- [ ] Returns `{"raw_news": [...], "buzz_scores": {...}}`

---

### US-012: Implement LLM curation node
**Description:** As a subscriber, I want irrelevant or stale articles filtered out by AI and insurance-scored so that only high-signal, relevant content reaches me.

**Acceptance Criteria:**
- [ ] `curate_node(state: AgentState) -> dict` sends `raw_news` and `buzz_scores` to Gemini 2.5 Flash
- [ ] Prompt instructs the model to:
  - Remove off-topic or stale items
  - Categorize into `business`, `technical`, `research`, `insurtech`
  - Assign `insurance_score` (1=low, 2=medium, 3=high relevance to life insurance / APAC financial services) to every item
  - Flag items involving Prudential, Great Eastern, Manulife, FWD, Allianz, or AXA as `competitor: true`
  - Flag items involving MAS, HKIA, OJK, or APAC AI regulation as `regulatory: true`
- [ ] Response parsed as JSON with four category keys; retry on parse failure up to 2 times
- [ ] Validates all four keys exist; raises `ValueError` if malformed after retries
- [ ] Returns flat `curated_news` list and `categorized_news` dict
- [ ] Authenticates using the service account JSON at the path in `GOOGLE_APPLICATION_CREDENTIALS` env var (pointing to `video-key.json`); raises `EnvironmentError` with a clear message if the file is missing or the path is unset

---

### US-013: Implement report generation node
**Description:** As a subscriber, I want a richly formatted email that is scannable in 2 minutes and deep-readable in 10, with clear separation between what matters for business and what matters for engineering.

**Acceptance Criteria:**
- [ ] `summarize_node(state: AgentState) -> dict` sends categorized news + buzz_scores to Gemini 2.5 Flash (temperature=0.2)
- [ ] Email opens with a **TL;DR block**: 3 bullet points, one sentence each, absolute must-reads of the day — selected by the LLM based on buzz score and insurance relevance
- [ ] Four persona sections rendered (only if non-empty), each with a header showing item count e.g. `Business & Strategy (4)`:
  - **Business & Strategy** — enterprise moves, product launches, funding; each item includes a "Boardroom angle" sentence framed for insurance leadership
  - **Tech & Engineering** — models, tools, open-source; each item includes a "Build this at AIA" sentence mapping the technology to an insurance use case (e.g. claims automation, underwriting scoring, fraud detection)
  - **Research Frontiers** — arXiv papers; includes one "Paper of the Day" card with a 4-sentence plain-English explainer accessible to non-academics
  - **InsurTech & AIA Relevance** — insurance-specific stories, competitor moves (tagged 🏢), regulatory signals (tagged ⚖️), APAC/Singapore AI initiatives; items with `insurance_score=3` from other sections are also promoted here
- [ ] Items appearing in 3+ sources display a **"Trending across N sources"** inline badge
- [ ] Each item shows a freshness tag: `[2h ago]`, `[1d ago]`, computed from `published_at`
- [ ] **Friday editions** include a "Week in Review" callout: LLM-generated single paragraph on the week's most important development for an APAC life insurer
- [ ] Email closes with a **Source Health footer**: compact table showing each source, items contributed today, and ✅/❌ status
- [ ] Appends collapsible "Raw Intelligence Index" (for Markdown file only, stripped before email send)
- [ ] Returns `{"final_report": "...html/markdown string..."}`

---

### US-014: Implement email distribution node with sent-URL tracking
**Description:** As a subscriber, I want the report delivered to my inbox automatically, and I want the system to track what has been sent so stories are never repeated.

**Acceptance Criteria:**
- [ ] `email_node(state: AgentState) -> dict` loads subscribers from: (1) Google Sheets CSV export URL if `GOOGLE_SHEET_URL` env var set, (2) local `subscribers.json` fallback
- [ ] `subscribers.json` schema: `[{"email": "...", "name": "...", "persona": "all|business|tech"}]` — persona field reserved for future use, all subscribers receive the same email for now
- [ ] Deduplicates and validates emails (basic format check)
- [ ] Strips Raw Intelligence Index collapsible from email body
- [ ] Converts Markdown to HTML with inline CSS; tested readable in Gmail
- [ ] Sends via SMTP-SSL (`GMAIL_USER`, `GMAIL_APP_PASSWORD`); sender added as BCC
- [ ] After successful send, appends all sent URLs from today's `curated_news` to `state/sent_urls.json`, pruning entries older than 7 days
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
- [ ] Validates `GOOGLE_APPLICATION_CREDENTIALS` (path to `video-key.json`) and `TAVILY_API_KEY` at startup; prints actionable error and exits if missing or file not found
- [ ] Creates `reports/`, `state/` directories if absent
- [ ] Saves Markdown report to `reports/YYYY-MM-DD_report.md`
- [ ] Saves full JSON state to `state/YYYY-MM-DD_state.json` (with `default=str` serializer)
- [ ] Prints success summary to stdout on completion

---

### US-017: Implement Python scheduler for daily automation
**Description:** As an operator, I want the agent to run daily at 8:00 AM SGT automatically by simply keeping a Python process alive, with no external CI/CD or cloud infrastructure required.

**Acceptance Criteria:**
- [ ] `scheduler.py` at project root uses APScheduler (`BlockingScheduler`) to trigger `main.py` logic on a cron schedule: `hour=8, minute=0, timezone="Asia/Singapore"`
- [ ] Scheduler logs next scheduled run time on startup
- [ ] Running `python scheduler.py` is the only command needed to start automated daily delivery
- [ ] `python main.py` still works independently for manual/test runs without touching the scheduler
- [ ] If the pipeline raises an unhandled exception, the scheduler logs the full traceback but continues running (does not crash the process) so the next day's run is not affected
- [ ] `state/sent_urls.json` persists naturally on disk between runs since scheduler and pipeline share the same filesystem
- [ ] All required env vars documented in `.env.example`: `GOOGLE_APPLICATION_CREDENTIALS` (path to `video-key.json`), `TAVILY_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, optionally `GOOGLE_SHEET_URL`, `GITHUB_TOKEN`

---

### US-018: Write unit tests for all nodes
**Description:** As a developer, I want each node tested in isolation so that regressions are caught without live API calls.

**Acceptance Criteria:**
- [ ] `tests/` directory with one test file per node
- [ ] All external API clients mocked (no live calls in CI)
- [ ] Tests cover: happy path, empty response, failure path (API exception → empty list)
- [ ] `curate_node` tests verify insurance scoring and competitor/regulatory flagging logic via mocked LLM responses
- [ ] `aggregate_node` tests verify buzz scoring, deduplication, and sent-URL filtering
- [ ] `pytest` runs cleanly with no failures
- [ ] Test coverage ≥ 80% for `src/nodes.py`

---

### US-019: Monthly "Best of the Month" email
**Description:** As a subscriber, I want a monthly roundup so that I can share the most important GenAI-for-insurance developments with colleagues who don't read the daily digest.

**Acceptance Criteria:**
- [ ] On the 1st of each month, GitHub Actions triggers an additional workflow run with `--mode monthly`
- [ ] Monthly email reads `state/sent_urls.json` history for the past 30 days, selects top 10 stories ranked by buzz score and `insurance_score`
- [ ] Subject line: `AIA GenAI Intelligence — [Month Year] Top 10`
- [ ] Formatted identically to the daily email but with a single "Best of Month" section replacing the four daily sections
- [ ] No new API calls required — sourced entirely from existing state

---

## Functional Requirements

- FR-1: Ingest news from 8 sources: Tavily, RSS, arXiv, GitHub, HuggingFace, HackerNews, Reddit, YouTube
- FR-2: All 8 ingestion nodes execute in parallel (LangGraph fan-out from START)
- FR-3: Each ingestion node returns an empty list (not raises) on API failure
- FR-4: Tavily runs two searches: one general GenAI query, one insurance-specific query
- FR-5: RSS feeds must include MAS and IMDA newsroom feeds alongside general AI publishers
- FR-6: Aggregation deduplicates by URL, computes cross-source buzz scores, and filters URLs sent in the past 7 days
- FR-7: Curation categorizes into four sections: `business`, `technical`, `research`, `insurtech`
- FR-8: Curation assigns `insurance_score` (1–3) and flags `competitor` and `regulatory` items on every curated article
- FR-9: Report opens with a 3-bullet TL;DR block selected by LLM for maximum relevance
- FR-10: Business section items include a "Boardroom angle" sentence; Tech items include a "Build this at AIA" sentence
- FR-11: InsurTech section aggregates insurance-specific items and promotes high-scoring items from other sections
- FR-12: Friday emails include a "Week in Review" paragraph for APAC life insurers
- FR-13: Items trending across 3+ sources display a buzz badge inline
- FR-14: Each item displays a human-readable freshness tag computed from `published_at`
- FR-15: Source Health footer appears in every email showing per-source item count and status
- FR-16: Sent URLs logged to `state/sent_urls.json` after each successful send; pruned to 7-day window
- FR-17: `sent_urls.json` persisted on disk between scheduler runs; no external cache needed
- FR-18: Monthly digest runs on the 1st of each month, requires no new API calls
- FR-19: All credentials configured via environment variables or files; nothing hardcoded — `GOOGLE_APPLICATION_CREDENTIALS` points to `video-key.json` on disk; `video-key.json` must never be committed to source control

---

## Non-Goals

- No web dashboard or UI for reading reports
- No real-time or streaming news (batch daily only)
- No per-subscriber personalized content in v1 (persona field in subscribers.json reserved for future use)
- No user authentication or subscription management UI
- No NLP-based deduplication (URL + title similarity threshold only)
- No support for LLM providers other than Google Gemini
- No multi-language support (English only)
- No retry/backoff for email delivery failures beyond a single attempt per recipient
- No analysis of AIA's internal data or proprietary systems

---

## Technical Considerations

- **Framework**: LangGraph for orchestration; `TypedDict` for state; no Pydantic models in the pipeline hot path
- **LLM**: `langchain-google-genai` with `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` for curation and summarization; authenticated via `google.oauth2.service_account.Credentials` loaded from `video-key.json` — pass credentials object directly to the `ChatGoogleGenerativeAI` constructor rather than relying on `GOOGLE_API_KEY`
- **Insurance keywords**: maintain a module-level constant `INSURANCE_KEYWORDS` used across curation prompts and HN filtering: `["insurance", "underwriting", "claims", "actuarial", "reinsurance", "insurtech", "life insurance", "MAS", "IMDA", "finserv", "financial services"]`
- **Competitor list**: module-level constant `COMPETITOR_INSURERS`: `["Prudential", "Great Eastern", "Manulife", "FWD", "Allianz", "AXA", "Sunlife", "Zurich"]`
- **Buzz scoring**: title similarity computed with `difflib.SequenceMatcher`; threshold 0.9 is sufficient for near-duplicate detection without heavy NLP deps
- **sent_urls.json**: stored in `state/`; each entry: `{"url": "...", "sent_at": "YYYY-MM-DD"}`; pruned on every aggregation run
- **Dependency pinning**: all packages pinned with compatible version ranges to avoid `pydantic<2.10.0` class of breakage
- **YouTube scraping**: isolated in a helper function for easy replacement with YouTube Data API v3
- **arXiv lag**: query with 2-day buffer beyond `state["days"]`
- **Gmail SMTP**: `smtplib.SMTP_SSL` on port 465; requires Gmail App Password
- **Scheduler**: `APScheduler` `BlockingScheduler` with `Asia/Singapore` timezone; `pytz` or `zoneinfo` (Python 3.9+) for timezone handling; add `apscheduler` to `requirements.txt`

---

## Success Metrics

- Pipeline runs end-to-end in under 5 minutes on GitHub Actions
- At least 6 of 8 sources return non-empty results on a typical run
- Every email contains at least 3 InsurTech section items on a typical weekday
- At least 1 item flagged as `competitor` or `regulatory` per week
- No story repeated within a 7-day window (verified via sent_urls log)
- Email delivery success rate ≥ 95% across runs
- Zero manual interventions required for 30 consecutive daily runs after initial setup

---

## Open Questions

1. Should the monthly digest be sent to a different (wider) distribution list than the daily digest — e.g., department heads who don't want daily email?
2. Should `insurance_score` thresholds be tunable via a config file rather than hardcoded in the prompt, to let non-developers adjust relevance calibration?
3. Should competitor flagging include AIA's own press releases as a "self-monitoring" source?
4. Should the YouTube node be replaced with YouTube Data API v3 for reliability, given HTML scraping brittleness?
5. Should failed runs send an alert email to an admin address rather than only logging to stdout?
6. Should the Friday "Week in Review" paragraph be a separate email send or appended to the Friday daily digest?
