from __future__ import annotations
import json
import os
from datetime import date
from typing import Any, List, cast
from src.llm import get_llm
from src.prompts import (
    TLDR_PROMPT, BOARDROOM_PROMPT, BUILD_AT_AIA_PROMPT,
    PAPER_EXPLAINER_PROMPT, WEEK_IN_REVIEW_PROMPT,
    EDITORS_TAKE_PROMPT, COMPETITIVE_HEATMAP_PROMPT, STEAL_THIS_WEEK_PROMPT,
)
from src.state import AgentState, NewsItem
from src.utils.dates import freshness_tag
from src.utils.edition_state import load_last_edition, save_last_edition

ACTION_BADGES = {"act": "🔴 Act", "watch": "🟡 Watch", "aware": "🟢 Aware"}
SENTIMENT_BADGES = {"opportunity": "📈", "risk": "⚠️"}
LAB_ORDER = [("openai", "OpenAI"), ("google", "Google"), ("anthropic", "Anthropic"),
             ("meta", "Meta"), ("mistral", "Mistral"), ("xai", "xAI")]


def _call_json(llm: Any, prompt_tpl: str, kwargs: dict[str, str]) -> Any:
    prompt = prompt_tpl.format(**kwargs)
    resp = llm.invoke(prompt)
    text = str(resp.content) if hasattr(resp, "content") else str(resp)
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _flatten(cat: dict[str, List[NewsItem]]) -> list[NewsItem]:
    out: list[NewsItem] = []
    for items in cat.values():
        out.extend(items)
    return out


