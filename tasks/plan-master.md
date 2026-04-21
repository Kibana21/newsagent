# Plan (Master): Gen AI News Agent — AIA Singapore Edition

Master plan for implementing the PRD at [`tasks/prd-gen-ai-news-agent.md`](./prd-gen-ai-news-agent.md). Each implementation phase has a dedicated plan file in this folder (see [Phase Map](#phase-map)).

---

## Context

Greenfield Python project. Only `.gitignore`, a stub `README.md`, `video-key.json` (GCP service account), the PRD, and these plan documents exist. Python 3.12 venv in place. No source code.

**Goal**: a daily email digest that curates GenAI news from 8 sources into four audience sections (Business & Strategy, Tech & Engineering, Research Frontiers, InsurTech & AIA Relevance) for both business and technical readers at AIA Singapore. Runs as a long-lived Python process via APScheduler.

---

## Locked Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | LLM auth: **Vertex AI** via `langchain-google-vertexai` + `ChatVertexAI` using `video-key.json` | `langchain-google-genai` does not accept service-account credentials; Vertex AI is the correct path |
| 2 | Build order: **walking skeleton first** (1 email, 2 sources, 2 personas) | Validates auth + graph + SMTP end-to-end before investing in sources or personas |
| 3 | Scheduler: **APScheduler `BlockingScheduler`** in `scheduler.py` | No GitHub Actions, no cloud infra; local/VM-friendly |
| 4 | State: **plain JSON files** in `state/` | Zero infra; human-readable; easy to inspect |
| 5 | Plan-before-code: **all phase plans written to `tasks/`** before any source code | Per user direction; planning artifacts travel with the repo |

---

## Phase Map

| Phase | Plan File | Goal | PRD Stories |
|---|---|---|---|
| 0 | [plan-phase-0-scaffold.md](./plan-phase-0-scaffold.md) | Project structure, deps, types, constants | US-001, US-002 |
| 1 | [plan-phase-1-walking-skeleton.md](./plan-phase-1-walking-skeleton.md) | One real email end-to-end, 2 sources | US-003 (partial), US-011–US-016 (minimal) |
| 2 | [plan-phase-2-ingestion-sources.md](./plan-phase-2-ingestion-sources.md) | All 8 sources operational | US-004, US-005, US-006, US-007, US-008, US-009, US-010 |
| 3 | [plan-phase-3-insurance-intelligence.md](./plan-phase-3-insurance-intelligence.md) | Buzz scoring, 4-category curation, full email layout | US-011 (full), US-012 (full), US-013 (full), US-014 (full) |
| 4 | [plan-phase-4-scheduler-and-tests.md](./plan-phase-4-scheduler-and-tests.md) | APScheduler + pytest suite ≥80% coverage | US-017, US-018 |
| 5 | [plan-phase-5-monthly-digest.md](./plan-phase-5-monthly-digest.md) | Monthly "Best of" email | US-019 |

---

## Dependency Order

```
Phase 0 (scaffold)
   ↓
Phase 1 (walking skeleton)           ← blocks everything below
   ↓
Phase 2 (all sources)   Phase 3 (intelligence)    ← can run in parallel
   ↓                       ↓
           Phase 4 (scheduler + tests)
                          ↓
                  Phase 5 (monthly digest)
```

Phases 2 and 3 are independent. Recommended order: **Phase 2 first** (sources produce data), **then Phase 3** (intelligence consumes and enriches).

---

## Target File & Directory Structure

```
newsagent/
├── .env.example                   # All required env vars
├── .gitignore                     # Already exists
├── README.md                      # Setup in <10 steps
├── requirements.txt               # Pinned deps
├── pyproject.toml                 # pytest + mypy + coverage config
├── video-key.json                 # GCP service account (already present)
├── subscribers.json               # Local fallback recipient list
├── scheduler.py                   # APScheduler entrypoint (Phase 4)
├── src/
│   ├── __init__.py
│   ├── state.py                   # AgentState + NewsItem TypedDicts
│   ├── config.py                  # Module-level constants (feeds, keywords, competitors)
│   ├── llm.py                     # Vertex AI client factory
│   ├── prompts.py                 # LLM prompt templates
│   ├── render.py                  # Markdown → inline-CSS HTML; freshness tags; Source Health
│   ├── monthly.py                 # Monthly digest builder (Phase 5)
│   ├── graph.py                   # build_graph() — LangGraph wiring
│   ├── main.py                    # CLI entrypoint
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── tavily_node.py
│   │   ├── rss_node.py
│   │   ├── arxiv_node.py
│   │   ├── github_node.py
│   │   ├── hf_node.py
│   │   ├── hn_node.py
│   │   ├── reddit_node.py
│   │   ├── youtube_node.py
│   │   ├── aggregate_node.py
│   │   ├── curate_node.py
│   │   ├── summarize_node.py
│   │   └── email_node.py
│   └── utils/
│       ├── __init__.py
│       ├── dates.py               # Freshness strings, ISO parsing
│       ├── text.py                # HTML strip, title similarity
│       ├── state_io.py            # sent_urls.json operations
│       └── subscribers.py         # Google Sheets + subscribers.json loader
├── tests/
│   ├── conftest.py
│   ├── fixtures/                  # Sample feed XML, Tavily JSON, HN IDs
│   └── test_*_node.py             # One per node
├── reports/                       # Runtime-created; gitignored
└── state/                         # Runtime-created; sent_urls.json lives here
```

---

## Critical Files (ordered by design risk)

| File | Why it's critical |
|---|---|
| `src/state.py` | Data contract every node reads/writes. Wrong shape = cascading breakage. |
| `src/llm.py` | Vertex AI auth. Only place touching `video-key.json`. |
| `src/prompts.py` | LLM prompt templates. Prompt quality = output quality. |
| `src/graph.py` | LangGraph wiring — parallel fan-out, sequential tail. |
| `src/nodes/aggregate_node.py` | Buzz scoring + sent-URL filter. Core to "never see a story twice" and "Trending across N sources". |
| `src/nodes/curate_node.py` | Insurance intelligence entry point (four categories, `insurance_score`, competitor/regulatory flags). |
| `src/nodes/summarize_node.py` | The user-facing email layout. Where "interesting for both Tech and Business" is realized. |
| `scheduler.py` | The only long-running process. Must survive pipeline exceptions. |

---

## Dependency Pinning

```
langgraph~=0.2.50
langchain-core~=0.3.20
langchain-google-vertexai~=2.0.10
langchain-tavily~=0.1.0
google-auth~=2.35.0
google-cloud-aiplatform~=1.70.0
feedparser~=6.0.11
requests~=2.32.0
markdown~=3.7
youtube-transcript-api~=0.6.2
apscheduler~=3.10.4
python-dotenv~=1.0.1
pydantic==2.9.2
pytest~=8.3.0
pytest-cov~=5.0.0
mypy~=1.11.0
```

`~=X.Y.Z` allows patch upgrades, blocks minor bumps. `pydantic` is pinned exactly per the PRD's explicit concern about `pydantic<2.10.0` breakage.

---

## Environment Variables (`.env.example`)

```
# Vertex AI (Gemini) — path to GCP service account JSON
GOOGLE_APPLICATION_CREDENTIALS=./video-key.json

# Tavily web search
TAVILY_API_KEY=

# Gmail SMTP
GMAIL_USER=
GMAIL_APP_PASSWORD=

# Optional
GOOGLE_SHEET_URL=
GITHUB_TOKEN=
```

---

## PRD Cleanups (not design changes, text only)

Done in parallel with Phase 0:

- Introduction: "The pipeline runs on a daily GitHub Actions schedule" → "daily APScheduler cron"
- Goals: drop "via GitHub Actions"
- US-019: "GitHub Actions triggers an additional workflow run" → "APScheduler cron (day=1) triggers monthly mode"
- Success Metrics: "Pipeline runs end-to-end in under 5 minutes on GitHub Actions" → "on the scheduler host"

---

## Out of Scope (PRD Non-Goals)

No web dashboard. No streaming / real-time. No per-subscriber personalization in v1. No auth/signup UI. No NLP dedup (URL + title similarity only). No LLM provider other than Gemini. English only. No retries on email failures beyond single attempt. No analysis of AIA internal data.

---

## Convention for Phase Plans

Each `plan-phase-N-*.md` file contains:

1. **Goal** — observable outcome; what "done" looks like
2. **User stories covered**
3. **Files created / modified** — path + one-line purpose
4. **Design decisions** — the non-obvious choices, with rationale
5. **Implementation steps** — ordered, each step 1–2 sentences
6. **Code sketches** — function signatures, prompt templates, data schemas
7. **Verification** — exact commands + expected output
8. **Risks / open items** — unresolved questions or known fragilities
