from __future__ import annotations
from datetime import date
from typing import Any
import markdown as md

INLINE_STYLES = {
    "h1": "font-family:Arial,sans-serif;font-size:22px;color:#1a1a1a;margin:20px 0 10px;",
    "h2": "font-family:Arial,sans-serif;font-size:18px;color:#1a1a1a;margin:20px 0 8px;border-bottom:2px solid #e8e8e8;padding-bottom:6px;",
    "h3": "font-family:Arial,sans-serif;font-size:15px;color:#333;margin:14px 0 6px;",
    "p":  "font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#333;margin:6px 0;",
    "ul": "margin:8px 0 14px 20px;padding:0;",
    "li": "font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#333;margin-bottom:8px;",
    "a":  "color:#1a73e8;text-decoration:none;",
    "em": "color:#555;font-style:italic;",
    "strong": "font-weight:600;",
}


def render_monthly(items: list[dict[str, Any]], llm_data: dict[str, Any]) -> str:
    month = date.today().strftime("%B %Y")
    lines = [
        f"# AIA GenAI Intelligence — {month} Top 10",
        "",
        "The month's most important GenAI developments for APAC life insurers,",
        "ranked by cross-source buzz × AIA relevance.",
        "",
    ]
    opening = (llm_data.get("opening") or "").strip()
    if opening:
        lines += ["## This Month's Theme", "", opening, ""]

    rationales = {r["url"]: r["sentence"] for r in llm_data.get("rationales", []) if "url" in r}

    lines += ["## Best of the Month", ""]
    for rank, item in enumerate(items, start=1):
        title = item.get("title", "(no title)")
        url = item.get("url", "#")
        rationale = rationales.get(url, "")
        buzz = item.get("buzz_score", 1)
        ins = item.get("insurance_score", 1)
        lines.append(f"**{rank}. [{title}]({url})** — buzz {buzz} · insurance {ins}/3")
        if rationale:
            lines.append(f"   _{rationale}_")
        lines.append("")

    return "\n".join(lines)


def markdown_to_email_html(md_text: str) -> str:
    html = md.markdown(md_text, extensions=["extra", "sane_lists"])
    for tag, style in INLINE_STYLES.items():
        html = html.replace(f"<{tag}>", f'<{tag} style="{style}">')
    return f'<div style="max-width:720px;margin:0 auto;padding:24px;background:#fff;">{html}</div>'
