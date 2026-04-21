from __future__ import annotations
import csv
import io
import json
import os
import re
from pathlib import Path
from typing import Any
import requests

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def _from_sheet(url: str) -> list[dict[str, Any]]:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        fieldnames = reader.fieldnames or []
        email_col = next((c for c in fieldnames if "email" in c.lower()), None)
        if not email_col:
            return []
        return [
            {"email": row[email_col].strip(), "name": row.get("name", ""), "persona": "all"}
            for row in reader if _valid(row.get(email_col, ""))
        ]
    except Exception as e:
        print(f"[subscribers] sheet fetch failed: {e}")
        return []


def _from_file() -> list[dict[str, Any]]:
    p = Path("subscribers.json")
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        return [s for s in data if _valid(s.get("email", ""))]
    except Exception:
        return []


def _dedupe(subs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out = []
    for s in subs:
        e = s["email"].lower()
        if e in seen:
            continue
        seen.add(e)
        out.append(s)
    return out


def load_subscribers() -> list[dict[str, Any]]:
    sheet_url = os.environ.get("GOOGLE_SHEET_URL")
    if sheet_url:
        subs = _from_sheet(sheet_url)
        if subs:
            return _dedupe(subs)
    return _dedupe(_from_file())
