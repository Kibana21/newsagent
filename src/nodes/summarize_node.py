from __future__ import annotations
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any, List, cast
from src.llm import get_llm
from src.prompts import (
    EDITORS_TAKE_PROMPT, DUAL_TLDR_PROMPT,
    MODEL_RELEASE_PROMPT, SECURITY_BRIEF_PROMPT, FRAMEWORK_BRIEF_PROMPT,
    EVAL_BRIEF_PROMPT, ENTERPRISE_BRIEF_PROMPT, REGULATORY_BRIEF_PROMPT,
    EMERGING_CONCEPT_PROMPT, BOARDROOM_PROMPT, PAPER_EXPLAINER_PROMPT,
    COMPETITIVE_HEATMAP_PROMPT, STEAL_THIS_WEEK_PROMPT, WEEK_IN_REVIEW_PROMPT,
)
from src.state import AgentState, NewsItem
from src.utils.dates import freshness_tag
from src.utils.edition_state import load_last_edition, save_last_edition

# ── Badges ────────────────────────────────────────────────────────────────────

ACTION_BADGES = {"act": "🔴 Act", "watch": "🟡 Watch", "aware": "🟢 Aware"}
SENTIMENT_BADGES = {"opportunity": "📈", "risk": "⚠️"}
SEVERITY_BADGES = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH",
    "medium":   "🟡 MEDIUM",
    "info":     "🔵 INFO",
}
TRY_BADGES = {"yes": "✅ Try today", "maybe": "⏳ Evaluate", "wait": "❌ Wait"}
ADOPTION_BADGES = {
    "production-ready": "✅ Production-ready",
    "early-beta":       "⏳ Early beta",
    "research-prototype": "🔬 Research prototype",
}
LAB_ORDER = [
    ("openai", "OpenAI"), ("google", "Google"), ("anthropic", "Anthropic"),
    ("meta", "Meta"), ("mistral", "Mistral"), ("xai", "xAI"),
]
REPLICABLE_BADGES = {"yes": "✅ Replicable at AIA", "maybe": "🤔 Potentially replicable", "no": ""}
STORY_ICONS = {"success": "✅", "failure": "⚠️", "pilot": "🧪", "strategy": "📋"}


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _item_prefix(item: NewsItem, flags: bool = False) -> str:
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


