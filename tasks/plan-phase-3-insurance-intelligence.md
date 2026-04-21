# Phase 3 — Insurance Intelligence Layer

## Goal

Transform the skeleton digest into a newsletter that is **materially more valuable for AIA Singapore readers than a generic GenAI digest**. Every email now has:

- A **TL;DR** (3 bullets, the day's must-reads)
- **Four** persona sections (Business, Tech, Research, InsurTech & AIA Relevance)
- **Per-item enrichment**: "Boardroom angle" for Business, "Build this at AIA" for Tech, "Paper of the Day" for Research
- **Buzz badges** for cross-source stories, **freshness tags** for every item
- A **Source Health footer** showing which sources ran
- A **Friday Week-in-Review** paragraph
- **No repeats within 7 days** (tracked via `state/sent_urls.json`)
- **Competitor / regulatory flags** on relevant items

## User Stories Covered (Full)

- **US-011** — full aggregation with buzz scoring + sent-URL filter
- **US-012** — full curation with 4 categories + scoring + flags
- **US-013** — full summarize layout
- **US-014** — full email with HTML+CSS, subscriber loading, sent_urls write

## Files Created / Modified

| Path | Change |
|---|---|
| `src/prompts.py` | Upgrade `CURATE_PROMPT` + add `TLDR_PROMPT`, `BOARDROOM_PROMPT`, `BUILD_AT_AIA_PROMPT`, `PAPER_EXPLAINER_PROMPT`, `WEEK_IN_REVIEW_PROMPT` |
| `src/utils/text.py` | NEW — `strip_html(s)`, `title_similarity(a, b)` |
| `src/utils/dates.py` | NEW — `freshness_tag(iso)` → `"[2h ago]"` etc. |
| `src/utils/state_io.py` | NEW — `load_sent_urls()`, `save_sent_urls(new_urls, metadata)`, `prune_sent_urls(days=7)` |
| `src/utils/subscribers.py` | NEW — `load_subscribers()` with Google Sheets + `subscribers.json` fallback |
| `src/render.py` | NEW — Markdown → inline-CSS HTML; Source Health table; layout helpers |
| `src/nodes/aggregate_node.py` | Add buzz scoring + sent-URL filter |
| `src/nodes/curate_node.py` | 4 categories + `insurance_score` + `competitor` + `regulatory` + JSON retry |
| `src/nodes/summarize_node.py` | Full layout with LLM enrichment passes |
| `src/nodes/email_node.py` | Subscriber loading, HTML conversion, sent_urls write |

## Design Decisions

1. **Buzz scoring happens in `aggregate_node`, before curation** — the LLM sees `buzz_scores` and uses it to pick TL;DR items. Computing buzz after the LLM would be circular (it may drop duplicates).
2. **Title similarity via `difflib.SequenceMatcher` ≥ 0.9** — stdlib-only, no new dependency. Good enough for near-duplicate detection without embedding models.
3. **`insurance_score` assigned by LLM**, not keyword matching — LLM-judged relevance is more accurate for nuanced cases ("a claims automation case study at Allianz" scores high, "a chatbot paper mentioning life insurance" scores low).
4. **`sent_urls.json` schema extended now**, not in Phase 5 — each entry stores `{url, sent_at, buzz_score, insurance_score, title}` so the monthly digest (Phase 5) can rank without a re-scoring pass.
5. **Enrichment sentences generated in a single batched LLM call** per section — one call per section, not one per item. 4 sections × ~5 items = 1 call returns 5 enrichment sentences. Cheaper + more consistent tone.
6. **Email HTML uses inline CSS** — Gmail strips `<style>` blocks; only inline `style="..."` attributes reliably render. Use `markdown` library + a post-processing pass that injects inline styles on common tags.
7. **Friday logic is date-based** — `date.today().weekday() == 4` (Friday). No config, no user toggle.
8. **Raw Intelligence Index** (the `<details>` collapsible) remains in the Markdown file for archive, but stripped from the email — email clients render `<details>` inconsistently.
9. **Sent URLs pruned to 7 days** on every write. Monthly digest (Phase 5) will extend this retention to 30 days (or read `state/YYYY-MM-DD_state.json` archives instead).

## Implementation Steps

### 1. `src/utils/text.py`

```python
from __future__ import annotations
import re
from difflib import SequenceMatcher

_TAG_RE = re.compile(r"<[^>]+>")

def strip_html(s: str) -> str:
    return _TAG_RE.sub("", s or "").strip()

def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()
```

### 2. `src/utils/dates.py`

```python
from __future__ import annotations
from datetime import datetime, timezone

def freshness_tag(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    delta = datetime.now(timezone.utc) - dt
    hours = int(delta.total_seconds() // 3600)
    if hours < 1:
        return "[<1h ago]"
    if hours < 24:
        return f"[{hours}h ago]"
    days = hours // 24
    return f"[{days}d ago]"
```

### 3. `src/utils/state_io.py`

```python
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

PATH = Path("state/sent_urls.json")

def load_sent_urls() -> list[dict[str, Any]]:
    if not PATH.exists():
        return []
    try:
        return json.loads(PATH.read_text())
    except Exception:
        return []

def prune_sent_urls(entries: list[dict], days: int = 7) -> list[dict]:
    cutoff = date.today() - timedelta(days=days)
    kept = []
    for e in entries:
        try:
            sent = date.fromisoformat(e["sent_at"])
        except Exception:
            continue
        if sent >= cutoff:
            kept.append(e)
    return kept

def save_sent_urls(entries: list[dict]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    pruned = prune_sent_urls(entries, days=30)  # retain 30 days for monthly digest
    PATH.write_text(json.dumps(pruned, indent=2))

def recent_urls(days: int = 7) -> set[str]:
    cutoff = date.today() - timedelta(days=days)
    seen: set[str] = set()
    for e in load_sent_urls():
        try:
            if date.fromisoformat(e["sent_at"]) >= cutoff:
                seen.add(e["url"].rstrip("/").lower())
        except Exception:
            continue
    return seen
```

### 4. `src/nodes/aggregate_node.py` (full)

```python
from __future__ import annotations
from src.state import AgentState
from src.utils.text import title_similarity
from src.utils.state_io import recent_urls

def aggregate_node(state: AgentState) -> dict:
    raw: list[dict] = []
    per_source: dict[str, int] = {}
    for field in ("tavily_news", "rss_news", "arxiv_news", "github_news",
                  "hf_news", "hn_news", "reddit_news", "youtube_news"):
        items = state.get(field, [])
        per_source[field.replace("_news", "")] = len(items)
        raw.extend(items)

    # URL-based dedup (case-insensitive, strip trailing slash)
    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for item in raw:
        u = (item.get("url") or "").strip().rstrip("/").lower()
        if not u or u in seen_urls:
            continue
        seen_urls.add(u)
        deduped.append(item)

    # Filter against sent_urls (rolling 7-day window)
    recent = recent_urls(days=7)
    filtered = [i for i in deduped if (i.get("url") or "").strip().rstrip("/").lower() not in recent]

    # Buzz scoring: count near-duplicate titles across the DEDUPED list
    buzz: dict[str, int] = {}
    for i, item in enumerate(filtered):
        count = 1
        for j, other in enumerate(filtered):
            if i == j:
                continue
            if title_similarity(item.get("title", ""), other.get("title", "")) >= 0.9:
                count += 1
        buzz[item.get("url", "")] = count
        item["buzz_score"] = count

    print(f"[aggregate] per_source={per_source} raw={len(raw)} deduped={len(deduped)} after_sent_filter={len(filtered)}")
    return {"raw_news": filtered, "buzz_scores": buzz}
```

### 5. `src/prompts.py` (full)

```python
CURATE_PROMPT = """You are an intelligence analyst curating GenAI news for AIA Singapore, a major APAC life insurance company.

You receive a JSON list of raw news items. For each item decide:
1. Is it on-topic and recent (last 7 days)? If not, drop it.
2. Which category does it fit best:
   - "business": corporate moves, funding, product launches, enterprise adoption
   - "technical": models, tools, open-source, engineering
   - "research": academic papers, benchmarks, algorithmic breakthroughs
   - "insurtech": insurance-specific AI, MAS/IMDA/regulatory, competitor insurer news
3. Assign `insurance_score` (1=low, 2=medium, 3=high) for relevance to a life insurer in APAC.
   - 3 = directly applicable: claims automation, underwriting AI, competitor insurer announcements, MAS/IMDA AI guidance
   - 2 = adjacent: enterprise GenAI platforms, compliance AI, customer-service AI in finserv
   - 1 = general GenAI news without insurance angle
4. Set `competitor=true` if the item mentions any of: {competitors}
5. Set `regulatory=true` if it mentions any of: {regulators}, or APAC financial regulation

Output STRICT JSON ONLY, no prose, no code fences:
{{
  "business": [{{"title": ..., "url": ..., "summary": ..., "source": ..., "published_at": ..., "insurance_score": N, "competitor": bool, "regulatory": bool}}],
  "technical": [...],
  "research": [...],
  "insurtech": [...]
}}

Input items (with buzz_scores showing cross-source appearances):
{items_json}

Buzz scores (url -> count):
{buzz_json}
"""

TLDR_PROMPT = """Pick the top 3 must-read items for an AIA Singapore audience (mix of business and tech leaders). Prefer items with high insurance_score, high buzz_score, or competitor/regulatory flags.

Return a JSON list of 3 single-sentence bullets, each referencing one item by its URL:
[{{"bullet": "...", "url": "..."}}, ...]

Items: {items_json}
"""

BOARDROOM_PROMPT = """For each business item below, write ONE sentence (max 30 words) framed as a boardroom takeaway for a life-insurance executive. Focus on strategic implication, not description.

Return JSON: [{{"url": "...", "sentence": "..."}}, ...]

Items: {items_json}
"""

BUILD_AT_AIA_PROMPT = """For each technical item below, write ONE sentence (max 30 words) mapping the technology to a concrete AIA use case. Domains: underwriting, claims automation, fraud detection, customer service, agent assist. Be specific.

Return JSON: [{{"url": "...", "sentence": "..."}}, ...]

Items: {items_json}
"""

PAPER_EXPLAINER_PROMPT = """Pick the single most important research paper below. Write a 4-sentence plain-English explainer for a non-academic technical audience. Avoid jargon. Explain: what problem, what approach, what result, why it matters.

Return JSON: {{"url": "...", "title": "...", "explainer": "..."}}

Papers: {items_json}
"""

WEEK_IN_REVIEW_PROMPT = """In one paragraph (max 100 words), summarize the single most important GenAI development this week for an APAC life insurer. Highlight the "so what" — what should AIA leadership notice, monitor, or act on?

This week's curated items: {items_json}
"""
```

### 6. `src/nodes/curate_node.py` (full with retry)

```python
from __future__ import annotations
import json
from src.config import COMPETITOR_INSURERS, REGULATORS
from src.llm import get_llm
from src.prompts import CURATE_PROMPT
from src.state import AgentState


def _parse_json(text: str) -> dict | None:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def curate_node(state: AgentState) -> dict:
    raw = state.get("raw_news", [])
    buzz = state.get("buzz_scores", {})
    if not raw:
        empty = {"business": [], "technical": [], "research": [], "insurtech": []}
        return {"curated_news": [], "categorized_news": empty}

    llm = get_llm(temperature=0.1)
    prompt = CURATE_PROMPT.format(
        competitors=", ".join(COMPETITOR_INSURERS),
        regulators=", ".join(REGULATORS),
        items_json=json.dumps(raw)[:20000],
        buzz_json=json.dumps(buzz),
    )

    data = None
    for attempt in range(3):
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        data = _parse_json(text)
        if data and all(k in data for k in ("business", "technical", "research", "insurtech")):
            break
        print(f"[curate] parse failed on attempt {attempt + 1}")

    if data is None:
        raise ValueError("curate_node: LLM did not return valid JSON after 3 attempts")

    categorized = {k: data.get(k, []) for k in ("business", "technical", "research", "insurtech")}
    flat = sum(categorized.values(), [])
    return {"curated_news": flat, "categorized_news": categorized}
```

### 7. `src/nodes/summarize_node.py` (full layout)

Structure:

```
┌ HEADER ──────────────────────────────────────────┐
│ AIA GenAI Intelligence — YYYY-MM-DD              │
│ [Week in Review paragraph, Fridays only]         │
│                                                  │
│ ## TL;DR                                         │
│ - bullet 1 (url)                                 │
│ - bullet 2 (url)                                 │
│ - bullet 3 (url)                                 │
├──────────────────────────────────────────────────┤
│ ## 🏢 Business & Strategy (N)                    │
│ - **[Title](url)** [Trending across N sources]   │
│   [2h ago]                                       │
│   Summary text.                                  │
│   *Boardroom angle:* one sentence.              │
├──────────────────────────────────────────────────┤
│ ## 🛠️ Tech & Engineering (N)                     │
│ - **[Title](url)** ...                          │
│   *Build this at AIA:* one sentence.            │
├──────────────────────────────────────────────────┤
│ ## 🔬 Research Frontiers (N)                     │
│ ┌ Paper of the Day ────────────────────────┐    │
│ │ Title — link                             │    │
│ │ 4-sentence plain-English explainer       │    │
│ └──────────────────────────────────────────┘    │
│ - other papers                                   │
├──────────────────────────────────────────────────┤
│ ## 🛡️ InsurTech & AIA Relevance (N)              │
│ - 🏢 competitor tag or ⚖️ regulatory tag          │
├──────────────────────────────────────────────────┤
│ ── Source Health ──                              │
│ tavily: 8 ✅   rss: 5 ✅   arxiv: 3 ✅           │
│ github: 3 ✅  hf: 0 ❌    hn: 5 ✅                │
│ reddit: 10 ✅ youtube: 0 ❌                       │
├──────────────────────────────────────────────────┤
│ <details> Raw Intelligence Index (stripped from  │
│  email before send)                              │
└──────────────────────────────────────────────────┘
```

Implementation sketch:

```python
from datetime import date
from src.llm import get_llm
from src.prompts import (
    TLDR_PROMPT, BOARDROOM_PROMPT, BUILD_AT_AIA_PROMPT,
    PAPER_EXPLAINER_PROMPT, WEEK_IN_REVIEW_PROMPT,
)
from src.utils.dates import freshness_tag

def summarize_node(state):
    cat = state.get("categorized_news", {})
    buzz = state.get("buzz_scores", {})
    llm = get_llm(temperature=0.2)

    tldr = _call_json(llm, TLDR_PROMPT, {"items_json": json.dumps(_flatten(cat))[:8000]})
    boardroom = _call_json(llm, BOARDROOM_PROMPT, {"items_json": json.dumps(cat.get("business", []))[:6000]})
    build_at_aia = _call_json(llm, BUILD_AT_AIA_PROMPT, {"items_json": json.dumps(cat.get("technical", []))[:6000]})
    paper = _call_json(llm, PAPER_EXPLAINER_PROMPT, {"items_json": json.dumps(cat.get("research", []))[:6000]}) if cat.get("research") else None

    week_review = ""
    if date.today().weekday() == 4:  # Friday
        week_review = llm.invoke(WEEK_IN_REVIEW_PROMPT.format(items_json=json.dumps(_flatten(cat))[:8000])).content

    report_md = _render_markdown(cat, buzz, tldr, boardroom, build_at_aia, paper, week_review, state)
    return {"final_report": report_md}
```

Details of `_render_markdown`:
- Sections only rendered if non-empty; headers show `(N)` count
- Each item shows: bold link title, freshness tag, summary, enrichment sentence, inline "Trending across N sources" badge if `buzz_scores[url] >= 3`
- InsurTech section prepends 🏢 to competitor items, ⚖️ to regulatory items
- InsurTech section includes items from other sections with `insurance_score == 3`
- Source Health table: read counts from `state["tavily_news"]` etc.

### 8. `src/render.py` — Markdown → inline-CSS HTML

```python
import markdown as md

INLINE_STYLES = {
    "h1": "font-family:Arial,sans-serif;font-size:20px;margin:16px 0 8px;",
    "h2": "font-family:Arial,sans-serif;font-size:18px;margin:16px 0 8px;border-bottom:1px solid #eee;padding-bottom:4px;",
    "h3": "font-family:Arial,sans-serif;font-size:16px;margin:12px 0 6px;",
    "p":  "font-family:Arial,sans-serif;font-size:14px;line-height:1.55;margin:6px 0;",
    "ul": "margin:8px 0 12px 20px;",
    "li": "font-family:Arial,sans-serif;font-size:14px;line-height:1.55;margin-bottom:6px;",
    "a":  "color:#1a73e8;text-decoration:none;",
    "em": "color:#555;",
}

def markdown_to_email_html(md_text: str) -> str:
    html = md.markdown(md_text, extensions=["extra", "sane_lists"])
    for tag, style in INLINE_STYLES.items():
        html = html.replace(f"<{tag}>", f'<{tag} style="{style}">')
    return f'<div style="max-width:720px;margin:0 auto;padding:24px;">{html}</div>'
```

### 9. `src/utils/subscribers.py`

```python
import csv
import io
import json
import os
import re
from pathlib import Path
import requests

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _valid(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))

def _from_sheet(url: str) -> list[dict]:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        email_col = next((c for c in reader.fieldnames if "email" in c.lower()), None)
        if not email_col:
            return []
        return [{"email": row[email_col].strip(), "name": row.get("name", ""), "persona": "all"}
                for row in reader if _valid(row.get(email_col, ""))]
    except Exception as e:
        print(f"[subscribers] sheet fetch failed: {e}")
        return []

def _from_file() -> list[dict]:
    p = Path("subscribers.json")
    if not p.exists():
        return []
    try:
        return [s for s in json.loads(p.read_text()) if _valid(s.get("email"))]
    except Exception:
        return []

def load_subscribers() -> list[dict]:
    sheet_url = os.environ.get("GOOGLE_SHEET_URL")
    if sheet_url:
        subs = _from_sheet(sheet_url)
        if subs:
            return _dedupe(subs)
    return _dedupe(_from_file())

def _dedupe(subs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for s in subs:
        e = s["email"].lower()
        if e in seen:
            continue
        seen.add(e)
        out.append(s)
    return out
```

### 10. `src/nodes/email_node.py` (full)

```python
from __future__ import annotations
import os
import smtplib
from datetime import date
from email.message import EmailMessage
from src.config import SMTP_HOST, SMTP_PORT
from src.render import markdown_to_email_html
from src.state import AgentState
from src.utils.state_io import load_sent_urls, save_sent_urls

RAW_INDEX_MARKER = "<details>"  # everything from here to </details> is stripped

def _strip_raw_index(md: str) -> str:
    idx = md.find(RAW_INDEX_MARKER)
    return md[:idx].rstrip() if idx >= 0 else md

def email_node(state: AgentState) -> dict:
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        return {"email_log": {"status": "failed", "subscribers_found": 0, "emails_sent": 0,
                              "errors": ["Missing GMAIL_USER / GMAIL_APP_PASSWORD"]}}

    from src.utils.subscribers import load_subscribers
    subs = load_subscribers()
    if not subs:
        return {"email_log": {"status": "failed", "subscribers_found": 0, "emails_sent": 0,
                              "errors": ["No subscribers"]}}

    body_md = _strip_raw_index(state.get("final_report", ""))
    body_html = markdown_to_email_html(body_md)

    sent, errors = 0, []
    for sub in subs:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"AIA GenAI Intelligence — {date.today().isoformat()}"
            msg["From"] = user
            msg["To"] = sub["email"]
            msg["Bcc"] = user
            msg.set_content(body_md)
            msg.add_alternative(body_html, subtype="html")
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
                s.login(user, pw)
                s.send_message(msg)
            sent += 1
        except Exception as e:
            errors.append(f"{sub['email']}: {e}")

    # Write sent URLs log
    if sent > 0:
        new_entries = load_sent_urls()
        today = date.today().isoformat()
        for item in state.get("curated_news", []):
            url = (item.get("url") or "").strip().rstrip("/").lower()
            if not url:
                continue
            new_entries.append({
                "url": url,
                "sent_at": today,
                "title": item.get("title", ""),
                "buzz_score": item.get("buzz_score", 1),
                "insurance_score": item.get("insurance_score", 1),
            })
        save_sent_urls(new_entries)

    return {"email_log": {
        "status": "success" if sent > 0 else "failed",
        "subscribers_found": len(subs),
        "emails_sent": sent,
        "errors": errors,
    }}
```

## Verification

```bash
# First run: baseline
python -m src.main --days 2

# Inspect the email:
#  - TL;DR block present (3 bullets)
#  - 4 section headers with "(N)" counts
#  - At least one "Boardroom angle:" sentence in Business
#  - At least one "Build this at AIA:" sentence in Tech
#  - Paper of the Day card in Research
#  - InsurTech section with 🏢 or ⚖️ flags visible on at least one item
#  - Source Health footer with 8 source rows
#  - No <details> in email body

# Second run (no-repeat filter)
python -m src.main --days 2

# Expected: second email contains NO URLs from first email
# Check state/sent_urls.json has 7-day retention
jq 'length, (map(.sent_at) | unique)' state/sent_urls.json

# Friday-specific
# On a Friday, email has a "Week in Review" paragraph after TL;DR
```

## Risks / Open Items

- **LLM latency**: 4–6 LLM calls per run (curate, TLDR, boardroom, build-at-AIA, paper, Friday). Each ~2–4s. Total ~15–25s acceptable for a daily batch job.
- **JSON parse retries cost time**: 3 retries × 4-6 calls = worst case 18 calls. Monitor cost.
- **Title similarity false positives**: short titles ("GPT-5") match too eagerly. Consider minimum title length ≥ 20 chars before similarity matching, or combine with URL-host check.
- **Enrichment prompts receive truncated JSON**: items cut to 6000–8000 chars. On heavy news days this truncates information. Log when truncation happens.
- **Markdown → email HTML loses `<details>`**: intentional; confirm via inbox that no `<details>` shows up.
- **`sent_urls.json` growth**: retained 30 days (for Phase 5). At ~30 items/day = 900 entries/month. Still small, but log size each run.

## Next Phase

Phase 4 wraps the pipeline in a scheduler and adds the full test suite. See [plan-phase-4-scheduler-and-tests.md](./plan-phase-4-scheduler-and-tests.md).
