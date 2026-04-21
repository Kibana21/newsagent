from __future__ import annotations
from datetime import datetime, timezone


def freshness_tag(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
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
