from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture
def sample_state():
    return {
        "search_query": "latest GenAI",
        "days": 2,
        "tavily_news": [], "rss_news": [], "arxiv_news": [], "github_news": [],
        "hf_news": [], "hn_news": [], "reddit_news": [], "youtube_news": [],
    }


@pytest.fixture
def sample_news_item():
    return {
        "title": "OpenAI Announces GPT-5",
        "url": "https://openai.com/blog/gpt-5",
        "summary": "Big release.",
        "source": "rss",
        "published_at": "2026-04-20T10:00:00+00:00",
    }


@pytest.fixture
def mock_llm(monkeypatch):
    curate_response = json.dumps({
        "business": [{"title": "AIA AI", "url": "https://x/1", "summary": "...",
                      "source": "tavily", "published_at": "", "insurance_score": 3,
                      "competitor": False, "regulatory": False}],
        "technical": [],
        "research": [],
        "insurtech": [],
    })
    responses = {
        "curate": curate_response,
        "tldr": json.dumps([{"bullet": "b1", "url": "https://x/1"},
                            {"bullet": "b2", "url": "https://x/2"},
                            {"bullet": "b3", "url": "https://x/3"}]),
        "boardroom": json.dumps([{"url": "https://x/1", "sentence": "Boardroom note."}]),
        "build": json.dumps([{"url": "https://x/1", "sentence": "Build this at AIA."}]),
        "paper": json.dumps({"url": "https://x/1", "title": "T", "explainer": "Explains..."}),
    }

    def _invoke(prompt: str):
        p = prompt.lower()
        key = (
            "curate" if "curate" in p or "categorise" in p or "insurtech" in p else
            "tldr" if "must-read" in p or "tl;dr" in p or "top 3" in p else
            "boardroom" if "boardroom" in p else
            "build" if "build this at aia" in p else
            "paper" if "paper" in p or "explainer" in p else
            "curate"
        )
        m = MagicMock()
        m.content = responses.get(key, "{}")
        return m

    fake = MagicMock()
    fake.invoke.side_effect = _invoke
    # Patch both the module-level reference and each node's imported reference
    for target in (
        "src.llm.get_llm",
        "src.nodes.curate_node.get_llm",
        "src.nodes.summarize_node.get_llm",
    ):
        monkeypatch.setattr(target, lambda temperature=0.2: fake)
    return fake
