from __future__ import annotations
import re
from typing import Any
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from src.config import YT_CHANNELS
from src.state import AgentState, NewsItem

VIDEO_ID_RE = re.compile(r'"videoId":"([a-zA-Z0-9_-]{11})"')


def _fetch_recent_video_ids(channel_id: str, limit: int = 1) -> list[str]:
    try:
        r = requests.get(
            f"https://www.youtube.com/channel/{channel_id}/videos", timeout=15
        )
        ids: list[str] = []
        for m in VIDEO_ID_RE.finditer(r.text):
            vid = m.group(1)
            if vid not in ids:
                ids.append(vid)
            if len(ids) >= limit:
                break
        return ids
    except Exception:
        return []


def _fetch_transcript(video_id: str) -> str:
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=["en"])
        return " ".join(snippet.text for snippet in transcript)
    except Exception:
        return ""


def youtube_node(state: AgentState) -> dict[str, Any]:
    items: list[NewsItem] = []
    print(f"[youtube] fetching transcripts for {len(YT_CHANNELS)} channels...")
    for name, channel_id in YT_CHANNELS:
        for vid in _fetch_recent_video_ids(channel_id, limit=1):
            transcript = _fetch_transcript(vid)
            if not transcript:
                continue
            items.append({
                "title": f"{name}: latest video",
                "url": f"https://www.youtube.com/watch?v={vid}",
                "summary": transcript[:1000],
                "source": "youtube",
                "published_at": "",
            })
    print(f"[youtube] got {len(items)} videos")
    return {"youtube_news": items}
