# Claude Guide — Gen AI News Agent (AIA Singapore)

Project-specific instructions for Claude. Read this first on every session.

---

## What this project is

An automated daily email digest that curates GenAI news from 8 sources into **four** audience sections — Business & Strategy, Tech & Engineering, Research Frontiers, **InsurTech & AIA Relevance** — tailored for business and technical readers at **AIA Singapore** (a life-insurance company). Runs as a long-lived Python process via APScheduler.

---

## Current status

- ✅ PRD written: [`tasks/prd-gen-ai-news-agent.md`](tasks/prd-gen-ai-news-agent.md)
- ✅ Master plan + 6 phase plans written in `tasks/`
- ⏸️ **No source code yet** — implementation is gated on user review of the phase plans
- 📌 Python 3.12 `.venv` is already created at project root
- 📌 `video-key.json` (GCP service account) is in place, gitignored

**Before writing any code**, confirm the user has reviewed the plans in `tasks/plan-*.md` and explicitly approved starting Phase 0.

---

## Project documents (read these on session start)

| File | Purpose |
|---|---|
| `tasks/prd-gen-ai-news-agent.md` | **Product requirements** — 19 user stories (US-001 to US-019), functional requirements, success metrics |
| `tasks/plan-master.md` | Plan overview, locked decisions, dependency graph |
| `tasks/plan-phase-0-scaffold.md` | Deps, TypedDicts, constants |
| `tasks/plan-phase-1-walking-skeleton.md` | End-to-end skeleton (1 email, 2 sources) |
| `tasks/plan-phase-2-ingestion-sources.md` | 7 remaining source nodes with API contracts |
| `tasks/plan-phase-3-insurance-intelligence.md` | Buzz scoring, 4-category curation, full email layout |
| `tasks/plan-phase-4-scheduler-and-tests.md` | APScheduler + pytest suite ≥80% coverage |
| `tasks/plan-phase-5-monthly-digest.md` | "Best of Month" digest |

**All planning documents live in `tasks/`** — not in `.claude/plans/`. Planning artifacts travel with the git repo alongside the PRD.

---

## Locked decisions (do not revisit without explicit user ask)

1. **LLM auth = Vertex AI** via `langchain-google-vertexai` + `ChatVertexAI`, using `video-key.json` service account. **Do NOT use** `langchain-google-genai` + `GOOGLE_API_KEY` — that library does not accept service-account credentials.
2. **Scheduler = APScheduler `BlockingScheduler`** running as a long-lived Python process (`python scheduler.py`). **No GitHub Actions**, no cloud infra, no Docker.
3. **State = plain JSON** files in `state/` (`sent_urls.json`, daily state dumps). No database.
4. **Build order = walking skeleton first** (Phase 1), then layer on sources (Phase 2), insurance intelligence (Phase 3), scheduler + tests (Phase 4), monthly digest (Phase 5).
5. **Planning documents always go in `tasks/`**, not `.claude/plans/`.

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 |
| Orchestration | LangGraph (parallel fan-out → sequential tail) |
| LLM | Gemini 2.5 Flash via `langchain-google-vertexai` + `ChatVertexAI` |
| Auth | GCP service account JSON (`video-key.json`) via `google-auth` |
| Scheduling | APScheduler `BlockingScheduler`, `Asia/Singapore` timezone |
| Web search | Tavily via `langchain-tavily` |
| RSS | `feedparser` |
| HTTP | `requests` |
| Email | `smtplib` + `email` stdlib (SMTP-SSL to Gmail port 465) |
| Markdown → HTML | `markdown` package, inline CSS post-processing for Gmail |
| Testing | `pytest`, `unittest.mock` |
| Deps | `requirements.txt` with pinned versions; `pyproject.toml` for tool config |

Full pinning is in `tasks/plan-master.md` § Dependency Pinning.

---

## Planned directory structure

```
newsagent/
├── .env.example, .gitignore, README.md, requirements.txt, pyproject.toml
├── video-key.json           # GCP service account, gitignored
├── subscribers.json         # Fallback subscriber list
├── scheduler.py             # Long-running APScheduler (Phase 4)
├── src/
│   ├── state.py             # AgentState + NewsItem TypedDicts
│   ├── config.py            # RSS_FEEDS, INSURANCE_KEYWORDS, COMPETITOR_INSURERS, etc.
│   ├── llm.py               # Vertex AI factory; only place touching video-key.json
│   ├── prompts.py           # All LLM prompt templates
│   ├── render.py            # Markdown → inline-CSS HTML, Source Health table
│   ├── monthly.py           # Monthly digest (Phase 5)
│   ├── graph.py             # build_graph() — LangGraph wiring
│   ├── main.py              # CLI entrypoint
│   ├── nodes/               # One file per node (8 source nodes + 4 pipeline nodes)
│   └── utils/               # dates.py, text.py, state_io.py, subscribers.py
├── tests/                   # One test file per node
├── reports/                 # Runtime output (gitignored)
└── state/                   # sent_urls.json + daily JSON dumps (gitignored)
```

