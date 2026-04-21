from __future__ import annotations
import json
from datetime import date
from typing import Any, List, cast
from src.llm import get_llm
from src.prompts import (
    TLDR_PROMPT, BOARDROOM_PROMPT, BUILD_AT_AIA_PROMPT,
    PAPER_EXPLAINER_PROMPT, WEEK_IN_REVIEW_PROMPT,
)
from src.state import AgentState, NewsItem
from src.utils.dates import freshness_tag


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


def _buzz_badge(url: str, buzz: dict[str, int]) -> str:
    count = buzz.get(url, 1)
    return f" 🔥 Trending across {count} sources" if count >= 3 else ""


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
        prefix = ""
        if flags:
            if item.get("competitor"):
                prefix = "🏢 "
            elif item.get("regulatory"):
                prefix = "⚖️ "
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
        lines.append(f"- **[{item_title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        if summary:
            lines.append(f"  {summary}")
        lines.append("")
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


def _raw_index(items: list[NewsItem]) -> list[str]:
    if not items:
        return []
    lines = ["<details>", "<summary>Raw Intelligence Index</summary>", ""]
    for item in items:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        score = item.get("insurance_score", 1)
        buzz = item.get("buzz_score", 1)
        lines.append(f"- [{title}]({url}) — ins:{score} buzz:{buzz}")
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
    print(f"[summarize] enriching {total} curated items across {sum(1 for v in cat.values() if v)} sections...")

    print("[summarize] LLM call 1/4 — TL;DR")
    tldr_data = _call_json(llm, TLDR_PROMPT, {"items_json": items_json_full}) or []

    print("[summarize] LLM call 2/4 — Boardroom angles")
    boardroom_data = _call_json(llm, BOARDROOM_PROMPT, {"items_json": json.dumps(cat.get("business", []))[:6000]}) or []

    print("[summarize] LLM call 3/4 — Build this at AIA")
    build_data = _call_json(llm, BUILD_AT_AIA_PROMPT, {"items_json": json.dumps(cat.get("technical", []))[:6000]}) or []

    paper_data: dict[str, Any] | None = None
    if cat.get("research"):
        print("[summarize] LLM call 4/4 — Paper of the Day")
        paper_data = _call_json(llm, PAPER_EXPLAINER_PROMPT, {"items_json": json.dumps(cat.get("research", []))[:6000]})
    else:
        print("[summarize] LLM call 4/4 — skipped (no research items)")

    week_review = ""
    if today.weekday() == 4:  # Friday
        print("[summarize] Friday detected — generating Week in Review")
        resp = llm.invoke(WEEK_IN_REVIEW_PROMPT.format(items_json=items_json_full))
        week_review = str(resp.content) if hasattr(resp, "content") else str(resp)

    # Build lookup dicts
    boardroom = {r.get("url", ""): r.get("sentence", "") for r in (boardroom_data if isinstance(boardroom_data, list) else [])}
    build_at_aia = {r.get("url", ""): r.get("sentence", "") for r in (build_data if isinstance(build_data, list) else [])}

    lines: list[str] = [
        f"# AIA GenAI Intelligence — {today.isoformat()}",
        "",
    ]

    if week_review:
        lines += ["## 📅 Week in Review", "", week_review.strip(), ""]

    # TL;DR
    if tldr_data and isinstance(tldr_data, list):
        lines += ["## ⚡ TL;DR — Today's Must-Reads", ""]
        for entry in tldr_data[:3]:
            bullet = entry.get("bullet", "")
            url = entry.get("url", "")
            if bullet:
                lines.append(f"- {bullet}" + (f" [→]({url})" if url else ""))
        lines.append("")

    lines += _render_section("🏢", "Business & Strategy", cast(List[NewsItem], cat.get("business", [])), buzz, boardroom, "Boardroom angle:")
    lines += _render_section("🛠️", "Tech & Engineering", cast(List[NewsItem], cat.get("technical", [])), buzz, build_at_aia, "Build this at AIA:")
    lines += _render_research(cast(List[NewsItem], cat.get("research", [])), buzz, paper_data)
    lines += _render_section("🛡️", "InsurTech & AIA Relevance", cast(List[NewsItem], cat.get("insurtech", [])), buzz, {}, "", flags=True)
    lines += _source_health(state)
    lines += _raw_index(curated)

    return {"final_report": "\n".join(lines)}
