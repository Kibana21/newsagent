# Phase 5 — Monthly "Best Of" Digest

## Goal

On the 1st of each month at 09:00 Asia/Singapore, send a separate email ranking the **top 10 most important GenAI stories of the past 30 days** for an AIA audience. No new source API calls — sourced entirely from the existing `state/sent_urls.json` log.

Subscribers should want to **forward this monthly email** to colleagues who don't read the daily digest.

## User Stories Covered

- **US-019** — Monthly "Best of the Month" email

## Files Created / Modified

| Path | Change |
|---|---|
| `src/monthly.py` | NEW — builds the monthly digest from `sent_urls.json` |
| `src/main.py` | Branch on `--mode monthly` → call `src.monthly:run()` instead of `build_graph().invoke(...)` |
| `src/prompts.py` | Add `MONTHLY_DIGEST_PROMPT` |
| `src/render.py` | Add `render_monthly(items, week_summary)` helper |
| `scheduler.py` | Monthly cron already added in Phase 4 |

No changes to node files — the daily pipeline already writes all the data the monthly digest needs.

## Design Decisions

1. **No new API calls** — the monthly digest reads `state/sent_urls.json` only. Saves cost, avoids rate limits, and is deterministic (same input → same output).
2. **sent_urls retention already extended** in Phase 3 to 30 days (`save_sent_urls` keeps 30 days, `recent_urls` checks only 7). Phase 5 uses the full 30-day window.
3. **Ranking formula**: `score = buzz_score × insurance_score`. Simple, explainable. Ties broken by `buzz_score` desc, then `sent_at` desc (newer wins).
4. **Top 10** — enough to be meaningful, few enough to read in 2 minutes.
5. **LLM enrichment**: one call that produces (a) a month-opening paragraph (what defined the month for APAC insurers), and (b) a one-sentence rationale per top-10 item. Single call = cheap + consistent.
6. **Subject line format**: `AIA GenAI Intelligence — [Month Year] Top 10` e.g. `AIA GenAI Intelligence — April 2026 Top 10`.
7. **Reuses `src/render.py`, `src/nodes/email_node.py:_strip_raw_index`, and the existing subscriber loader** — no new delivery code.
8. **Distribution list**: same as daily for v1. The PRD Open Question (different monthly list) is deferred — one `subscribers.json` stays simpler.

## Implementation Steps

### 1. `src/prompts.py` additions

```python
MONTHLY_DIGEST_PROMPT = """You are writing the monthly GenAI digest for AIA Singapore (life insurance).

Below are the top 10 GenAI stories from the past 30 days, ranked by cross-source buzz × AIA insurance relevance. Write:
1. An opening paragraph (max 80 words) on the single defining theme for APAC insurers this month.
2. For each of the 10 items, a one-sentence rationale (max 25 words) on why it mattered.

Output STRICT JSON:
{{
  "opening": "...",
  "rationales": [{{"url": "...", "sentence": "..."}}, ...]
}}

Items (with scores):
{items_json}
"""
```

### 2. `src/monthly.py`

```python
from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.llm import get_llm
from src.prompts import MONTHLY_DIGEST_PROMPT
from src.render import render_monthly, markdown_to_email_html
from src.utils.state_io import load_sent_urls
from src.utils.subscribers import load_subscribers


def _top_items(days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
    cutoff = date.today() - timedelta(days=days)
    entries = [
        e for e in load_sent_urls()
        if _parse_date(e.get("sent_at")) and _parse_date(e["sent_at"]) >= cutoff
    ]

    def score(e: dict) -> tuple:
        buzz = int(e.get("buzz_score", 1))
        ins = int(e.get("insurance_score", 1))
        return (buzz * ins, buzz, e.get("sent_at", ""))

    entries.sort(key=score, reverse=True)

    # URL-dedup in case sent multiple days
    seen: set[str] = set()
    top: list[dict] = []
    for e in entries:
        u = e["url"]
        if u in seen:
            continue
        seen.add(u)
        top.append(e)
        if len(top) >= limit:
            break
    return top


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def build_monthly_report() -> str:
    items = _top_items()
    if not items:
        return "# AIA GenAI Intelligence — Monthly Digest\n\nNo items in the past 30 days."

    llm = get_llm(temperature=0.3)
    resp = llm.invoke(MONTHLY_DIGEST_PROMPT.format(items_json=json.dumps(items)))
    text = resp.content if hasattr(resp, "content") else str(resp)
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        llm_data = json.loads(text)
    except json.JSONDecodeError:
        llm_data = {"opening": "", "rationales": []}

    return render_monthly(items, llm_data)


def run() -> dict[str, Any]:
    import os, smtplib
    from email.message import EmailMessage
    from src.config import SMTP_HOST, SMTP_PORT

    report_md = build_monthly_report()
    report_html = markdown_to_email_html(report_md)

    today = date.today()
    month_name = today.strftime("%B %Y")
    subject = f"AIA GenAI Intelligence — {month_name} Top 10"

    # Persist the monthly report for archive
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/{today.isoformat()}_monthly.md").write_text(report_md)

    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    subs = load_subscribers()
    sent, errors = 0, []
    for sub in subs:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = user
            msg["To"] = sub["email"]
            msg["Bcc"] = user
            msg.set_content(report_md)
            msg.add_alternative(report_html, subtype="html")
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
                s.login(user, pw)
                s.send_message(msg)
            sent += 1
        except Exception as e:
            errors.append(f"{sub['email']}: {e}")

    return {"status": "success" if sent else "failed", "subscribers_found": len(subs),
            "emails_sent": sent, "errors": errors}
```

