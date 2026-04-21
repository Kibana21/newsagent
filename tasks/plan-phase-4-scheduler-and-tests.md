# Phase 4 — Scheduler & Test Suite

## Goal

- Pipeline runs automatically every day at 08:00 Asia/Singapore with zero manual intervention.
- Scheduler survives pipeline exceptions — one bad day does not break the next.
- `pytest` runs green with ≥80% coverage on `src/nodes/`.
- All external API calls mocked in tests; no network required to run the suite.

## User Stories Covered

- **US-017** — Python scheduler for daily automation
- **US-018** — Unit tests for all nodes

## Files Created

| Path | Purpose |
|---|---|
| `scheduler.py` | Long-running APScheduler process at project root |
| `tests/conftest.py` | Shared pytest fixtures + mocked `ChatVertexAI` |
| `tests/fixtures/tavily_response.json` | Sample Tavily API response |
| `tests/fixtures/rss_openai.xml` | Sample RSS XML |
| `tests/fixtures/arxiv_atom.xml` | Sample arXiv Atom response |
| `tests/fixtures/hn_topstories.json` + `hn_item_*.json` | Sample HN API responses |
| `tests/fixtures/hf_models.json` | Sample HuggingFace response |
| `tests/fixtures/github_repos.json` | Sample GitHub Search response |
| `tests/fixtures/reddit_top.json` | Sample Reddit top.json |
| `tests/fixtures/curate_output.json` | Sample well-formed curate LLM JSON |
| `tests/test_tavily_node.py` | Happy, empty, error paths |
| `tests/test_rss_node.py` | Same |
| `tests/test_arxiv_node.py` | Same + lag-buffer behavior |
| `tests/test_github_node.py` | Same + token handling |
| `tests/test_hf_node.py` | Same |
| `tests/test_hn_node.py` | Same + keyword filter |
| `tests/test_reddit_node.py` | Same |
| `tests/test_youtube_node.py` | Same |
| `tests/test_aggregate_node.py` | Dedup, buzz scoring, sent-URL filter |
| `tests/test_curate_node.py` | Insurance scoring, flagging, JSON retry |
| `tests/test_summarize_node.py` | Layout rendering, Friday logic, empty sections |
| `tests/test_email_node.py` | Subscriber loading, sent_urls write, partial-send resilience |
| `tests/test_state_io.py` | sent_urls load / prune / save |
| `tests/test_utils_text.py` | `strip_html`, `title_similarity` |
| `tests/test_utils_dates.py` | `freshness_tag` at various ages |

## Design Decisions

1. **`BlockingScheduler`, not `BackgroundScheduler`** — scheduler IS the process. No need for a separate supervisor thread. Simpler and more robust.
2. **Single try/except at the job boundary** — the scheduler wraps `run_pipeline()` in `try/except Exception`. One-day failures are logged, never crash the scheduler.
3. **Logging goes to stdout** — the scheduler is run under systemd / nohup / a tmux session; stdout capture is enough. No rotating file logs.
4. **Tests mock at the boundary**: mock `requests.get`, `feedparser.parse`, `TavilySearch`, `ChatVertexAI.invoke`, `smtplib.SMTP_SSL`. Do not mock internal functions.
5. **Shared `mock_llm` fixture** in `conftest.py` returns a function that records calls and yields pre-canned responses per prompt pattern. Used by `test_curate_node` and `test_summarize_node`.
6. **Coverage target is ≥80% on `src/nodes/`**, not on the whole project. Utility modules are incidentally covered; config and state don't need tests.
7. **No integration tests in this phase** — the Phase 3 end-to-end verification (run pipeline, check inbox) is the integration test. Pytest stays unit-level.

## Implementation Steps

### 1. `scheduler.py`

