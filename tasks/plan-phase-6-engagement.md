# Phase 6 — Engagement & Intelligence Upgrades

## Goal

Transform the digest from an **information dump** into a newsletter people genuinely look forward to opening. Every change below is measurable against open rate, forward rate, or reader feedback.

## Features

| ID | Feature | Impact | Effort |
|---|---|---|---|
| F1 | Act / Watch / Aware signal per item | High | Low |
| F2 | Sentiment signal per insurance item | High | Low |
| F3 | Editor's Take — opinionated 2-3 sentence opener | High | Low |
| F4 | Competitive Heat Map (OpenAI vs Google vs Anthropic vs Meta) | High | Medium |
| F5 | "Steal This Week" — one concrete AIA product idea | High | Medium |
| F6 | Reading time at top | Low | Low |
| F7 | "Last week you read" continuity hook | Medium | Low |
| F8 | One-click pulse feedback (👍 / 👎) | Medium | Low |

---

## Files Modified

| Path | Change |
|---|---|
| `src/state.py` | Add `action_signal`, `sentiment` fields to `NewsItem` |
| `src/prompts.py` | Update `CURATE_PROMPT` (F1, F2); add `EDITORS_TAKE_PROMPT`, `COMPETITIVE_HEATMAP_PROMPT`, `STEAL_THIS_WEEK_PROMPT` |
| `src/nodes/curate_node.py` | Pass new fields through from LLM response |
| `src/nodes/summarize_node.py` | Add 4 new sections; reading time; last-week hook |
| `src/utils/edition_state.py` | NEW — save/load `state/last_edition.json` and `state/feedback.json` |
| `src/render.py` | Render action badges, sentiment badges, heatmap table |

---

## Design Decisions

1. **F1 + F2 added to `CURATE_PROMPT` — not separate LLM calls.** The LLM already reads every item once for categorisation and scoring. Adding two extra fields (`action_signal`, `sentiment`) costs zero extra API calls and keeps scoring consistent.

