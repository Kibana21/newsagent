from __future__ import annotations
import json
from typing import Any
from src.config import COMPETITOR_INSURERS, REGULATORS
from src.llm import get_llm
from src.prompts import CURATE_PROMPT
from src.state import AgentState

KEYS = ("business", "technical", "research", "insurtech")


def _parse_json(text: str) -> dict[str, Any] | None:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return None


def curate_node(state: AgentState) -> dict[str, Any]:
    raw = list(state.get("raw_news") or [])  # type: ignore[arg-type]
    buzz = dict(state.get("buzz_scores") or {})  # type: ignore[arg-type]
    if not raw:
        return {"curated_news": [], "categorized_news": {k: [] for k in KEYS}}

    # Cap at 25 items, prioritising high-buzz items to keep the prompt manageable
    raw.sort(key=lambda x: buzz.get(x.get("url", ""), 1), reverse=True)
    raw = raw[:25]

    llm = get_llm(temperature=0.1)
    prompt = CURATE_PROMPT.format(
        competitors=", ".join(COMPETITOR_INSURERS),
        regulators=", ".join(REGULATORS),
        items_json=json.dumps(raw)[:15000],
        buzz_json=json.dumps(buzz),
    )

    print(f"[curate] calling LLM to categorise {len(raw)} items (this takes ~20-40s)...")
    data: dict[str, Any] | None = None
    for attempt in range(3):
        resp = llm.invoke(prompt)
        text = str(resp.content) if hasattr(resp, "content") else str(resp)
        data = _parse_json(text)
        if data and all(k in data for k in KEYS):
            break
        print(f"[curate] parse failed on attempt {attempt + 1}, retrying...")

    if data is None:
        raise ValueError("curate_node: LLM did not return valid JSON after 3 attempts")

    categorized = {k: data.get(k, []) for k in KEYS}
    flat: list[Any] = sum(categorized.values(), [])
    counts = {k: len(v) for k, v in categorized.items()}
    print(f"[curate] done — {counts}")
    return {"curated_news": flat, "categorized_news": categorized}
