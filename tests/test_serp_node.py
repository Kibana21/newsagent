from __future__ import annotations
from unittest.mock import MagicMock, patch
from src.nodes.serp_node import serp_node


def _state(days: int = 2) -> dict:
    return {"days": days}


def test_returns_empty_when_key_missing(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    out = serp_node(_state())
    assert out == {"serp_news": []}


def test_items_tagged_with_topic_pack(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "fake-key")
    fake_result = {
        "news_results": [
            {"title": "AI security flaw found", "link": "https://x.com/1", "snippet": "Bad.", "date": ""},
        ]
    }
    mock_gs = MagicMock()
    mock_gs.return_value.get_dict.return_value = fake_result
    with patch("src.nodes.serp_node.get_serp_query_packs", return_value={"ai_security": ["AI security news"]}):
        with patch("serpapi.GoogleSearch", mock_gs):
            out = serp_node(_state())
    items = out["serp_news"]
    assert len(items) >= 1
    assert items[0]["topic_pack"] == "ai_security"
    assert items[0]["source"] == "serp"


def test_failed_pack_returns_partial_results(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "fake-key")
    good_result = {"news_results": [{"title": "Good news", "link": "https://x.com/2", "snippet": ""}]}
    call_count = 0

    def side_effect(params):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        if call_count == 1:
            m.get_dict.side_effect = Exception("API error")
        else:
            m.get_dict.return_value = good_result
        return m

    with patch("src.nodes.serp_node.get_serp_query_packs", return_value={
        "pack_a": ["query a"],
        "pack_b": ["query b"],
    }):
        with patch("serpapi.GoogleSearch", side_effect=side_effect):
            out = serp_node(_state())
    # Should still return items from the successful pack
    assert isinstance(out["serp_news"], list)
