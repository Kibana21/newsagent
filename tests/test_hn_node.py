import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.nodes.hn_node import hn_node

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_get(url, **kwargs):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    if "topstories" in url:
        r.json.return_value = json.loads((FIXTURES / "hn_topstories.json").read_text())
    elif "1001" in url:
        r.json.return_value = json.loads((FIXTURES / "hn_item_1001.json").read_text())
    elif "1002" in url:
        r.json.return_value = json.loads((FIXTURES / "hn_item_1002.json").read_text())
    elif "1003" in url:
        r.json.return_value = json.loads((FIXTURES / "hn_item_1003.json").read_text())
    else:
        r.json.return_value = {}
    return r


def test_keyword_filter_keeps_ai_stories():
    with patch("src.nodes.hn_node.requests.get", side_effect=_mock_get):
        out = hn_node({})
    titles = [i["title"] for i in out["hn_news"]]
    # Item 1001 has "llm" in title, item 1003 has "claude"/"gpt" — both should pass
    assert any("llm" in t.lower() or "claude" in t.lower() or "gpt" in t.lower() for t in titles)


def test_keyword_filter_drops_non_ai():
    with patch("src.nodes.hn_node.requests.get", side_effect=_mock_get):
        out = hn_node({})
    titles = [i["title"].lower() for i in out["hn_news"]]
    # "Show HN: My weekend project" should be filtered out
    assert not any("weekend project" in t for t in titles)


def test_exception_returns_empty():
    with patch("src.nodes.hn_node.requests.get", side_effect=Exception("timeout")):
        out = hn_node({})
    assert out["hn_news"] == []
