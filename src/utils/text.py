from __future__ import annotations
import re
from difflib import SequenceMatcher

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    return _TAG_RE.sub("", s or "").strip()


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()