```python
from __future__ import annotations
import logging
import subprocess
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("newsagent")


def run_daily() -> None:
    log.info("Starting daily pipeline")
    try:
        subprocess.run([sys.executable, "-m", "src.main", "--days", "2", "--mode", "daily"],
                       check=True)
        log.info("Daily pipeline completed")
    except subprocess.CalledProcessError as e:
        log.exception("Daily pipeline failed: %s", e)
    except Exception:
        log.exception("Unexpected error during daily run")


def run_monthly() -> None:
    log.info("Starting monthly pipeline")
    try:
        subprocess.run([sys.executable, "-m", "src.main", "--mode", "monthly"], check=True)
        log.info("Monthly pipeline completed")
    except Exception:
        log.exception("Monthly pipeline failed")


def main() -> None:
    sched = BlockingScheduler(timezone="Asia/Singapore")
    sched.add_job(run_daily, CronTrigger(hour=8, minute=0), id="daily", name="Daily digest")
    sched.add_job(run_monthly, CronTrigger(day=1, hour=9, minute=0),
                  id="monthly", name="Monthly digest")

    for job in sched.get_jobs():
        log.info("Scheduled %s (next run: %s)", job.name, job.next_run_time)

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down scheduler")


if __name__ == "__main__":
    main()
```

**Why `subprocess.run` instead of calling `src.main:main()` directly**: isolates memory/state per run. If the LLM client holds onto GC-heavy objects, they're released between days. Also if the pipeline ever `sys.exit`s, the scheduler isn't killed.

### 2. `tests/conftest.py`

```python
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture
def sample_state():
    return {
        "search_query": "latest GenAI",
        "days": 2,
        "tavily_news": [], "rss_news": [], "arxiv_news": [], "github_news": [],
        "hf_news": [], "hn_news": [], "reddit_news": [], "youtube_news": [],
    }


@pytest.fixture
def sample_news_item():
    return {
        "title": "OpenAI Announces GPT-5",
        "url": "https://openai.com/blog/gpt-5",
        "summary": "Big release.",
        "source": "rss",
        "published_at": "2026-04-20T10:00:00+00:00",
    }


@pytest.fixture
def mock_llm(monkeypatch):
    """Replace src.llm.get_llm with a mock that returns pre-canned responses
    based on a simple prompt-pattern dispatch."""
    responses = {
        "curate": json.dumps({
            "business": [{"title": "AIA ...", "url": "https://x/1", "summary": "...",
                          "source": "tavily", "published_at": "", "insurance_score": 3,
                          "competitor": False, "regulatory": False}],
            "technical": [],
            "research": [],
            "insurtech": [],
        }),
        "tldr": json.dumps([{"bullet": "b1", "url": "https://x/1"}] * 3),
        "boardroom": json.dumps([{"url": "https://x/1", "sentence": "boardroom note"}]),
        "build": json.dumps([]),
        "paper": json.dumps({"url": "https://x/1", "title": "T", "explainer": "..."}),
    }

    def _invoke(prompt: str):
        key = (
            "curate" if "curate" in prompt.lower() else
            "tldr" if "tl;dr" in prompt.lower() or "must-read" in prompt.lower() else
            "boardroom" if "boardroom" in prompt.lower() else
            "build" if "build this at aia" in prompt.lower() else
            "paper" if "paper" in prompt.lower() else
            "{}"
        )
        m = MagicMock()
        m.content = responses.get(key, "{}")
        return m

    fake = MagicMock()
    fake.invoke.side_effect = _invoke

    monkeypatch.setattr("src.llm.get_llm", lambda temperature=0.2: fake)
    return fake
```

### 3. Representative test: `tests/test_aggregate_node.py`

```python
from unittest.mock import patch
from src.nodes.aggregate_node import aggregate_node

def test_dedup_by_url():
    state = {
        "tavily_news": [{"title": "A", "url": "https://x/1"}],
        "rss_news": [{"title": "A dup", "url": "https://x/1/"}],  # same URL
    }
    with patch("src.nodes.aggregate_node.recent_urls", return_value=set()):
        out = aggregate_node(state)
    assert len(out["raw_news"]) == 1

def test_sent_urls_filter_removes_recent():
    state = {"tavily_news": [{"title": "A", "url": "https://x/1"}]}
    with patch("src.nodes.aggregate_node.recent_urls", return_value={"https://x/1"}):
        out = aggregate_node(state)
    assert out["raw_news"] == []

def test_buzz_scoring_near_duplicates():
    state = {
        "tavily_news": [{"title": "OpenAI announces GPT-5", "url": "https://a/1"}],
        "rss_news":    [{"title": "OpenAI announces GPT 5!", "url": "https://b/2"}],
        "hn_news":     [{"title": "OpenAI Announces GPT-5 model", "url": "https://c/3"}],
    }
    with patch("src.nodes.aggregate_node.recent_urls", return_value=set()):
        out = aggregate_node(state)
    # All three URLs should have buzz >= 2 (near-duplicate titles)
    assert max(out["buzz_scores"].values()) >= 2
```