2. **F3 (Editor's Take) is one LLM call at the start of `summarize_node`, before the section rendering.** It sees the full curated set and writes a 2–3 sentence opinionated opener. Temperature 0.6 for personality.

3. **F4 (Competitive Heat Map) is a dedicated prompt** that receives only the business + insurtech items and extracts mentions of OpenAI, Google/DeepMind, Anthropic, Meta, Mistral, xAI. If a lab isn't mentioned, it shows `——`. Rendered as a compact table with 🔥 indicators.

4. **F5 (Steal This Week) is a dedicated prompt** that receives the full curated set and produces ONE concrete, AIA-specific product idea with: what to build, which team owns it, rough effort estimate (days/weeks/months), and which domain it serves (underwriting/claims/marketing/compliance/customer service).

5. **F6 (Reading time)** — computed from final Markdown word count before rendering. No LLM call. Formula: `max(2, word_count // 200)` minutes.

6. **F7 (Last week hook)** — `state/last_edition.json` stores the top TL;DR item from each run (url + headline + date). On next run, `summarize_node` reads this and prepends one line: *"Last [weekday]: [headline] — [what developed since, if any new items reference the same URL or domain]"*

7. **F8 (Feedback)** — two `mailto:` links at the bottom of the email (`👍 This was useful` / `👎 Needs improvement`). The mailto populates a subject line that encodes the edition date. When the user sends the email, it lands in GMAIL_USER's inbox with a parseable subject. A separate `python -m src.parse_feedback` script (Phase 6b) reads those and writes to `state/feedback.json`. For now, just the links — parsing is a later step.

---

## Implementation Steps

### Step 1 — `src/state.py`: new fields on `NewsItem`

```python
action_signal: str   # "act" | "watch" | "aware"
sentiment: str       # "opportunity" | "risk" | "neutral"  (insurance items only)
```

### Step 2 — `src/prompts.py`: update `CURATE_PROMPT`

Add to the output schema per item:
```
"action_signal": "act" | "watch" | "aware"   # act = decision needed in 1-2 weeks
"sentiment": "opportunity" | "risk" | "neutral"
```

Rules for the LLM:
- `action_signal = "act"` → competitive threat, imminent regulatory deadline, or AIA-applicable tool available NOW
- `action_signal = "watch"` → developing story, revisit in 30 days
- `action_signal = "aware"` → background context, no decision needed
- `sentiment` only meaningful when `insurance_score >= 2`; default `"neutral"` otherwise

### Step 3 — `src/prompts.py`: three new prompts

#### `EDITORS_TAKE_PROMPT`
```
You are writing the opening 2-3 sentences of a daily AI intelligence brief for AIA Singapore's leadership team. 
Be direct, opinionated, and specific. Highlight the single most important theme of the day and what it means for a life insurer in APAC. 
Write with authority — not "it seems" or "it appears". Use active voice. No bullet points.
Today's curated items: {items_json}
```

#### `COMPETITIVE_HEATMAP_PROMPT`
```
From the news items below, extract mentions of the following AI labs: OpenAI, Google/DeepMind, Anthropic, Meta/LLaMA, Mistral, xAI/Grok.

For each lab mentioned, write ONE sentence (max 15 words) on what they shipped or announced.
For labs not mentioned, output null.

Return JSON only:
{{"openai": "...", "google": "...", "anthropic": "...", "meta": "...", "mistral": "...", "xai": "..."}}

Items: {items_json}
```

#### `STEAL_THIS_WEEK_PROMPT`
```
You are an AI innovation advisor to AIA Singapore. Based on the week's AI developments below, identify the single most actionable product idea AIA could build or pilot in the next quarter.

Be specific. Output JSON:
{{
  "title": "short idea name (max 8 words)",
  "what": "one sentence — what to build",
  "why_now": "one sentence — why this week's news makes it timely",
  "domain": "underwriting | claims | marketing | compliance | customer_service | agent_tools",
  "effort": "days | weeks | months",
  "team": "which AIA team would own this"
}}

Items: {items_json}
```

### Step 4 — `src/utils/edition_state.py` (new file)

```python
# Saves/loads state/last_edition.json and state/feedback.json
# last_edition.json schema: {"date": "...", "top_url": "...", "top_headline": "..."}
def save_last_edition(date: str, top_url: str, top_headline: str) -> None
def load_last_edition() -> dict | None
```

### Step 5 — `src/nodes/summarize_node.py`: assemble new layout

New email structure:
```
┌─────────────────────────────────────────┐
│  AIA GenAI Intelligence — YYYY-MM-DD    │
│  X min read                             │
│                                         │
│  📌 Editor's Take                       │
│  [2-3 sentence opinionated opener]      │
│                                         │
│  [last week hook if applicable]         │
│                                         │
│  ⚡ TL;DR — Today's Must-Reads          │
│                                         │
│  🌡️ AI Lab Pulse                        │
│  OpenAI 🔥🔥🔥 | Google 🔥🔥 | ...     │
│                                         │
│  🏢 Business & Strategy                 │
│  [🔴 Act] [📈 Opportunity] item         │
│  Boardroom angle: ...                   │
│                                         │
│  🛠️ Tech & Engineering                  │
│  [🟡 Watch] item                        │
│  Build this at AIA: ...                │
│                                         │
│  🔬 Research Frontiers                  │
│                                         │
│  🛡️ InsurTech & AIA Relevance           │
│  [⚠️ Risk] [🏢 Competitor] item         │
│                                         │
│  💡 Steal This Week                     │
│  [concrete AIA product idea]            │
│                                         │
│  Source Health footer                   │
│                                         │
│  Was this useful? 👍 👎                  │
└─────────────────────────────────────────┘
```

### Step 6 — Badge rendering in `src/render.py`

```python
ACTION_BADGES = {"act": "🔴 Act", "watch": "🟡 Watch", "aware": "🟢 Aware"}
SENTIMENT_BADGES = {"opportunity": "📈 Opportunity", "risk": "⚠️ Risk", "neutral": ""}
```

### Step 7 — Feedback links in `src/nodes/email_node.py`

```python
FEEDBACK_FOOTER = """
---
*Was today's edition useful?*
[👍 Yes, this helped](mailto:{gmail_user}?subject=feedback-{date}-good) · [👎 Needs improvement](mailto:{gmail_user}?subject=feedback-{date}-poor)
"""
```

---

## Verification

```bash
# Run pipeline, inspect report
python -m src.main --days 2

# Check report has all new sections
grep -c "Editor's Take" reports/$(date -I)_report.md        # → 1
grep -c "AI Lab Pulse" reports/$(date -I)_report.md         # → 1
grep -c "Steal This Week" reports/$(date -I)_report.md      # → 1
grep -c "🔴\|🟡\|🟢" reports/$(date -I)_report.md           # → >= 3
grep -c "📈\|⚠️" reports/$(date -I)_report.md               # → >= 1
grep -c "min read" reports/$(date -I)_report.md             # → 1
grep -c "Was this useful" reports/$(date -I)_report.md      # → 1

# Check last_edition.json written
cat state/last_edition.json

# Second run — check "last week" hook
python -m src.main --days 2
grep "Last" reports/$(date -I)_report.md                    # → last-edition line
```

---

## Risks / Open Items

- **CURATE_PROMPT growing large**: adding `action_signal` and `sentiment` to 25 items × JSON output increases response size. Monitor for truncation. Mitigate: reduce item cap from 25 → 20 if needed.
- **Editor's Take temperature**: 0.6 may produce inconsistent tone. Test with 0.4 if it feels too random.
- **Competitive Heat Map misses labs not in news**: expected behaviour — `null` entries render as `——`. Do not hallucinate.
- **Steal This Week quality**: highly dependent on news day. On slow news days it may be generic. Add a `confidence: "high" | "medium" | "low"` field — only render if confidence is medium or high.
- **Feedback mailto links**: open rate of email clients varies. Some strip mailto links. This is a best-effort mechanism — no server needed.
- **LLM call count increase**: +3 new calls (Editor's Take, Heatmap, Steal This Week) per daily run. Total: ~7 calls/run. At Gemini Flash pricing, negligible. Total runtime ~35–50s.