---

## Commands (once implemented)

```bash
# Setup (once)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in TAVILY_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD

# Manual run (daily mode)
python -m src.main --days 2

# Manual run (monthly mode)
python -m src.main --mode monthly

# Start the scheduler (daily 08:00 Asia/Singapore + monthly day=1 09:00)
python scheduler.py

# Test suite
pytest --cov=src/nodes --cov-report=term-missing

# Type check
mypy src/
```

---

## Required environment variables

| Var | Purpose |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to `video-key.json` |
| `TAVILY_API_KEY` | Tavily web search |
| `GMAIL_USER` | Sender Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not account password) |
| `GOOGLE_SHEET_URL` (optional) | CSV export URL for subscribers |
| `GITHUB_TOKEN` (optional) | Raises GitHub Search API rate limit |

---

## Audience model — critical context

Every email must be valuable to **both** audiences at AIA Singapore:

- **Business readers**: insurance leaders + strategy teams. Need "so what" implications, competitor moves (Prudential, Great Eastern, Manulife, FWD, Allianz, AXA), MAS/IMDA regulatory signals. Each Business item gets a **"Boardroom angle"** sentence.
- **Tech readers**: engineers + data scientists. Need models, tools, papers — with insurance-applicable framing. Each Tech item gets a **"Build this at AIA"** sentence mapping to underwriting / claims / fraud detection / customer service.

The **InsurTech & AIA Relevance** section aggregates insurance-tagged items from all other sections plus dedicated insurance news.

LLM assigns `insurance_score` (1–3) and `competitor` / `regulatory` booleans to every curated item. These flags drive email formatting and monthly digest ranking.

---

## Working conventions

- **Defer to the plans.** When implementing, follow the phase plan for the current phase; deviate only with the user's explicit OK.
- **Nodes never raise.** Every source node returns `[]` on failure so one broken source never kills the pipeline.
- **Constants live in `src/config.py`.** RSS feeds, YouTube channels, insurance keywords, competitor names — single source of truth.
- **Prompts live in `src/prompts.py`.** Single source of truth for LLM templates; tuneable without touching logic.
- **`src/llm.py` is the only place that touches `video-key.json`.** All other modules get a `ChatVertexAI` via `get_llm()`.
- **State schema uses `TypedDict(total=False)`.** LangGraph merges partial dicts; nodes return only what they contribute.
- **No repeats within 7 days.** `state/sent_urls.json` rolling log, enforced in `aggregate_node`.

---

## Don't do (common mistakes)

- ❌ Don't use `langchain-google-genai` + `GOOGLE_API_KEY`. Use Vertex AI — see `src/llm.py` plan.
- ❌ Don't add GitHub Actions, Dockerfiles, or cloud deployment. The user chose APScheduler specifically to avoid that.
- ❌ Don't commit `video-key.json` or `.env`. Both are in `.gitignore`.
- ❌ Don't write code before all phase plans are user-approved.
- ❌ Don't put planning documents in `.claude/plans/`. They go in `tasks/`.
- ❌ Don't assume Pydantic ≥ 2.10 — it breaks LangChain's dep tree. See the explicit pin in `requirements.txt`.
- ❌ Don't add web UI, streaming, or subscriber auth. These are explicit Non-Goals in the PRD.

---

## Memory for this project

User memory lives at `~/.claude/projects/-Users-kartik-Documents-Work-Projects-newsagent/memory/`:

- `user_role.md` — works at AIA Singapore (life insurance)
- `feedback_planning_artifacts.md` — plans belong in `tasks/`, not `.claude/plans/`

If user preferences or constraints emerge that apply to future sessions, save them to memory following the auto-memory rules in the system prompt.

---

## Quick orientation for a new session

1. Read this file.
2. Scan `tasks/plan-master.md` for current phase and locked decisions.
3. Check `git log --oneline -20` to see recent progress.
4. Check `ls src/` to see which phase has been implemented.
5. Ask the user what they want to work on, or pick up the next pending phase per `tasks/plan-master.md`.