### 3. `src/render.py` addition

```python
def render_monthly(items: list[dict], llm_data: dict) -> str:
    from datetime import date
    month = date.today().strftime("%B %Y")
    lines = [
        f"# AIA GenAI Intelligence — {month} Top 10",
        "",
        "The month's most important GenAI developments for APAC life insurers,",
        "ranked by cross-source buzz × AIA relevance.",
        "",
    ]
    opening = llm_data.get("opening", "").strip()
    if opening:
        lines += ["## This Month's Theme", "", opening, ""]

    rationales = {r["url"]: r["sentence"] for r in llm_data.get("rationales", [])}

    lines += ["## Best of the Month", ""]
    for rank, item in enumerate(items, start=1):
        title = item.get("title", "(no title)")
        url = item["url"]
        rationale = rationales.get(url, "")
        buzz = item.get("buzz_score", 1)
        ins = item.get("insurance_score", 1)
        lines.append(f"**{rank}. [{title}]({url})** — buzz {buzz} · insurance {ins}/3")
        if rationale:
            lines.append(f"   _{rationale}_")
        lines.append("")

    return "\n".join(lines)
```

### 4. `src/main.py` — branch on mode

```python
# Add near the end of main():
if args.mode == "monthly":
    from src.monthly import run
    result = run()
    print(f"Monthly digest: {result}")
    return

# existing daily code follows
```

## Verification

```bash
# Force-trigger the monthly digest (doesn't wait for day=1)
python -m src.main --mode monthly

# Expected:
#  - reports/YYYY-MM-DD_monthly.md written
#  - Email delivered: subject "AIA GenAI Intelligence — April 2026 Top 10"
#  - Body has "This Month's Theme" paragraph + "Best of the Month" with 10 ranked items
#  - Each item shows buzz/insurance scores + one-sentence rationale
#  - NO Tavily / arXiv / GitHub calls made (verify via logs — no `[tavily_node]`, `[arxiv_node]` etc.)

# Scheduler picks it up on day=1
# Wait (or adjust CronTrigger temporarily for testing)
```

### Unit test for monthly

```python
# tests/test_monthly.py
import json
from unittest.mock import MagicMock, patch
from src import monthly

def test_top_items_ranks_by_buzz_times_insurance(tmp_path, monkeypatch):
    # Seed a fake sent_urls.json
    data = [
        {"url": "u1", "title": "T1", "sent_at": "2026-04-20", "buzz_score": 3, "insurance_score": 3},
        {"url": "u2", "title": "T2", "sent_at": "2026-04-19", "buzz_score": 5, "insurance_score": 1},
        {"url": "u3", "title": "T3", "sent_at": "2026-04-18", "buzz_score": 2, "insurance_score": 3},
    ]
    monkeypatch.setattr(monthly, "load_sent_urls", lambda: data)
    top = monthly._top_items(limit=3)
    assert [e["url"] for e in top] == ["u1", "u3", "u2"]  # 9, 6, 5

def test_build_monthly_renders_when_llm_returns_json(monkeypatch):
    fake = MagicMock()
    fake.invoke.return_value.content = json.dumps({
        "opening": "April was dominated by...",
        "rationales": [{"url": "u1", "sentence": "because X"}],
    })
    monkeypatch.setattr("src.monthly.get_llm", lambda temperature=0.3: fake)
    monkeypatch.setattr(monthly, "load_sent_urls", lambda: [
        {"url": "u1", "title": "T1", "sent_at": "2026-04-20", "buzz_score": 3, "insurance_score": 3},
    ])
    report = monthly.build_monthly_report()
    assert "Best of the Month" in report
    assert "because X" in report
```

## Risks / Open Items

- **Cold-start problem**: on the very first 1st of a month after deploying, `sent_urls.json` may have <30 days of history. The digest will still render but with fewer items. Acceptable.
- **LLM JSON parse failure**: if the monthly LLM call returns invalid JSON, the opening paragraph and rationales are blank but the ranked list still renders. Graceful degradation — no retries to keep cost predictable.
- **Duplicate URL handling**: the same story URL could appear on multiple days (buzz score incremented each day). Monthly dedups by URL and takes the first (highest-scoring) occurrence.
- **PRD Open Question #1** (wider monthly distribution list): not resolved in this plan. Current behavior sends to the same daily list. If a separate list is needed later, add a `subscribers_monthly.json` and a lookup flag in `src/utils/subscribers.py`.
- **Retention growth**: `sent_urls.json` at 30-day retention is ~900 entries. Small. If the window ever extends (e.g. quarterly digest), consider a SQLite file instead of JSON.

## Project Complete

After Phase 5 passes verification, the PRD's 19 user stories are all satisfied. The scheduler runs both crons; the test suite is green; daily and monthly emails deliver reliably. Ready for deployment.
