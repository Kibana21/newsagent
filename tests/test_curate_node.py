import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.nodes.curate_node import curate_node

FIXTURES = Path(__file__).parent / "fixtures"

RAW = [{"title": "t", "url": "https://x/1", "source": "tavily", "summary": "s", "published_at": ""}]
BUZZ = {"https://x/1": 1}


def _fake_llm(content: str):
    fake = MagicMock()
    fake.invoke.return_value.content = content
    return fake


def test_happy_path():
    good = json.dumps(json.loads((FIXTURES / "curate_output.json").read_text()))
    with patch("src.nodes.curate_node.get_llm", return_value=_fake_llm(good)):
        out = curate_node({"raw_news": RAW, "buzz_scores": BUZZ})
    assert "business" in out["categorized_news"]
    assert "insurtech" in out["categorized_news"]


def test_retries_on_bad_json():
    bad = MagicMock()
    bad.content = "not json"
    good = MagicMock()
    good.content = json.dumps({"business": [], "models": [], "frameworks": [], "security": [],
                               "research": [], "enterprise": [], "regulatory": [],
                               "insurtech": [], "emerging": []})
    fake = MagicMock()
    fake.invoke.side_effect = [bad, good]
    with patch("src.nodes.curate_node.get_llm", return_value=fake):
        out = curate_node({"raw_news": RAW, "buzz_scores": BUZZ})
    assert fake.invoke.call_count == 2
    assert "business" in out["categorized_news"]


def test_raises_after_three_bad_attempts():
    fake = MagicMock()
    fake.invoke.return_value.content = "still not json"
    with patch("src.nodes.curate_node.get_llm", return_value=fake):
        with pytest.raises(ValueError, match="3 attempts"):
            curate_node({"raw_news": RAW, "buzz_scores": BUZZ})


def test_empty_raw_returns_empty_categories():
    out = curate_node({"raw_news": [], "buzz_scores": {}})
    assert out["curated_news"] == []
    for k in ("models", "frameworks", "security", "research",
              "enterprise", "regulatory", "business", "insurtech", "emerging"):
        assert out["categorized_news"][k] == []
