from __future__ import annotations
import json
from typing import Any
from src.config import COMPETITOR_INSURERS, REGULATORS, SINGAPORE_BANKS
from src.llm import get_llm
from src.prompts import CURATE_PROMPT
from src.state import AgentState

CATEGORIES = (
    "models", "frameworks", "security", "research",
    "enterprise", "regulatory", "business", "insurtech", "emerging",
)


def _parse_json(text: str) -> dict[str, Any] | None:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return None


def curate_node(state: AgentState) -> dict[str, Any]:
    raw = list(state.get("raw_news") or [])  # type: ignore[arg-type]
    buzz = dict(state.get("buzz_scores") or {})  # type: ignore[arg-type]
    days = int(state.get("days") or 2)
    if not raw:
        return {"curated_news": [], "categorized_news": {k: [] for k in CATEGORIES}}

    # Sort by buzz; ensure coverage across topic packs by interleaving
    raw.sort(key=lambda x: buzz.get(x.get("url", ""), 1), reverse=True)
    # Guarantee at least 2 items per topic pack reach the LLM if available
    seen_packs: dict[str, int] = {}
    priority: list[Any] = []
    remainder: list[Any] = []
    for item in raw:
        pack = str(item.get("topic_pack") or "")
        if pack and seen_packs.get(pack, 0) < 2:
            seen_packs[pack] = seen_packs.get(pack, 0) + 1
            priority.append(item)
        else:
            remainder.append(item)
    # Fill up to 50 items — more headroom for 18 sources
    items_to_curate = (priority + remainder)[:50]

    llm = get_llm(temperature=0.1)
    prompt = CURATE_PROMPT.format(
        competitors=", ".join(COMPETITOR_INSURERS),
        regulators=", ".join(REGULATORS),
        sg_banks=", ".join(SINGAPORE_BANKS),
        days=days,
        items_json=json.dumps(items_to_curate)[:20000],
        buzz_json=json.dumps(buzz),
    )

    print(f"[curate] calling LLM to categorise {len(items_to_curate)} items (this takes ~20-40s)...")
    data: dict[str, Any] | None = None
    for attempt in range(3):
        resp = llm.invoke(prompt)
        text = str(resp.content) if hasattr(resp, "content") else str(resp)
        data = _parse_json(text)
        if data and any(k in data for k in CATEGORIES):
            break
        print(f"[curate] parse failed on attempt {attempt + 1}, retrying...")

    if data is None:
        raise ValueError("curate_node: LLM did not return valid JSON after 3 attempts")

    categorized = {k: data.get(k, []) for k in CATEGORIES}
    flat: list[Any] = sum(categorized.values(), [])
    counts = {k: len(v) for k, v in categorized.items() if v}
    dropped = len(data.get("dropped", []))
    print(f"[curate] done — {counts} (dropped={dropped})")
    return {"curated_news": flat, "categorized_news": categorized}