def _source_health(state: AgentState) -> list[str]:
    lines = ["---", "", "**Source Health**", ""]
    rows = []
    for field, label in [
        ("tavily_news", "Tavily"), ("rss_news", "RSS"), ("arxiv_news", "arXiv"),
        ("github_news", "GitHub"), ("hf_news", "HuggingFace"), ("hn_news", "HackerNews"),
        ("reddit_news", "Reddit"), ("youtube_news", "YouTube"), ("serp_news", "SerpAPI"),
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
        "---", "",
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


# ── New section renderers ─────────────────────────────────────────────────────

def _render_dual_tldr(dual_data: Any) -> list[str]:
    if not dual_data or not isinstance(dual_data, dict):
        return []
    lines: list[str] = ["## ⚡ Today's Signals", ""]
    for key, label in [("ceo", "Executives"), ("cto", "Engineers")]:
        bullets = dual_data.get(key, [])
        if not bullets:
            continue
        lines.append(f"*{label}*")
        for entry in bullets[:3]:
            bullet = entry.get("bullet", "")
            url = entry.get("url", "")
            action = entry.get("action", "")
            if bullet:
                link = f" [→]({url})" if url else ""
                action_str = f" *{action}*" if action else ""
                lines.append(f"- {bullet}{action_str}{link}")
        lines.append("")
    return lines


def _render_models(items: list[NewsItem], briefs: list[dict[str, Any]], buzz: dict[str, int]) -> list[str]:
    if not items:
        return []
    brief_map = {b.get("url", ""): b for b in (briefs or [])}
    lines = [f"## 🚀 Model Releases ({len(items)})", ""]
    for item in items:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        prefix = _item_prefix(item)
        lines.append(f"- {prefix}**[{title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        b = brief_map.get(url)
        if b:
            vendor = b.get("vendor") or ""
            model_name = b.get("model_name") or ""
            key_upgrade = b.get("key_upgrade") or ""
            ctx = b.get("context_window")
            price = b.get("pricing_change")
            aia = b.get("aia_use_case") or ""
            meta_parts = []
            if vendor and model_name:
                meta_parts.append(f"**{vendor} · {model_name}**")
            if key_upgrade:
                meta_parts.append(key_upgrade)
            if ctx:
                meta_parts.append(f"context: {ctx}")
            if price:
                meta_parts.append(f"price: {price}")
            if meta_parts:
                lines.append(f"  {' · '.join(meta_parts)}")
            if aia:
                lines.append(f"  *AIA use case:* {aia}")
        lines.append("")
    return lines


def _render_security(items: list[NewsItem], briefs: list[dict[str, Any]], buzz: dict[str, int]) -> list[str]:
    if not items:
        return []
    brief_map = {b.get("url", ""): b for b in (briefs or [])}
    # Sort by severity
    sev_order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    items_sorted = sorted(
        items,
        key=lambda x: sev_order.get(brief_map.get(x.get("url", ""), {}).get("severity", "info"), 3),
    )
    lines = [f"## 🔐 Security Threat Intel ({len(items)})", ""]
    attack_vectors: list[str] = []
    for item in items_sorted:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        b = brief_map.get(url, {})
        severity = b.get("severity", "info")
        sev_badge = SEVERITY_BADGES.get(severity, "🔵 INFO")
        if severity == "critical":
            lines.append("⚠️ **IMMEDIATE ACTION REQUIRED**")
        lines.append(f"- {sev_badge}  **[{title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        attack = b.get("attack_vector", "")
        if attack:
            attack_vectors.append(attack)
            lines.append(f"  *Attack vector:* {attack}")
        affected = b.get("affected_systems", "")
        if affected:
            lines.append(f"  *Affected:* {affected}")
        mitigation = b.get("mitigation", "")
        if mitigation:
            lines.append(f"  *Mitigation:* {mitigation}")
        aia_rel = b.get("aia_relevance", "")
        if aia_rel == "direct":
            lines.append("  🎯 *AIA relevance: DIRECT*")
        lines.append("")

    # "This Week in Attacks" micro-summary
    if len(items) >= 2 and attack_vectors:
        top_vector = Counter(attack_vectors).most_common(1)[0][0]
        lines += [
            f"> *This week: {len(items)} AI security incident(s) logged — "
            f"**{top_vector}** was the leading attack vector.*",
            "",
        ]
    return lines


def _render_frameworks(items: list[NewsItem], briefs: list[dict[str, Any]], buzz: dict[str, int]) -> list[str]:
    if not items:
        return []
    brief_map = {b.get("url", ""): b for b in (briefs or [])}
    # Sort: try_today=yes first
    try_order = {"yes": 0, "maybe": 1, "wait": 2}
    items_sorted = sorted(
        items,
        key=lambda x: try_order.get(brief_map.get(x.get("url", ""), {}).get("try_today", "wait"), 2),
    )
    lines = [f"## 🧰 Framework Watch ({len(items)})", ""]
    for item in items_sorted:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        b = brief_map.get(url, {})
        try_badge = TRY_BADGES.get(b.get("try_today", ""), "")
        adoption = ADOPTION_BADGES.get(b.get("adoption_signal", ""), "")
        replaces = b.get("replaces_or_extends")
        lang = b.get("primary_language", "")
        use_case = b.get("use_case", "")
        aia_fit = b.get("aia_fit", "")
        prefix = _item_prefix(item)
        lines.append(f"- {prefix}**[{title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        meta = []
        if use_case:
            meta.append(use_case)
        if replaces:
            meta.append(f"replaces: {replaces}")
        if lang:
            meta.append(lang)
        if adoption:
            meta.append(adoption)
        if try_badge:
            meta.append(try_badge)
        if meta:
            lines.append(f"  {' · '.join(meta)}")
        if aia_fit:
            lines.append(f"  *AIA fit:* {aia_fit}")
        lines.append("")
    return lines


def _render_evals(items: list[NewsItem], briefs: list[dict[str, Any]], buzz: dict[str, int],
                  paper_data: dict[str, Any] | None) -> list[str]:
    if not items:
        return []
    brief_map = {b.get("url", ""): b for b in (briefs or [])}
    paper_url = paper_data.get("url", "") if paper_data else ""
    lines = [f"## 📊 Research & Evals ({len(items)})", ""]

    # Paper of the day first
    if paper_data:
        lines += [
            "**📄 Paper of the Day**", "",
            f"**[{paper_data.get('title', '')}]({paper_url})**", "",
            paper_data.get("explainer", ""), "",
        ]

    for item in items:
        url = item.get("url", "#")
        if url == paper_url:
            continue
        title = item.get("title", "(no title)")
        summary = item.get("summary", "")[:200]
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        prefix = _item_prefix(item)
        b = brief_map.get(url, {})
        lines.append(f"- {prefix}**[{title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        if b.get("key_finding"):
            lines.append(f"  *Finding:* {b['key_finding']}")
            if b.get("winner"):
                lines.append(f"  *Winner:* {b['winner']}")
            if b.get("aia_takeaway"):
                lines.append(f"  *AIA takeaway:* {b['aia_takeaway']}")
        elif summary:
            lines.append(f"  {summary}")
        lines.append("")
    return lines


def _render_enterprise(items: list[NewsItem], briefs: list[dict[str, Any]], buzz: dict[str, int]) -> list[str]:
    if not items:
        return []
    brief_map = {b.get("url", ""): b for b in (briefs or [])}
    lines = [f"## 🏭 Enterprise Stories ({len(items)})", ""]
    for item in items:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        b = brief_map.get(url, {})
        story_type = b.get("story_type", "")
        icon = STORY_ICONS.get(story_type, "📰")
        replicable = REPLICABLE_BADGES.get(b.get("replicable_at_aia", ""), "")
        industry = b.get("industry", "")
        use_case = b.get("use_case", "")
        outcome = b.get("outcome", "")
        lesson = b.get("lesson", "")
        prefix = _item_prefix(item)
        lines.append(f"- {icon} {prefix}**[{title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        meta = []
        if industry:
            meta.append(industry)
        if use_case:
            meta.append(use_case)
        if replicable:
            meta.append(replicable)
        if meta:
            lines.append(f"  {' · '.join(meta)}")
        if outcome:
            lines.append(f"  *Outcome:* {outcome}")
        if lesson:
            lines.append(f"  *Lesson:* {lesson}")
        lines.append("")
    return lines


def _render_regulatory(items: list[NewsItem], briefs: list[dict[str, Any]], buzz: dict[str, int]) -> list[str]:
    if not items:
        return []
    brief_map = {b.get("url", ""): b for b in (briefs or [])}
    urg_order = {"act": 0, "watch": 1, "aware": 2}
    items_sorted = sorted(
        items,
        key=lambda x: urg_order.get(brief_map.get(x.get("url", ""), {}).get("urgency", "aware"), 2),
    )
    lines = [f"## 🏛️ Regulatory Radar ({len(items)})", ""]
    for item in items_sorted:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        b = brief_map.get(url, {})
        urgency = b.get("urgency", "aware")
        deadline = b.get("deadline")
        instrument = b.get("instrument_type", "")
        jurisdiction = b.get("jurisdiction", "")
        aia_action = b.get("aia_action", "")
        prefix = _item_prefix(item, flags=True)
        if deadline:
            lines.append(f"📅 **DEADLINE: {deadline}**")
        lines.append(f"- {ACTION_BADGES.get(urgency, '')} {prefix}**[{title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        meta = []
        if instrument:
            meta.append(instrument)
        if jurisdiction:
            meta.append(jurisdiction)
        if meta:
            lines.append(f"  {' · '.join(meta)}")
        if aia_action:
            lines.append(f"  *AIA action:* {aia_action}")
        lines.append("")
    return lines


def _render_emerging(items: list[NewsItem], briefs: list[dict[str, Any]], buzz: dict[str, int]) -> list[str]:
    if not items:
        return []
    brief_map = {b.get("url", ""): b for b in (briefs or [])}
    maturity_order = {"mainstream": 0, "early-adoption": 1, "research": 2, "theoretical": 3}
    items_sorted = sorted(
        items,
        key=lambda x: maturity_order.get(brief_map.get(x.get("url", ""), {}).get("maturity", "research"), 2),
    )
    lines = [f"## 💡 Emerging Concepts ({len(items)})", ""]
    for item in items_sorted:
        url = item.get("url", "#")
        title = item.get("title", "(no title)")
        fresh = freshness_tag(item.get("published_at", ""))
        badge = _buzz_badge(url, buzz)
        b = brief_map.get(url, {})
        concept_name = b.get("concept_name", "")
        tech_exp = b.get("tech_explanation", "")
        biz_impl = b.get("business_implication", "")
        maturity = b.get("maturity", "")
        horizon = b.get("horizon", "")
        prefix = _item_prefix(item)
        header = f"**{concept_name}** — " if concept_name else ""
        lines.append(f"- {prefix}{header}**[{title}]({url})**{badge}")
        if fresh:
            lines.append(f"  {fresh}")
        meta = []
        if maturity:
            meta.append(f"maturity: {maturity}")
        if horizon:
            meta.append(f"horizon: {horizon}")
        if meta:
            lines.append(f"  {' · '.join(meta)}")
        if tech_exp:
            lines.append(f"  *For engineers:* {tech_exp}")
        if biz_impl:
            lines.append(f"  *For leadership:* {biz_impl}")
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


def _render_section(
    emoji: str, title: str, items: list[NewsItem], buzz: dict[str, int],
    enrichments: dict[str, str], label: str, flags: bool = False,
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


def _render_steal(steal: dict[str, Any] | None) -> list[str]:
    if not steal or steal.get("confidence") == "low":
        return []
    lines = [
        "## 💡 Steal This Week", "",
        f"**{steal.get('title', '')}**", "",
        f"{steal.get('what', '')}", "",
        f"*Why now:* {steal.get('why_now', '')}", "",
    ]
    meta = " · ".join(filter(None, [
        steal.get("domain", ""),
        f"effort: {steal.get('effort', '')}" if steal.get("effort") else "",
        steal.get("team", ""),
    ]))
    if meta:
        lines += [f"*{meta}*", ""]
    return lines


# ── Render context (shared across all three reports) ─────────────────────────

@dataclass
class _RenderCtx:
    cat: dict[str, List[NewsItem]]
    buzz: dict[str, int]
    curated: list[NewsItem]
    state: AgentState
    editors_take: str
    dual_tldr: Any
    heatmap_data: Any
    model_briefs: list[dict[str, Any]]
    security_briefs: list[dict[str, Any]]
    framework_briefs: list[dict[str, Any]]
    eval_briefs: list[dict[str, Any]]
    paper_data: dict[str, Any] | None
    enterprise_briefs: list[dict[str, Any]]
    regulatory_briefs: list[dict[str, Any]]
    boardroom: dict[str, str]
    emerging_briefs: list[dict[str, Any]]
    steal_data: Any
    week_review: str
    last_hook: str
    today_str: str


def _finalize(lines: list[str]) -> str:
    MARKER = "{{READING_TIME}}"
    text = "\n".join(lines)
    mins = _reading_time(text)
    return text.replace(MARKER, f"*{mins} min read*")


def _render_cto_signals(dual_tldr: Any) -> list[str]:
    """Engineer-only signals panel from the dual TL;DR data."""
    if not dual_tldr or not isinstance(dual_tldr, dict):
        return []
    bullets = dual_tldr.get("cto", [])
    if not bullets:
        return []
    lines = ["## ⚡ Developer Signals", ""]
    for entry in bullets[:3]:
        bullet = entry.get("bullet", "")
        url = entry.get("url", "")
        action = entry.get("action", "")
        if bullet:
            link = f" [→]({url})" if url else ""
            action_str = f" *{action}*" if action else ""
            lines.append(f"- {bullet}{action_str}{link}")
    lines.append("")
    return lines


def _render_ceo_signals(dual_tldr: Any) -> list[str]:
    """Executive-only signals panel from the dual TL;DR data."""
    if not dual_tldr or not isinstance(dual_tldr, dict):
        return []
    bullets = dual_tldr.get("ceo", [])
    if not bullets:
        return []
    lines = ["## ⚡ Executive Signals", ""]
    for entry in bullets[:3]:
        bullet = entry.get("bullet", "")
        url = entry.get("url", "")
        action = entry.get("action", "")
        if bullet:
            link = f" [→]({url})" if url else ""
            action_str = f" *{action}*" if action else ""
            lines.append(f"- {bullet}{action_str}{link}")
    lines.append("")
    return lines


def _assemble_dev(ctx: _RenderCtx) -> str:
    """Developer-focused report: models, security, frameworks, research, emerging."""
    MARKER = "{{READING_TIME}}"
    lines: list[str] = [
        f"# AIA Developer Intelligence — {ctx.today_str}", "",
        MARKER, "",
        "> *Audience: engineers, AI practitioners, platform teams*", "",
    ]
    lines += _render_cto_signals(ctx.dual_tldr)
    lines += _render_models(
        cast(List[NewsItem], ctx.cat.get("models", [])), ctx.model_briefs, ctx.buzz)
    lines += _render_security(
        cast(List[NewsItem], ctx.cat.get("security", [])), ctx.security_briefs, ctx.buzz)
    lines += _render_frameworks(
        cast(List[NewsItem], ctx.cat.get("frameworks", [])), ctx.framework_briefs, ctx.buzz)
    lines += _render_evals(
        cast(List[NewsItem], ctx.cat.get("research", [])), ctx.eval_briefs, ctx.buzz, ctx.paper_data)
    lines += _render_emerging(
        cast(List[NewsItem], ctx.cat.get("emerging", [])), ctx.emerging_briefs, ctx.buzz)
    lines += _source_health(ctx.state)
    return _finalize(lines)


def _assemble_biz(ctx: _RenderCtx) -> str:
    """Business-focused report: strategy, enterprise, regulatory, insurtech."""
    MARKER = "{{READING_TIME}}"
    lines: list[str] = [
        f"# AIA Business Intelligence — {ctx.today_str}", "",
        MARKER, "",
        "> *Audience: leadership, strategy, compliance, innovation teams*", "",
    ]
    if ctx.week_review:
        lines += ["## 📅 Week in Review", "", ctx.week_review.strip(), ""]
    if ctx.editors_take.strip():
        lines += ["## 📌 Editor's Take", "", ctx.editors_take.strip(), ""]
    if ctx.last_hook:
        lines += [f"> {ctx.last_hook}", ""]
    lines += _render_ceo_signals(ctx.dual_tldr)
    lines += _render_heatmap(ctx.heatmap_data)
    lines += _render_section(
        "🏢", "Business & Strategy",
        cast(List[NewsItem], ctx.cat.get("business", [])), ctx.buzz, ctx.boardroom, "Boardroom angle:")
    lines += _render_enterprise(
        cast(List[NewsItem], ctx.cat.get("enterprise", [])), ctx.enterprise_briefs, ctx.buzz)
    lines += _render_regulatory(
        cast(List[NewsItem], ctx.cat.get("regulatory", [])), ctx.regulatory_briefs, ctx.buzz)
    lines += _render_section(
        "🛡️", "InsurTech & AIA Relevance",
        cast(List[NewsItem], ctx.cat.get("insurtech", [])), ctx.buzz, {}, "", flags=True)
    lines += _render_steal(ctx.steal_data)
    lines += _source_health(ctx.state)
    lines += _feedback_footer(ctx.today_str)
    return _finalize(lines)


def _assemble_full(ctx: _RenderCtx) -> str:
    """Combined report for all audiences."""
    MARKER = "{{READING_TIME}}"
    lines: list[str] = [
        f"# AIA GenAI Intelligence — {ctx.today_str}", "",
        MARKER, "",
    ]
    if ctx.week_review:
        lines += ["## 📅 Week in Review", "", ctx.week_review.strip(), ""]
    if ctx.editors_take.strip():
        lines += ["## 📌 Editor's Take", "", ctx.editors_take.strip(), ""]
    if ctx.last_hook:
        lines += [f"> {ctx.last_hook}", ""]
    lines += _render_dual_tldr(ctx.dual_tldr)
    lines += _render_heatmap(ctx.heatmap_data)
    lines += _render_models(
        cast(List[NewsItem], ctx.cat.get("models", [])), ctx.model_briefs, ctx.buzz)
    lines += _render_security(
        cast(List[NewsItem], ctx.cat.get("security", [])), ctx.security_briefs, ctx.buzz)
    lines += _render_frameworks(
        cast(List[NewsItem], ctx.cat.get("frameworks", [])), ctx.framework_briefs, ctx.buzz)
    lines += _render_evals(
        cast(List[NewsItem], ctx.cat.get("research", [])), ctx.eval_briefs, ctx.buzz, ctx.paper_data)
    lines += _render_enterprise(
        cast(List[NewsItem], ctx.cat.get("enterprise", [])), ctx.enterprise_briefs, ctx.buzz)
    lines += _render_regulatory(
        cast(List[NewsItem], ctx.cat.get("regulatory", [])), ctx.regulatory_briefs, ctx.buzz)
    lines += _render_section(
        "🏢", "Business & Strategy",
        cast(List[NewsItem], ctx.cat.get("business", [])), ctx.buzz, ctx.boardroom, "Boardroom angle:")
    lines += _render_emerging(
        cast(List[NewsItem], ctx.cat.get("emerging", [])), ctx.emerging_briefs, ctx.buzz)
    lines += _render_section(
        "🛡️", "InsurTech & AIA Relevance",
        cast(List[NewsItem], ctx.cat.get("insurtech", [])), ctx.buzz, {}, "", flags=True)
    lines += _render_steal(ctx.steal_data)
    lines += _source_health(ctx.state)
    lines += _feedback_footer(ctx.today_str)
    lines += _raw_index(ctx.curated)
    return _finalize(lines)


# ── Main node ─────────────────────────────────────────────────────────────────

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
    print(f"[summarize] {total} curated items across {active_sections} sections — starting LLM calls...")

    # ── LLM calls ─────────────────────────────────────────────────────────────
    from src.config import COMPETITOR_INSURERS

    print("[summarize] call 1/13 — Editor's Take")
    editors_resp = llm.invoke(EDITORS_TAKE_PROMPT.format(items_json=items_json_full))
    editors_take = str(editors_resp.content) if hasattr(editors_resp, "content") else str(editors_resp)

    print("[summarize] call 2/13 — Dual TL;DR (CEO + CTO)")
    dual_tldr = _call_json(llm, DUAL_TLDR_PROMPT, {
        "items_json": items_json_full,
        "competitors": ", ".join(COMPETITOR_INSURERS),
    })

    print("[summarize] call 3/13 — AI Lab Pulse")
    heatmap_data = _call_json(llm, COMPETITIVE_HEATMAP_PROMPT, {"items_json": items_json_full})

    model_briefs: list[dict[str, Any]] = []
    if cat.get("models"):
        print("[summarize] call 4/13 — Model Release cards")
        result = _call_json(llm, MODEL_RELEASE_PROMPT, {"items_json": json.dumps(cat["models"])[:6000]})
        model_briefs = result if isinstance(result, list) else []
    else:
        print("[summarize] call 4/13 — skipped (no model items)")

    security_briefs: list[dict[str, Any]] = []
    if cat.get("security"):
        print("[summarize] call 5/13 — Security briefs")
        result = _call_json(llm, SECURITY_BRIEF_PROMPT, {"items_json": json.dumps(cat["security"])[:6000]})
        security_briefs = result if isinstance(result, list) else []
    else:
        print("[summarize] call 5/13 — skipped (no security items)")

    framework_briefs: list[dict[str, Any]] = []
    if cat.get("frameworks"):
        print("[summarize] call 6/13 — Framework briefs")
        result = _call_json(llm, FRAMEWORK_BRIEF_PROMPT, {"items_json": json.dumps(cat["frameworks"])[:6000]})
        framework_briefs = result if isinstance(result, list) else []
    else:
        print("[summarize] call 6/13 — skipped (no framework items)")

    eval_briefs: list[dict[str, Any]] = []
    paper_data: dict[str, Any] | None = None
    if cat.get("research"):
        print("[summarize] call 7/13 — Eval/Research briefs + Paper of Day")
        result = _call_json(llm, EVAL_BRIEF_PROMPT, {"items_json": json.dumps(cat["research"])[:6000]})
        eval_briefs = result if isinstance(result, list) else []
        paper_data = _call_json(llm, PAPER_EXPLAINER_PROMPT, {"items_json": json.dumps(cat["research"])[:6000]})
    else:
        print("[summarize] call 7/13 — skipped (no research items)")

    enterprise_briefs: list[dict[str, Any]] = []
    if cat.get("enterprise"):
        print("[summarize] call 8/13 — Enterprise story briefs")
        result = _call_json(llm, ENTERPRISE_BRIEF_PROMPT, {"items_json": json.dumps(cat["enterprise"])[:6000]})
        enterprise_briefs = result if isinstance(result, list) else []
    else:
        print("[summarize] call 8/13 — skipped (no enterprise items)")

    regulatory_briefs: list[dict[str, Any]] = []
    if cat.get("regulatory"):
        print("[summarize] call 9/13 — Regulatory briefs")
        result = _call_json(llm, REGULATORY_BRIEF_PROMPT, {"items_json": json.dumps(cat["regulatory"])[:6000]})
        regulatory_briefs = result if isinstance(result, list) else []
    else:
        print("[summarize] call 9/13 — skipped (no regulatory items)")

    boardroom: dict[str, str] = {}
    if cat.get("business"):
        print("[summarize] call 10/13 — Boardroom angles")
        result = _call_json(llm, BOARDROOM_PROMPT, {"items_json": json.dumps(cat["business"])[:6000]})
        boardroom = {r.get("url", ""): r.get("sentence", "") for r in (result if isinstance(result, list) else [])}
    else:
        print("[summarize] call 10/13 — skipped (no business items)")

    emerging_briefs: list[dict[str, Any]] = []
    if cat.get("emerging"):
        print("[summarize] call 11/13 — Emerging concept briefs")
        result = _call_json(llm, EMERGING_CONCEPT_PROMPT, {"items_json": json.dumps(cat["emerging"])[:6000]})
        emerging_briefs = result if isinstance(result, list) else []
    else:
        print("[summarize] call 11/13 — skipped (no emerging items)")

    print("[summarize] call 12/13 — Steal This Week")
    steal_data = _call_json(llm, STEAL_THIS_WEEK_PROMPT, {"items_json": items_json_full})

    week_review = ""
    if today.weekday() == 4:  # Friday
        print("[summarize] call 13/13 — Week in Review (Friday)")
        resp = llm.invoke(WEEK_IN_REVIEW_PROMPT.format(items_json=items_json_full))
        week_review = str(resp.content) if hasattr(resp, "content") else str(resp)
    else:
        print("[summarize] call 13/13 — skipped (not Friday)")

    # ── Last edition hook ──────────────────────────────────────────────────────
    last = load_last_edition()
    last_hook = ""
    if last:
        from datetime import datetime
        try:
            last_dt = datetime.fromisoformat(last["date"])
            day_name = last_dt.strftime("%A")
            last_hook = (
                f"*Last {day_name}:* [{last['top_headline']}]({last['top_url']}) "
                f"— follow-up below if it reappears today."
            )
        except Exception:
            pass

    # ── Assemble all three reports ─────────────────────────────────────────────
    today_str = today.isoformat()

    ctx = _RenderCtx(
        cat=cat, buzz=buzz, curated=curated, state=state,
        editors_take=editors_take, dual_tldr=dual_tldr, heatmap_data=heatmap_data,
        model_briefs=model_briefs, security_briefs=security_briefs,
        framework_briefs=framework_briefs, eval_briefs=eval_briefs,
        paper_data=paper_data, enterprise_briefs=enterprise_briefs,
        regulatory_briefs=regulatory_briefs, boardroom=boardroom,
        emerging_briefs=emerging_briefs, steal_data=steal_data,
        week_review=week_review, last_hook=last_hook, today_str=today_str,
    )

    full_report = _assemble_full(ctx)
    dev_report = _assemble_dev(ctx)
    biz_report = _assemble_biz(ctx)

    # Save last edition for next run's continuity hook
    top_url, top_headline = "", ""
    if dual_tldr and isinstance(dual_tldr, dict):
        ceo = dual_tldr.get("ceo", [])
        if ceo and isinstance(ceo, list):
            top_url = ceo[0].get("url", "")
            top_headline = ceo[0].get("bullet", "")[:80]
    if top_url:
        save_last_edition(today_str, top_url, top_headline)

    reading_mins = _reading_time(full_report)
    print(f"[summarize] done — {reading_mins} min read, {total} items, {active_sections} sections")
    return {"final_report": full_report, "dev_report": dev_report, "biz_report": biz_report}