def _reading_time(text: str) -> int:
    return max(2, len(text.split()) // 200)


def _buzz_badge(url: str, buzz: dict[str, int]) -> str:
    count = buzz.get(url, 1)
    return f" 🔥 Trending across {count} sources" if count >= 3 else ""


def _item_prefix(item: NewsItem, flags: bool) -> str:
    parts = []
    action = item.get("action_signal", "")
    sentiment = item.get("sentiment", "")
    if action in ACTION_BADGES:
        parts.append(ACTION_BADGES[action])
    if sentiment in SENTIMENT_BADGES:
        parts.append(SENTIMENT_BADGES[sentiment])
    if flags:
        if item.get("competitor"):
            parts.append("🏢")
        elif item.get("regulatory"):
            parts.append("⚖️")
    return " · ".join(parts) + " · " if parts else ""


def _render_section(
    emoji: str,
    title: str,
    items: list[NewsItem],
    buzz: dict[str, int],
    enrichments: dict[str, str],
    label: str,
    flags: bool = False,
) -> list[str]:
    if not items:
        return []
    lines = [f"## {emoji} {title} ({len(items)})", ""]
    for item in items:
        url = item.get("url", "#")
        item_title = item.get("title", "(no title)")
        summary = item.get("summary", "")[:300]
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        prefix = _item_prefix(item, flags)
        lines.append(f"- {prefix}**[{item_title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        if summary:
            lines.append(f"  {summary}")
        sentence = enrichments.get(url, "")
        if sentence:
            lines.append(f"  *{label}* {sentence}")
        lines.append("")
    return lines


def _render_research(
    items: list[NewsItem],
    buzz: dict[str, int],
    paper: dict[str, Any] | None,
) -> list[str]:
    if not items:
        return []
    lines = [f"## 🔬 Research Frontiers ({len(items)})", ""]
    paper_url = paper.get("url", "") if paper else ""
    if paper:
        lines += [
            "**📄 Paper of the Day**",
            "",
            f"**[{paper.get('title', '')}]({paper_url})**",
            "",
            paper.get("explainer", ""),
            "",
        ]
    for item in items:
        url = item.get("url", "#")
        if url == paper_url:
            continue
        item_title = item.get("title", "(no title)")
        summary = item.get("summary", "")[:200]
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        prefix = _item_prefix(item, False)
        lines.append(f"- {prefix}**[{item_title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        if summary:
            lines.append(f"  {summary}")
        lines.append("")
    return lines


def _render_heatmap(heatmap: dict[str, Any] | None) -> list[str]:
    if not heatmap:
        return []
    rows = []
    for key, label in LAB_ORDER:
        val = heatmap.get(key)
        if val and val != "null":
            rows.append(f"**{label}** — {val}")
    if not rows:
        return []
    lines = ["## 🌡️ AI Lab Pulse", ""]
    lines += [f"- {r}" for r in rows]
    lines.append("")
    return lines


def _render_steal(steal: dict[str, Any] | None) -> list[str]:
    if not steal or steal.get("confidence") == "low":
        return []
    lines = [
        "## 💡 Steal This Week",
        "",
        f"**{steal.get('title', '')}**",
        "",
        f"{steal.get('what', '')}",
        "",
        f"*Why now:* {steal.get('why_now', '')}",
        "",
    ]
    domain = steal.get("domain", "")
    effort = steal.get("effort", "")
    team = steal.get("team", "")
    meta = " · ".join(filter(None, [domain, f"effort: {effort}" if effort else "", team]))
    if meta:
        lines += [f"*{meta}*", ""]
    return lines


def _source_health(state: AgentState) -> list[str]:
    lines = ["---", "", "**Source Health**", ""]
    rows = []
    for field, label in [
        ("tavily_news", "Tavily"), ("rss_news", "RSS"), ("arxiv_news", "arXiv"),
        ("github_news", "GitHub"), ("hf_news", "HuggingFace"), ("hn_news", "HackerNews"),
        ("reddit_news", "Reddit"), ("youtube_news", "YouTube"),
    ]:
        count = len(list(state.get(field) or []))  # type: ignore[arg-type, call-overload]
        status = "✅" if count > 0 else "❌"
        rows.append(f"{label}: {count} {status}")
    lines.append(" · ".join(rows))
    lines.append("")
    return lines


def _feedback_footer(today: str) -> list[str]:
    gmail_user = os.environ.get("GMAIL_USER", "")
    if not gmail_user:
        return []
    return [
        "---",
        "",
        f"*Was today's edition useful?*  "
        f"[👍 Yes, this helped](mailto:{gmail_user}?subject=feedback-{today}-good) · "
        f"[👎 Needs improvement](mailto:{gmail_user}?subject=feedback-{today}-poor)",
        "",
    ]


def _raw_index(items: list[NewsItem]) -> list[str]:
    if not items:
        return []
    lines = ["<details>", "<summary>Raw Intelligence Index</summary>", ""]
    for item in items:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        score = item.get("insurance_score", 1)
        buzz = item.get("buzz_score", 1)
        action = item.get("action_signal", "")
        lines.append(f"- [{title}]({url}) — ins:{score} buzz:{buzz} {action}")
    lines += ["", "</details>", ""]
    return lines


def summarize_node(state: AgentState) -> dict[str, Any]:
    cat: dict[str, List[NewsItem]] = cast(Any, state.get("categorized_news") or {})
    buzz: dict[str, int] = cast(Any, state.get("buzz_scores") or {})
    curated: list[NewsItem] = cast(Any, state.get("curated_news") or [])
    llm = get_llm(temperature=0.2)
    today = date.today()

    all_items = _flatten(cat)
    items_json_full = json.dumps(all_items)[:8000]
    total = len(all_items)
    active_sections = sum(1 for v in cat.values() if v)
    print(f"[summarize] enriching {total} curated items across {active_sections} sections...")

    print("[summarize] LLM call 1/7 — Editor's Take")
    editors_take_resp = llm.invoke(EDITORS_TAKE_PROMPT.format(items_json=items_json_full))
    editors_take = str(editors_take_resp.content) if hasattr(editors_take_resp, "content") else str(editors_take_resp)

    print("[summarize] LLM call 2/7 — TL;DR")
    tldr_data = _call_json(llm, TLDR_PROMPT, {"items_json": items_json_full}) or []

    print("[summarize] LLM call 3/7 — Boardroom angles")
    boardroom_data = _call_json(llm, BOARDROOM_PROMPT, {"items_json": json.dumps(cat.get("business", []))[:6000]}) or []

    print("[summarize] LLM call 4/7 — Build this at AIA")
    build_data = _call_json(llm, BUILD_AT_AIA_PROMPT, {"items_json": json.dumps(cat.get("technical", []))[:6000]}) or []

    paper_data: dict[str, Any] | None = None
    if cat.get("research"):
        print("[summarize] LLM call 5/7 — Paper of the Day")
        paper_data = _call_json(llm, PAPER_EXPLAINER_PROMPT, {"items_json": json.dumps(cat.get("research", []))[:6000]})
    else:
        print("[summarize] LLM call 5/7 — skipped (no research items)")

    print("[summarize] LLM call 6/7 — AI Lab Pulse")
    heatmap_data = _call_json(llm, COMPETITIVE_HEATMAP_PROMPT, {"items_json": items_json_full})

    print("[summarize] LLM call 7/7 — Steal This Week")
    steal_data = _call_json(llm, STEAL_THIS_WEEK_PROMPT, {"items_json": items_json_full})

    week_review = ""
    if today.weekday() == 4:  # Friday
        print("[summarize] Friday — generating Week in Review")
        resp = llm.invoke(WEEK_IN_REVIEW_PROMPT.format(items_json=items_json_full))
        week_review = str(resp.content) if hasattr(resp, "content") else str(resp)

    boardroom = {r.get("url", ""): r.get("sentence", "") for r in (boardroom_data if isinstance(boardroom_data, list) else [])}
    build_at_aia = {r.get("url", ""): r.get("sentence", "") for r in (build_data if isinstance(build_data, list) else [])}

    # Last edition hook
    last = load_last_edition()
    last_hook = ""
    if last:
        from datetime import datetime
        try:
            last_dt = datetime.fromisoformat(last["date"])
            day_name = last_dt.strftime("%A")
            last_hook = f"*Last {day_name}:* [{last['top_headline']}]({last['top_url']}) — follow-up below if it reappears today."
        except Exception:
            pass

    # Build report
    today_str = today.isoformat()
    lines: list[str] = [
        f"# AIA GenAI Intelligence — {today_str}",
        "",
    ]

    # Reading time placeholder — computed after assembly
    READING_TIME_MARKER = "{{READING_TIME}}"
    lines.append(READING_TIME_MARKER)
    lines.append("")

    if week_review:
        lines += ["## 📅 Week in Review", "", week_review.strip(), ""]

    # Editor's Take
    if editors_take.strip():
        lines += ["## 📌 Editor's Take", "", editors_take.strip(), ""]

    # Last week hook
    if last_hook:
        lines += [f"> {last_hook}", ""]

    # TL;DR
    if tldr_data and isinstance(tldr_data, list):
        lines += ["## ⚡ TL;DR — Today's Must-Reads", ""]
        for entry in tldr_data[:3]:
            bullet = entry.get("bullet", "")
            url = entry.get("url", "")
            if bullet:
                lines.append(f"- {bullet}" + (f" [→]({url})" if url else ""))
        lines.append("")

    lines += _render_heatmap(heatmap_data)
    lines += _render_section("🏢", "Business & Strategy", cast(List[NewsItem], cat.get("business", [])), buzz, boardroom, "Boardroom angle:")
    lines += _render_section("🛠️", "Tech & Engineering", cast(List[NewsItem], cat.get("technical", [])), buzz, build_at_aia, "Build this at AIA:")
    lines += _render_research(cast(List[NewsItem], cat.get("research", [])), buzz, paper_data)
    lines += _render_section("🛡️", "InsurTech & AIA Relevance", cast(List[NewsItem], cat.get("insurtech", [])), buzz, {}, "", flags=True)
    lines += _render_steal(steal_data)
    lines += _source_health(state)
    lines += _feedback_footer(today_str)
    lines += _raw_index(curated)

    report = "\n".join(lines)
    reading_mins = _reading_time(report)
    report = report.replace(READING_TIME_MARKER, f"*{reading_mins} min read*")

    # Save last edition for next run's continuity hook
    top_url, top_headline = "", ""
    if tldr_data and isinstance(tldr_data, list) and tldr_data:
        top_url = tldr_data[0].get("url", "")
        top_headline = tldr_data[0].get("bullet", "")[:80]
    if top_url:
        save_last_edition(today_str, top_url, top_headline)

    print(f"[summarize] done — {reading_mins} min read, {len(all_items)} items")
    return {"final_report": report}