### 4. Representative test: `tests/test_curate_node.py`

```python
import json
from unittest.mock import MagicMock, patch
from src.nodes.curate_node import curate_node

def test_retries_on_bad_json():
    # First response invalid, second valid
    bad = MagicMock(); bad.content = "not json"
    good = MagicMock(); good.content = json.dumps({
        "business": [], "technical": [], "research": [], "insurtech": []
    })
    fake = MagicMock()
    fake.invoke.side_effect = [bad, good]
    with patch("src.nodes.curate_node.get_llm", return_value=fake):
        out = curate_node({"raw_news": [{"title": "t", "url": "u"}], "buzz_scores": {}})
    assert fake.invoke.call_count == 2
    assert "business" in out["categorized_news"]

def test_raises_after_three_bad_attempts():
    bad = MagicMock(); bad.content = "still not json"
    fake = MagicMock()
    fake.invoke.return_value = bad
    with patch("src.nodes.curate_node.get_llm", return_value=fake):
        import pytest
        with pytest.raises(ValueError):
            curate_node({"raw_news": [{"title": "t", "url": "u"}], "buzz_scores": {}})
```

### 5. Representative test: `tests/test_rss_node.py`

```python
from unittest.mock import patch, MagicMock
from src.nodes.rss_node import rss_node

def _fake_feed(entries):
    feed = MagicMock()
    feed.entries = entries
    return feed

def test_happy_path():
    entry = {"title": "t", "link": "https://x/1", "summary": "s",
             "published_parsed": (2026, 4, 21, 10, 0, 0, 0, 111, 0)}
    with patch("src.nodes.rss_node.feedparser.parse", return_value=_fake_feed([entry])):
        out = rss_node({"days": 7})
    assert len(out["rss_news"]) >= 1
    assert out["rss_news"][0]["source"] == "rss"

def test_empty_feed():
    with patch("src.nodes.rss_node.feedparser.parse", return_value=_fake_feed([])):
        out = rss_node({"days": 2})
    assert out["rss_news"] == []

def test_exception_returns_empty():
    with patch("src.nodes.rss_node.feedparser.parse", side_effect=Exception("boom")):
        out = rss_node({"days": 2})
    assert out["rss_news"] == []
```

## Verification

```bash
# Run full suite
pytest --cov=src/nodes --cov-report=term-missing

# Expected:
#   tests/ ... all passing
#   Coverage on src/nodes: >=80%

# Start scheduler (manual verification)
python scheduler.py
# Expected log lines:
#   [INFO] Scheduled Daily digest (next run: 2026-04-22 08:00:00+08:00)
#   [INFO] Scheduled Monthly digest (next run: 2026-05-01 09:00:00+08:00)

# Test exception resilience: temporarily break a node (e.g. set a bogus env var),
# trigger a manual run via the APScheduler job, confirm:
#   - Traceback is logged
#   - Scheduler does NOT crash
#   - Next scheduled run time is still shown

# Verify timezone is correct
python -c "from pytz import timezone; from datetime import datetime; print(datetime.now(timezone('Asia/Singapore')))"
```

## Risks / Open Items

- **APScheduler catches crashes silently if a job exits `0`**: the `subprocess.run(check=True)` pattern surfaces nonzero exits. Verify on a deliberately failing run.
- **`pytz` vs `zoneinfo`**: Python 3.12 has `zoneinfo` stdlib. APScheduler 3.10 still accepts string tz (`"Asia/Singapore"`) and converts internally. No import needed.
- **Running under `nohup`**: output buffering. Add `-u` flag or set `PYTHONUNBUFFERED=1` so logs stream.
- **Test parallelism**: each test mocks its own boundaries; no shared state. Safe to run `pytest -n auto` if pytest-xdist is added later.
- **Fixture drift**: API response formats change. If a test suddenly fails after a dependency bump, regenerate the fixture from a live run.

## Next Phase

Phase 5 adds the monthly "Best Of" digest. See [plan-phase-5-monthly-digest.md](./plan-phase-5-monthly-digest.md).
