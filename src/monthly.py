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


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _top_items(days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
    cutoff = date.today() - timedelta(days=days)
    entries = [
        e for e in load_sent_urls()
        if _parse_date(e.get("sent_at")) and (_parse_date(e["sent_at"]) or date.min) >= cutoff
    ]

    def score(e: dict[str, Any]) -> tuple[int, int, str]:
        buzz = int(e.get("buzz_score", 1))
        ins = int(e.get("insurance_score", 1))
        return (buzz * ins, buzz, e.get("sent_at", ""))

    entries.sort(key=score, reverse=True)

    seen: set[str] = set()
    top: list[dict[str, Any]] = []
    for e in entries:
        u = e.get("url", "")
        if u in seen:
            continue
        seen.add(u)
        top.append(e)
        if len(top) >= limit:
            break
    return top


def build_monthly_report() -> str:
    items = _top_items()
    if not items:
        month = date.today().strftime("%B %Y")
        return f"# AIA GenAI Intelligence — {month} Top 10\n\nNo items in the past 30 days."

    print(f"[monthly] ranking {len(items)} items, calling LLM for enrichment...")
    llm = get_llm(temperature=0.3)
    resp = llm.invoke(MONTHLY_DIGEST_PROMPT.format(items_json=json.dumps(items)))
    text = str(resp.content) if hasattr(resp, "content") else str(resp)
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        llm_data = json.loads(text)
    except json.JSONDecodeError:
        print("[monthly] LLM JSON parse failed — rendering without enrichment")
        llm_data = {"opening": "", "rationales": []}

    return render_monthly(items, llm_data)


def run() -> dict[str, Any]:
    import os
    import smtplib
    from email.message import EmailMessage
    from src.config import SMTP_HOST, SMTP_PORT

    report_md = build_monthly_report()
    report_html = markdown_to_email_html(report_md)

    today = date.today()
    month_name = today.strftime("%B %Y")
    subject = f"AIA GenAI Intelligence — {month_name} Top 10"

    Path("reports").mkdir(exist_ok=True)
    out_path = Path(f"reports/{today.isoformat()}_monthly.md")
    out_path.write_text(report_md)
    print(f"[monthly] report saved to {out_path}")

    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        print("[monthly] SMTP credentials not set — skipping email delivery")
        return {"status": "saved", "report_path": str(out_path), "emails_sent": 0, "errors": []}

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

    return {
        "status": "success" if sent else "saved",
        "report_path": str(out_path),
        "subscribers_found": len(subs),
        "emails_sent": sent,
        "errors": errors,
    }
